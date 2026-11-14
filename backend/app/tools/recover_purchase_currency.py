"""Recover an explicit current currency declaration for an exact purchase inventory.

This maintenance command appends confirmations through the existing execution
owner. It never changes executions, source evidence or SELLs, and never claims
to reconstruct a historical confirmation. The caller owns one outer transaction;
the owner's commits release savepoints within it. A private plan supplies the
already authorized declaration and exact inventory, without per-purchase prompts.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from dataclasses import asdict, replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal
from uuid import UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, AsyncSession

from app.core.config import get_settings
from app.database import DatabaseManager
from app.features.market.persistence.models import CurrencyModel
from app.features.performance.domain.models import (
    CurrencyReference,
    RealizedGrossReport,
    ReportFilters,
    ReportSnapshot,
    SummaryStatus,
)
from app.features.performance.domain.periods import report_interval
from app.features.performance.domain.report import ReportLimitExceeded, build_report
from app.features.performance.service.reader import (
    MAX_CURRENCY_EVIDENCE,
    MAX_EXECUTIONS,
    RealizedGrossSnapshotReader,
)
from app.features.product.persistence.models import WarrantModel
from app.features.trade_position.domain.currency import (
    ExecutionCurrencyConfirmation,
    ExecutionCurrencyDeclaration,
    ExecutionCurrencySource,
)
from app.features.trade_position.domain.currency_evidence import CurrencyEvidenceLimitExceeded
from app.features.trade_position.persistence.currency_evidence import (
    SqlAlchemyCurrencyEvidenceRepository,
)
from app.features.trade_position.persistence.currency_repository import (
    SqlAlchemyExecutionCurrencyConfirmationRepository,
)
from app.features.trade_position.persistence.models import TradeModel
from app.features.trade_position.service.currency_confirmations import (
    ExecutionCurrencyConfirmationService,
    confirmation_fingerprint,
)

REQUEST_NAMESPACE = UUID("e5fbc7ab-5bd7-57d1-a835-6d378b32c28c")
MAX_PLAN_BYTES = 8 * 1024 * 1024


class RecoveryError(ValueError):
    """A stable, non-sensitive rejection suitable for the CLI's JSON output."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class RecoveryTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    execution_id: UUID
    trade_id: UUID
    product_id: UUID


class RecoveryFilters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    from_date: date
    to_date: date
    report_currency: str = Field(pattern=r"^[A-Z]{3}$")
    report_timezone: str = Field(min_length=1, max_length=100)

    def to_domain(self) -> ReportFilters:
        return ReportFilters(**self.model_dump())

    @model_validator(mode="after")
    def validate_interval(self) -> RecoveryFilters:
        report_interval(self.to_domain())
        return self


