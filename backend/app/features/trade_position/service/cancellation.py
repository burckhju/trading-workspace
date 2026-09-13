"""Explicit, auditable cancellation of a purchase-only entry mistake.

The economic execution/position facts are retained. Cancellation is not a sale.
The caller cannot alter another trade; duplicate_of is a checked reference only.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.types import ApplicationError
from app.features.alert.persistence.models import AlertModel
from app.features.market.domain.enums import ActorType, AggregateType, ChangeType, DataOrigin
from app.features.market.persistence.models import AuditEventModel
from app.features.notification.persistence.models import NotificationModel
from app.features.trade_position.persistence.models import (
    ExecutionRecordModel,
    PositionModel,
    TradeManagementEventModel,
    TradeModel,
)
from app.features.trade_position.service.errors import capture_conflict


class TradeCancellationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _trade(self, workspace_id: UUID, trade_id: UUID) -> TradeModel:
        model = await self._session.scalar(
            select(TradeModel)
            .where(TradeModel.workspace_id == workspace_id, TradeModel.id == trade_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if model is None:
            raise ApplicationError(
                code="TRADE_NOT_FOUND", message="Trade nicht gefunden.", status_code=404
            )
        return model

    async def preview(self, workspace_id: UUID, trade_id: UUID) -> dict[str, Any]:
        trade = await self._trade(workspace_id, trade_id)
        position = await self._session.scalar(
            select(PositionModel).where(PositionModel.trade_id == trade.id)
        )
        records = (
            await self._session.scalars(
                select(ExecutionRecordModel)
                .where(ExecutionRecordModel.trade_id == trade.id)
                .order_by(ExecutionRecordModel.id)
            )
        ).all()
        management_ids = tuple(
            (
                await self._session.scalars(
                    select(TradeManagementEventModel.id)
                    .where(TradeManagementEventModel.trade_id == trade.id)
                    .order_by(TradeManagementEventModel.id)
                )
            ).all()
        )
        blockers = []
        if position is None or position.open_quantity == 0:
            blockers.append("Nur eine noch offene, reine Kauferfassung kann hier storniert werden.")
        if not records or any(record.side == "SELL" for record in records):
            blockers.append(
                "Verkäufe oder fehlende Kaufhistorie: eine gesonderte Korrektur ist erforderlich."
            )
        for table in (
            "post_trade_observations",
            "trade_journals",
            "ft011_evidence",
            "external_observation_trade_link_versions",
        ):
            # Fixed application table identifiers, never user input.
            if await self._session.scalar(
                text(f"SELECT EXISTS(SELECT 1 FROM {table} WHERE trade_id=:id)"), {"id": trade.id}
            ):
                blockers.append(f"Abhängige Nachbeobachtungs-/Lerndaten vorhanden ({table}).")
        sending = await self._session.scalar(
            text("""
            SELECT EXISTS(SELECT 1 FROM notification_delivery_attempts d
            JOIN notifications n ON n.id=d.notification_id JOIN alerts a ON a.id=n.alert_id
            WHERE a.trade_id=:id AND d.status='IN_PROGRESS')
        """),
            {"id": trade.id},
        )
        if sending:
            blockers.append(
                "Eine Benachrichtigung wird gerade versendet. Abschluss abwarten und erneut prüfen."
            )
        other_ids = list(
            (
                await self._session.scalars(
                    select(TradeModel.id)
                    .join(PositionModel, PositionModel.trade_id == TradeModel.id)
                    .where(
                        TradeModel.workspace_id == workspace_id,
                        TradeModel.product_id == trade.product_id,
                        TradeModel.id != trade_id,
                        TradeModel.cancelled_at.is_(None),
                        PositionModel.open_quantity > 0,
                    )
                    .order_by(TradeModel.id)
                )
            ).all()
        )
        facts = {
            "trade_id": str(trade.id),
            "product_id": str(trade.product_id),
            "created_at": trade.created_at.isoformat(),
            "cancelled_at": trade.cancelled_at.isoformat() if trade.cancelled_at else None,
            "cancelled_by": str(trade.cancelled_by) if trade.cancelled_by else None,
            "reason": trade.cancellation_reason,
            "duplicate_of_trade_id": (
                str(trade.duplicate_of_trade_id) if trade.duplicate_of_trade_id else None
            ),
            "open_quantity": position.open_quantity if position else None,
            "cost_basis": str(position.cost_basis) if position else None,
            "opened_at": position.opened_at.isoformat() if position else None,
            "other_open_trade_ids": [str(value) for value in other_ids],
            "executions": [
                {
                    "id": str(r.id),
                    "side": r.side,
                    "quantity": r.quantity,
                    "price_per_unit": str(r.price_per_unit),
                    "executed_at": r.executed_at.isoformat(),
                    "recorded_at": r.recorded_at.isoformat(),
                    "executed_on": r.executed_on.isoformat() if r.executed_on else None,
                    "execution_timezone": r.execution_timezone,
                    "supersedes_id": (
                        str(r.supersedes_execution_id) if r.supersedes_execution_id else None
                    ),
                }
                for r in records
            ],
            "blockers": blockers,
            "can_cancel": trade.cancelled_at is None and not blockers,
        }
        fingerprint = {**facts, "management_ids": [str(value) for value in management_ids]}
        facts["state_token"] = hashlib.sha256(
            json.dumps(fingerprint, sort_keys=True).encode()
        ).hexdigest()
        return facts

    async def cancel(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        expected_product_id: UUID,
        expected_state_token: str,
        reason: str,
        actor: UUID,
        duplicate_of_trade_id: UUID | None = None,
    ) -> dict[str, Any]:
        reason = reason.strip()
        if not reason or len(reason) > 1000:
            raise ApplicationError(
                code="CANCELLATION_REASON_REQUIRED",
                message="Bitte einen Stornogrund angeben (maximal 1000 Zeichen).",
                status_code=422,
            )
        try:
            if duplicate_of_trade_id is not None:
                await self._session.scalars(
                    select(TradeModel.id)
                    .where(
                        TradeModel.workspace_id == workspace_id,
                        TradeModel.id.in_([trade_id, duplicate_of_trade_id]),
                    )
                    .order_by(TradeModel.id)
                    .with_for_update()
                )
            trade = await self._trade(workspace_id, trade_id)
            if trade.product_id != expected_product_id:
                raise capture_conflict(
                    "CANCELLATION_PRODUCT_CONFLICT",
                    "Die Produktzuordnung stimmt nicht mit der geprüften Vorschau überein.",
                )
            if trade.cancelled_at is not None:
                if (
                    trade.cancellation_reason != reason
                    or trade.duplicate_of_trade_id != duplicate_of_trade_id
                ):
                    raise capture_conflict(
                        "TRADE_ALREADY_CANCELLED",
                        "Dieser Trade wurde bereits mit anderem Stornogrund storniert.",
                    )
                # Lost response / retry: never modify facts or emit another audit record.
                return await self.preview(workspace_id, trade_id)
            preview = await self.preview(workspace_id, trade_id)
            if preview["state_token"] != expected_state_token:
                raise capture_conflict(
                    "CANCELLATION_STALE",
                    "Der Trade wurde zwischenzeitlich verändert. Bitte die "
                    "Stornovorschau neu laden.",
                )
            if not preview["can_cancel"]:
                raise capture_conflict("CANCELLATION_BLOCKED", " ".join(preview["blockers"]))
            if (
                duplicate_of_trade_id is not None
                and str(duplicate_of_trade_id) not in preview["other_open_trade_ids"]
            ):
                raise capture_conflict(
                    "CANCELLATION_DUPLICATE_CONFLICT",
                    "Der beizubehaltende Trade muss offen sein und zum selben "
                    "Optionsschein gehören.",
                )
            now = datetime.now(UTC)
            trade.cancelled_at = now
            trade.cancelled_by = actor
            trade.cancellation_reason = reason
            trade.duplicate_of_trade_id = duplicate_of_trade_id
            # Force cancellation validation before changing derived alert delivery state.
            await self._session.flush()
            await self._session.execute(
                update(AlertModel)
                .where(AlertModel.trade_id == trade.id, AlertModel.status == "OPEN")
                .values(status="RESOLVED", resolved_at=now)
            )
            await self._session.execute(
                update(NotificationModel)
                .where(
                    NotificationModel.alert_id.in_(
                        select(AlertModel.id).where(AlertModel.trade_id == trade.id)
                    ),
                    NotificationModel.status == "PENDING",
                )
                .values(status="FAILED")
            )
            self._session.add(
                AuditEventModel(
                    id=uuid4(),
                    workspace_id=workspace_id,
                    aggregate_type=AggregateType.TRADE,
                    aggregate_id=trade.id,
                    occurred_at=now,
                    actor_type=ActorType.SYSTEM_USER,
                    actor_id=str(actor),
                    actor_display_name=str(actor),
                    data_origin=DataOrigin.MANUAL,
                    change_type=ChangeType.DEACTIVATED,
                    version_before=None,
                    version_after=None,
                    field_changes={
                        "cancellation": {
                            "before": None,
                            "after": {
                                "reason": reason,
                                "duplicate_of_trade_id": (
                                    str(duplicate_of_trade_id) if duplicate_of_trade_id else None
                                ),
                                "cancelled_at": now.isoformat(),
                            },
                        }
                    },
                )
            )
            await self._session.commit()
            return await self.preview(workspace_id, trade_id)
        except Exception:
            await self._session.rollback()
            raise
