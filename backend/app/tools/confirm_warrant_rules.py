"""Preview and atomically confirm existing stop/target values as warrant prices.

No provider calls, orders or notifications. Management events are written through
FT-010; its commits release savepoints inside one caller-owned transaction.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app.core.config import get_settings
from app.database import DatabaseManager
from app.features.position_monitoring.service.subjects import SqlAlchemyMonitoringSubjectReader
from app.features.product.persistence.models import WarrantModel
from app.features.product.service.application import WarrantService
from app.features.trade_position.domain.enums import TradeManagementEventType
from app.features.trade_position.domain.price_binding import PriceBasis, PriceBinding
from app.features.trade_position.persistence.repositories import (
    SqlAlchemyTradeManagementEventRepository,
)
from app.features.trade_position.persistence.unit_of_work import SqlAlchemyTradePositionUnitOfWork
from app.features.trade_position.service.application import TradePositionService
from app.features.trade_position.service.resolvers import (
    SqlAlchemyWorkspaceSelectionResolver,
    WarrantProductResolver,
)


class RuleConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    trade_id: UUID
    position_id: UUID
    warrant_id: UUID
    isin: str
    product_name: str
    rule_key: Literal["CURRENT_STOP", "CURRENT_TARGET"]
    threshold: Decimal = Field(gt=0, allow_inf_nan=False)
    already_confirmed: bool


class ConfirmationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["warrant-rule-confirmation-v1"] = "warrant-rule-confirmation-v1"
    workspace_id: UUID
    basis: Literal["WARRANT"] = "WARRANT"
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    positions_count: int = Field(gt=0)
    rules: tuple[RuleConfirmation, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_scope(self) -> ConfirmationPlan:
        positions = {(r.trade_id, r.position_id, r.warrant_id) for r in self.rules}
        keys = {(r.trade_id, r.rule_key) for r in self.rules}
        if (
            len(positions) != self.positions_count
            or len({r.trade_id for r in self.rules}) != self.positions_count
            or len({r.position_id for r in self.rules}) != self.positions_count
            or len(keys) != len(self.rules)
            or len(self.rules) != 2 * self.positions_count
        ):
            raise ValueError("Each position must have exactly one stop and one target")
        return self


async def preview(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    currency: str,
    expect_positions: int | None = None,
) -> ConfirmationPlan:
    # Validate currency even when the requested workspace has no open positions.
    PriceBinding(PriceBasis.WARRANT, workspace_id, currency)
    reader = SqlAlchemyMonitoringSubjectReader(
        session, for_rule_evaluation=True, workspace_id=workspace_id
    )
    resolutions = await reader.list_resolutions()
    if not resolutions or (expect_positions is not None and len(resolutions) != expect_positions):
        raise ValueError(
            f"OPEN_POSITION_COUNT_MISMATCH: expected {expect_positions}, found {len(resolutions)}"
        )
    rules: list[RuleConfirmation] = []
    events = SqlAlchemyTradeManagementEventRepository(session)
    for resolution in resolutions:
        subject = resolution.subject
        if subject is None or subject.warrant_id is None:
            raise ValueError(f"UNRESOLVED_POSITION: {resolution.position_id}: {resolution.issue}")
        product = await session.scalar(
            select(WarrantModel).where(
                WarrantModel.id == subject.warrant_id, WarrantModel.workspace_id == workspace_id
            )
        )
        if product is None or not product.isin:
            raise ValueError(f"WARRANT_IDENTITY_MISSING: {subject.trade_id}")
        future_prices = [
            event
            for event in await events.list_effective_for_trade(subject.trade_id)
            if event.effective_at > datetime.now(UTC)
            and event.event_type
            in (TradeManagementEventType.STOP_CHANGED, TradeManagementEventType.TARGET_CHANGED)
        ]
        if future_prices:
            raise ValueError(f"FUTURE_PRICE_EVENTS: {subject.trade_id}")
        binding = PriceBinding(PriceBasis.WARRANT, subject.warrant_id, currency)
        for rule in subject.rules:
            if rule.price_binding is not None and rule.price_binding != binding:
                raise ValueError(f"CONFLICTING_PRICE_BINDING: {subject.trade_id}: {rule.rule_key}")
            if rule.rule_key not in ("CURRENT_STOP", "CURRENT_TARGET"):
                raise ValueError(f"UNSUPPORTED_RULE: {rule.rule_key}")
            rules.append(
                RuleConfirmation(
                    trade_id=subject.trade_id,
                    position_id=subject.position_id,
                    warrant_id=subject.warrant_id,
                    isin=product.isin,
                    product_name=product.display_name,
                    rule_key=(
                        "CURRENT_STOP" if rule.rule_key == "CURRENT_STOP" else "CURRENT_TARGET"
                    ),
                    threshold=rule.threshold,
                    already_confirmed=rule.price_binding == binding,
                )
            )
    return ConfirmationPlan(
        workspace_id=workspace_id,
        currency=currency,
        positions_count=len(resolutions),
        rules=tuple(sorted(rules, key=lambda r: (r.trade_id, r.rule_key))),
    )


def pending_confirmations(
    planned: ConfirmationPlan, current: ConfirmationPlan
) -> tuple[RuleConfirmation, ...]:
    """Allow exact replays, never a changed scope, threshold, identity or binding."""
    if planned.model_dump(exclude={"rules"}) != current.model_dump(exclude={"rules"}):
        raise ValueError("PLAN_CHANGED: workspace, currency or position count differs")
    expected = {(r.trade_id, r.rule_key): r for r in planned.rules}
    actual = {(r.trade_id, r.rule_key): r for r in current.rules}
    if expected.keys() != actual.keys():
        raise ValueError("PLAN_CHANGED: position/rule scope differs")
    for key, before in expected.items():
        after = actual[key]
        if before.model_dump(exclude={"already_confirmed"}) != after.model_dump(
            exclude={"already_confirmed"}
        ) or (before.already_confirmed and not after.already_confirmed):
            raise ValueError(f"PLAN_CHANGED: {before.trade_id}: {before.rule_key}")
    return tuple(r for r in current.rules if not r.already_confirmed)


async def apply_plan(
    connection: AsyncConnection,
    *,
    plan: ConfirmationPlan,
    workspace_id: UUID,
    currency: str,
    actor: UUID,
) -> dict[str, object]:
    """Caller must own the outer transaction and roll it back on any exception."""
    if not connection.in_transaction():
        raise ValueError("OUTER_TRANSACTION_REQUIRED")
    if plan.workspace_id != workspace_id or plan.currency != currency:
        raise ValueError("PLAN_SCOPE_MISMATCH")
    # A short maintenance lock also serializes ordinary API/import writes, which
    # do not acquire this tool's locks themselves. Reads/monitoring remain allowed.
    await connection.execute(text("SET LOCAL lock_timeout = '5s'"))
    await connection.execute(
        text(
            "LOCK TABLE trades, positions, warrants, trade_management_events, "
            "trade_plans, trade_plan_versions, trade_plan_targets IN SHARE ROW EXCLUSIVE MODE"
        )
    )
    async with AsyncSession(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    ) as session:
        current = await preview(
            session,
            workspace_id=workspace_id,
            currency=currency,
            expect_positions=plan.positions_count,
        )
        pending = pending_confirmations(plan, current)
        service = TradePositionService(
            uow=SqlAlchemyTradePositionUnitOfWork(session),
            workspace_selections=SqlAlchemyWorkspaceSelectionResolver(session),
            products=WarrantProductResolver(WarrantService(session)),
        )
        created: list[dict[str, str]] = []
        for rule in pending:
            event = await service.record_management_event(
                workspace_id=workspace_id,
                trade_id=rule.trade_id,
                event_type=(
                    TradeManagementEventType.STOP_CHANGED
                    if rule.rule_key == "CURRENT_STOP"
                    else TradeManagementEventType.TARGET_CHANGED
                ),
                effective_at=datetime.now(UTC),
                actor=actor,
                numeric_value=rule.threshold,
                price_binding=PriceBinding(PriceBasis.WARRANT, rule.warrant_id, currency),
            )
            created.append(
                {
                    "trade_id": str(rule.trade_id),
                    "rule_key": rule.rule_key,
                    "event_id": str(event.id),
                }
            )
        return {
            "status": "APPLIED" if created else "ALREADY_CONFIRMED",
            "workspace_id": str(workspace_id),
            "basis": "WARRANT",
            "currency": currency,
            "positions_count": plan.positions_count,
            "events_created": len(created),
            "rules_already_confirmed": len(plan.rules) - len(created),
            "events": created,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("preview", "apply"))
    parser.add_argument("--workspace-id", type=UUID, required=True)
    parser.add_argument("--currency", required=True)
    parser.add_argument("--expect-positions", type=int)
    parser.add_argument("--actor-id", type=UUID)
    parser.add_argument("--plan", default="-", help="Apply JSON plan file, or - for stdin")
    return parser


async def run(args: argparse.Namespace) -> dict[str, object]:
    plan = None
    if args.mode == "apply":
        if args.actor_id is None:
            raise ValueError("--actor-id is required for apply")
        payload = sys.stdin.read() if args.plan == "-" else Path(args.plan).read_text()
        plan = ConfirmationPlan.model_validate_json(payload)
        if args.expect_positions is not None and plan.positions_count != args.expect_positions:
            raise ValueError("PLAN_POSITION_COUNT_MISMATCH")
    database = DatabaseManager(get_settings())
    try:
        if plan is None:
            async with database.session_context() as session:
                return (
                    await preview(
                        session,
                        workspace_id=args.workspace_id,
                        currency=args.currency,
                        expect_positions=args.expect_positions,
                    )
                ).model_dump(mode="json")
        async with database.engine.begin() as connection:
            return await apply_plan(
                connection,
                plan=plan,
                workspace_id=args.workspace_id,
                currency=args.currency,
                actor=args.actor_id,
            )
    finally:
        await database.dispose()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = asyncio.run(run(args))
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