class RecoveryCounts(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    examined: int = Field(ge=0)
    in_period: int = Field(ge=0)
    outside_period: int = Field(ge=0)
    period_ambiguous: int = Field(ge=0)
    period_unknown: int = Field(ge=0)
    candidates: int = Field(ge=0)
    usable: int = Field(ge=0)
    unresolved: int = Field(ge=0)
    excluded: int = Field(ge=0)
    cancelled: int = Field(ge=0)


class PurchaseCurrencyRecoveryPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_version: Literal["purchase-currency-recovery-v1"] = "purchase-currency-recovery-v1"
    workspace_id: UUID
    actor_id: UUID
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    expected_basis: str = Field(pattern=r"^[0-9a-f]{64}$")
    filters: RecoveryFilters
    inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    note: str = Field(min_length=1, max_length=1000)
    targets: tuple[RecoveryTarget, ...] = Field(min_length=1, max_length=MAX_EXECUTIONS)
    expected_counts: RecoveryCounts
    expected_summary_status: SummaryStatus

    @model_validator(mode="after")
    def validate_scope(self) -> PurchaseCurrencyRecoveryPlan:
        if self.note != self.note.strip():
            raise ValueError("The declaration note must already be trimmed")
        if self.currency != self.filters.report_currency:
            raise ValueError("Declaration and report currency must match")
        if len({target.execution_id for target in self.targets}) != len(self.targets):
            raise ValueError("Each purchase must occur exactly once in the plan")
        products: dict[UUID, UUID] = {}
        for target in self.targets:
            if products.setdefault(target.trade_id, target.product_id) != target.product_id:
                raise ValueError("Each trade must refer to one product")
        return self


def _ordered_targets(plan: PurchaseCurrencyRecoveryPlan) -> tuple[RecoveryTarget, ...]:
    return tuple(sorted(plan.targets, key=lambda target: (target.trade_id, target.execution_id)))


def plan_fingerprint(plan: PurchaseCurrencyRecoveryPlan) -> str:
    """Bind every declaration/scope/postcondition field, independent of list order."""
    payload = plan.model_dump(mode="json")
    payload["targets"] = [target.model_dump(mode="json") for target in _ordered_targets(plan)]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def recovery_request_id(plan: PurchaseCurrencyRecoveryPlan, target: RecoveryTarget) -> UUID:
    return uuid5(REQUEST_NAMESPACE, f"{plan_fingerprint(plan)}:{target.execution_id}")


def _declaration(plan: PurchaseCurrencyRecoveryPlan) -> ExecutionCurrencyDeclaration:
    return ExecutionCurrencyDeclaration(
        currency_code=plan.currency, source=ExecutionCurrencySource.USER_CONFIRMED, note=plan.note
    )


async def read_snapshot(
    session: AsyncSession, workspace_id: UUID, currency_code: str
) -> ReportSnapshot:
    """Materialize the regular complete report input inside this same transaction.

    The caller supplies either a repeatable-read, read-only transaction or the
    maintenance locks. Calling the reader's public read() would use a different
    connection and miss this transaction's uncommitted confirmations.
    """
    started = datetime.now(UTC)
    bind = session.bind
    if bind is None:
        raise RecoveryError("SESSION_UNBOUND", "A database-bound session is required.")
    engine = bind.engine if isinstance(bind, AsyncConnection) else bind
    reader = RealizedGrossSnapshotReader(engine)
    currency = await session.get(CurrencyModel, currency_code)
    if currency is None:
        raise RecoveryError("CURRENCY_NOT_FOUND", "The plan currency is not in the catalogue.")
    trades = await reader._read_trades(session, workspace_id)
    executions = await reader._read_executions(session, workspace_id)
    confirmations = await reader._read_confirmations(session, workspace_id)
    try:
        evidence = await SqlAlchemyCurrencyEvidenceRepository(session).list_for_workspace(
            workspace_id, limit=MAX_CURRENCY_EVIDENCE
        )
    except CurrencyEvidenceLimitExceeded as error:
        raise ReportLimitExceeded("Report exceeds the complete source evidence limit") from error
    return ReportSnapshot(
        workspace_id=workspace_id,
        trades=trades,
        executions=executions,
        confirmations=confirmations,
        currency=CurrencyReference(currency.code, currency.minor_unit, currency.reference_version),
        read_started_at=started,
        read_completed_at=datetime.now(UTC),
        currency_evidence=evidence,
    )


def _validate_targets(
    snapshot: ReportSnapshot, report: RealizedGrossReport, plan: PurchaseCurrencyRecoveryPlan
) -> None:
    trades = {fact.trade.id: fact.trade for fact in snapshot.trades}
    sources = {source.execution_id: source for source in report.sources}
    for target in plan.targets:
        source = sources.get(target.execution_id)
        trade = trades.get(target.trade_id)
        if (
            source is None
            or trade is None
            or trade.workspace_id != plan.workspace_id
            or trade.product_id != target.product_id
            or trade.cancelled_at is not None
            or source.trade_id != target.trade_id
            or source.product_id != target.product_id
            or source.side != "BUY"
            or not source.is_effective
            or source.superseded_by_execution_id is not None
        ):
            raise RecoveryError(
                "TARGET_NOT_EFFECTIVE",
                "A planned purchase is missing, replaced, cancelled or outside its exact scope.",
            )


def _validate_baseline(
    snapshot: ReportSnapshot, report: RealizedGrossReport, plan: PurchaseCurrencyRecoveryPlan
) -> None:
    _validate_targets(snapshot, report, plan)
    if report.basis.id != plan.expected_basis:
        raise RecoveryError(
            "BASELINE_CHANGED", "The complete report inventory differs from the approved basis."
        )
    active_trades = {fact.trade.id for fact in snapshot.trades if fact.trade.cancelled_at is None}
    unknown_buys = {
        source.execution_id
        for source in report.sources
        if source.side == "BUY"
        and source.is_effective
        and source.trade_id in active_trades
        and source.currency_resolution.source == "UNKNOWN"
    }
    if unknown_buys != {target.execution_id for target in plan.targets}:
        raise RecoveryError(
            "TARGET_SCOPE_CHANGED",
            "The exact plan must cover all current, non-cancelled UNKNOWN purchases; "
            "the tool never expands or reduces that scope.",
        )
    sources = {source.execution_id: source for source in report.sources}
    for target in plan.targets:
        source = sources[target.execution_id]
        resolution = source.currency_resolution
        if (
            source.currency_confirmation is not None
            or source.currency_history
            or resolution.source != "UNKNOWN"
            or resolution.currency_code is not None
            or resolution.confirmation_ids
            or resolution.evidence_ids
            or resolution.evidence
            or resolution.reason is not None
        ):
            raise RecoveryError(
                "TARGET_NOT_UNKNOWN",
                "A purchase already has a declaration, source evidence or another resolution.",
            )


def _validate_postcondition(
    report: RealizedGrossReport, plan: PurchaseCurrencyRecoveryPlan
) -> None:
    if (
        asdict(report.counts) != plan.expected_counts.model_dump()
        or report.summary.status != plan.expected_summary_status
    ):
        raise RecoveryError(
            "POSTCONDITION_FAILED", "The regular report did not reach the exact planned result."
        )


def _receipt(confirmation: ExecutionCurrencyConfirmation) -> dict[str, str]:
    return {
        "confirmation_id": str(confirmation.id),
        "execution_id": str(confirmation.execution_id),
        "trade_id": str(confirmation.trade_id),
        "request_id": str(confirmation.request_id),
        "confirmed_at": confirmation.confirmed_at.isoformat(),
    }


async def _inspect_state(
    session: AsyncSession, plan: PurchaseCurrencyRecoveryPlan
) -> dict[str, object]:
    snapshot = await read_snapshot(session, plan.workspace_id, plan.currency)
    report = build_report(snapshot, plan.filters.to_domain())
    _validate_targets(snapshot, report, plan)
    repository = SqlAlchemyExecutionCurrencyConfirmationRepository(session)
    own: list[ExecutionCurrencyConfirmation] = []
    for target in _ordered_targets(plan):
        found = await repository.find_request(plan.workspace_id, recovery_request_id(plan, target))
        if found is not None:
            own.append(found)
    if own and len(own) != len(plan.targets):
        raise RecoveryError(
            "PARTIAL_REPLAY", "Only part of this atomic plan exists; no further writes are allowed."
        )
    if not own:
        _validate_baseline(snapshot, report, plan)
    else:
        sources = {source.execution_id: source for source in report.sources}
        declaration = _declaration(plan)
        for target, confirmation in zip(_ordered_targets(plan), own, strict=True):
            source = sources[target.execution_id]
            expected_fingerprint = confirmation_fingerprint(
                trade_id=target.trade_id,
                execution_id=target.execution_id,
                declaration=declaration,
                supersedes_confirmation_id=None,
            )
            if (
                confirmation.workspace_id != plan.workspace_id
                or confirmation.trade_id != target.trade_id
                or confirmation.execution_id != target.execution_id
                or confirmation.currency_code != plan.currency
                or confirmation.source != ExecutionCurrencySource.USER_CONFIRMED
                or confirmation.note != plan.note
                or confirmation.confirmed_by != plan.actor_id
                or confirmation.supersedes_confirmation_id is not None
                or confirmation.request_id != recovery_request_id(plan, target)
                or confirmation.request_fingerprint != expected_fingerprint
                or source.currency_confirmation is None
                or source.currency_confirmation.id != confirmation.id
                or len(source.currency_history) != 1
                or source.currency_resolution.source != "USER_CONFIRMED"
                or source.currency_resolution.currency_code != plan.currency
                or source.currency_resolution.confirmation_ids != (confirmation.id,)
            ):
                raise RecoveryError(
                    "REPLAY_CONFLICT",
                    "A recovery receipt differs or is no longer the current declaration.",
                )
        own_ids = {confirmation.id for confirmation in own}
        if len(own_ids) != len(plan.targets) or not own_ids.issubset(
            {confirmation.id for confirmation in snapshot.confirmations}
        ):
            raise RecoveryError("REPLAY_CONFLICT", "Recovery receipts are inconsistent.")
        # Remove ONLY this plan's verified rows. Every other fact, including all
        # raw amounts, evidence, history and unrelated executions, stays bound to
        # the original complete report basis without exporting those values.
        baseline = replace(
            snapshot,
            confirmations=tuple(
                confirmation
                for confirmation in snapshot.confirmations
                if confirmation.id not in own_ids
            ),
        )
        _validate_baseline(baseline, build_report(baseline, plan.filters.to_domain()), plan)
        _validate_postcondition(report, plan)
    return {
        "status": "ALREADY_APPLIED" if own else "READY",
        "plan_fingerprint": plan_fingerprint(plan),
        "workspace_id": str(plan.workspace_id),
        "currency": plan.currency,
        "target_count": len(plan.targets),
        "expected_basis": plan.expected_basis,
        "actual_basis": report.basis.id,
        "counts": asdict(report.counts),
        "summary_status": report.summary.status,
        "confirmations_created": 0,
        "confirmations": [_receipt(confirmation) for confirmation in own],
    }


async def inspect_plan(
    session: AsyncSession, plan: PurchaseCurrencyRecoveryPlan
) -> dict[str, object]:
    """Read-only comparison; caller supplies a stable snapshot or maintenance locks."""
    return await _inspect_state(session, plan)


async def apply_plan(
    connection: AsyncConnection, plan: PurchaseCurrencyRecoveryPlan
) -> dict[str, object]:
    """Apply all declarations or none; the caller must roll back on every exception.

    This function does not commit the outer transaction. The CLI additionally
    verifies from a fresh read-only transaction after the commit completes.
    """
    if not connection.in_transaction():
        raise RecoveryError("OUTER_TRANSACTION_REQUIRED", "An outer transaction is required.")
    outer = connection.get_transaction()
    isolation = await connection.scalar(text("SHOW transaction_isolation"))
    if isolation != "read committed":
        raise RecoveryError("ISOLATION_REQUIRED", "Recovery requires READ COMMITTED isolation.")
    await connection.execute(text("SET LOCAL lock_timeout = '1s'"))
    await connection.execute(text("SET LOCAL statement_timeout = '10000ms'"))
    # These are exactly the tables materialized by the report plus the currency
    # catalogue. A short maintenance lock serializes ordinary owners/imports as
    # well as phantom inserts; unrelated readers remain permitted. NOWAIT also
    # avoids lock-order deadlocks with an owner already holding a product/trade.
    await connection.execute(
        text(
            "LOCK TABLE currencies, warrants, trades, positions, execution_records, "
            "execution_currency_confirmations, currency_source_evidence "
            "IN SHARE ROW EXCLUSIVE MODE NOWAIT"
        )
    )
    async with AsyncSession(
        bind=connection,
        expire_on_commit=False,
        autoflush=False,
        join_transaction_mode="create_savepoint",
    ) as session:
        products = set(
            await session.scalars(
                select(WarrantModel.id)
                .where(
                    WarrantModel.workspace_id == plan.workspace_id,
                    WarrantModel.id.in_({target.product_id for target in plan.targets}),
                )
                .order_by(WarrantModel.id)
                .with_for_update(nowait=True)
            )
        )
        trades = set(
            await session.scalars(
                select(TradeModel.id)
                .where(
                    TradeModel.workspace_id == plan.workspace_id,
                    TradeModel.id.in_({target.trade_id for target in plan.targets}),
                )
                .order_by(TradeModel.id)
                .with_for_update(nowait=True)
            )
        )
        if products != {target.product_id for target in plan.targets} or trades != {
            target.trade_id for target in plan.targets
        }:
            raise RecoveryError("TARGET_NOT_EFFECTIVE", "The exact product/trade scope is missing.")
        before = await inspect_plan(session, plan)
        if before["status"] == "ALREADY_APPLIED":
            return before
        service = ExecutionCurrencyConfirmationService(session)
        declaration = _declaration(plan)
        for target in _ordered_targets(plan):
            await service.confirm(
                workspace_id=plan.workspace_id,
                trade_id=target.trade_id,
                execution_id=target.execution_id,
                declaration=declaration,
                actor=plan.actor_id,
                request_id=recovery_request_id(plan, target),
                supersedes_confirmation_id=None,
            )
            if connection.get_transaction() is not outer or not connection.in_transaction():
                raise RecoveryError(
                    "OUTER_TRANSACTION_LOST", "The owner did not preserve the outer transaction."
                )
        # Do not re-check UNKNOWN eligibility between purchases: an earlier BUY
        # may make a later one derivable. All planned direct declarations were
        # validated against the one locked baseline before the first write.
        after = await _inspect_state(session, plan)
        if after["status"] != "ALREADY_APPLIED":
            raise RecoveryError("POSTCONDITION_FAILED", "The complete recovery is not visible.")
        return after | {"status": "APPLIED", "confirmations_created": len(plan.targets)}


async def _readonly_inspect(
    engine: AsyncEngine, plan: PurchaseCurrencyRecoveryPlan
) -> dict[str, object]:
    async with engine.connect() as connection, connection.begin():
        await connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
        await connection.execute(text("SET LOCAL statement_timeout = '10000ms'"))
        async with AsyncSession(
            bind=connection,
            expire_on_commit=False,
            autoflush=False,
            join_transaction_mode="create_savepoint",
        ) as session:
            return await inspect_plan(session, plan)


async def run(mode: str, plan: PurchaseCurrencyRecoveryPlan) -> dict[str, object]:
    if mode not in {"preview", "apply", "verify"}:
        raise RecoveryError("INVALID_MODE", "Expected preview, apply or verify.")
    # This is a separate maintenance process; even a diagnostic application
    # configuration must not emit SQL parameters or money into its receipts.
    database = DatabaseManager(get_settings().model_copy(update={"database_echo": False}))
    try:
        if mode in {"preview", "verify"}:
            inspected = await _readonly_inspect(database.engine, plan)
            if mode == "verify" and inspected["status"] != "ALREADY_APPLIED":
                raise RecoveryError("NOT_APPLIED", "The complete recovery has not been applied.")
            return inspected
        prepared = False
        try:
            async with database.engine.begin() as connection:
                result = await apply_plan(connection, plan)
                prepared = True
        except Exception as error:
            if prepared:
                raise RecoveryError(
                    "COMMIT_OUTCOME_UNKNOWN",
                    "The commit acknowledgement failed. Verify or replay this exact plan "
                    "before taking any other recovery action.",
                ) from error
            raise
        try:
            verified = await _readonly_inspect(database.engine, plan)
            if verified["status"] != "ALREADY_APPLIED":
                raise RecoveryError("NOT_APPLIED", "The committed recovery was not found.")
        except Exception as error:
            raise RecoveryError(
                "POST_COMMIT_VERIFICATION_FAILED",
                "The commit completed but fresh verification failed. Preserve the plan and "
                "verify its exact state; do not assume that nothing was written.",
            ) from error
        return verified | {
            "status": result["status"],
            "confirmations_created": result["confirmations_created"],
            "verified_after_commit": True,
        }
    finally:
        await database.dispose()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("preview", "apply", "verify"))
    parser.add_argument("--plan", default="-", help="Private JSON plan, or - for standard input")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.plan == "-":
            raw = sys.stdin.buffer.read(MAX_PLAN_BYTES + 1)
        else:
            with Path(args.plan).open("rb") as handle:
                raw = handle.read(MAX_PLAN_BYTES + 1)
        if len(raw) > MAX_PLAN_BYTES:
            raise RecoveryError("INVALID_PLAN", "The plan exceeds the supported size.")
        try:
            plan = PurchaseCurrencyRecoveryPlan.model_validate_json(raw)
        except ValidationError as error:
            raise RecoveryError(
                "INVALID_PLAN", "The private plan does not match the strict recovery schema."
            ) from error
        result = asyncio.run(run(args.mode, plan))
    except RecoveryError as error:
        print(json.dumps({"status": "ERROR", "code": error.code, "message": error.message}))
        return 1
    except SQLAlchemyError:
        print(
            json.dumps(
                {
                    "status": "ERROR",
                    "code": "DATABASE_REJECTED",
                    "message": "Database access or the maintenance lock failed. Preserve the "
                    "plan and verify its exact state before retrying.",
                }
            )
        )
        return 1
    except (KeyboardInterrupt, asyncio.CancelledError):
        print(
            json.dumps(
                {
                    "status": "ERROR",
                    "code": "RECOVERY_INTERRUPTED",
                    "message": "Recovery was interrupted. Preserve the exact plan and verify "
                    "its state before retrying.",
                }
            )
        )
        return 1
    except Exception:
        # Database drivers and validation exceptions may contain URLs, bound
        # financial data or private plan fields. Never emit their repr/traceback.
        print(
            json.dumps(
                {
                    "status": "ERROR",
                    "code": "RECOVERY_FAILED",
                    "message": "Recovery did not finish successfully. Preserve the exact plan "
                    "and verify its state before retrying.",
                }
            )
        )
        return 1
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
