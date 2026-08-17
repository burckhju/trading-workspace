"""FT-010 composed trade timeline and FT-011 handoff state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from app.features.trade_position.domain.enums import ExecutionSide, TradeManagementEventType
from app.features.trade_position.domain.models import (
    ExecutionRecord,
    Position,
    TradeManagementEvent,
)


class TradeTimelineEntryKind(StrEnum):
    EXECUTION = "EXECUTION"
    MANAGEMENT_EVENT = "MANAGEMENT_EVENT"


@dataclass(frozen=True, slots=True)
class TradeTimelineEntry:
    id: UUID
    trade_id: UUID
    occurred_at: datetime
    recorded_at: datetime
    kind: TradeTimelineEntryKind
    execution_side: ExecutionSide | None = None
    management_event_type: TradeManagementEventType | None = None
    quantity: int | None = None
    price_per_unit: Decimal | None = None
    numeric_value: Decimal | None = None
    text_value: str | None = None
    supersedes_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class Ft011Eligibility:
    trade_id: UUID
    eligible: bool
    reason: str


def compose_trade_timeline(
    *,
    trade_id: UUID,
    executions: list[ExecutionRecord],
    management_events: list[TradeManagementEvent],
) -> list[TradeTimelineEntry]:
    entries: list[TradeTimelineEntry] = []

    for execution in executions:
        if execution.trade_id != trade_id:
            raise ValueError("execution does not belong to trade")
        entries.append(
            TradeTimelineEntry(
                id=execution.id,
                trade_id=trade_id,
                occurred_at=execution.executed_at,
                recorded_at=execution.recorded_at,
                kind=TradeTimelineEntryKind.EXECUTION,
                execution_side=execution.side,
                quantity=execution.quantity,
                price_per_unit=execution.price_per_unit,
                supersedes_id=execution.supersedes_execution_id,
            )
        )

    for event in management_events:
        if event.trade_id != trade_id:
            raise ValueError("management event does not belong to trade")
        entries.append(
            TradeTimelineEntry(
                id=event.id,
                trade_id=trade_id,
                occurred_at=event.effective_at,
                recorded_at=event.recorded_at,
                kind=TradeTimelineEntryKind.MANAGEMENT_EVENT,
                management_event_type=event.event_type,
                numeric_value=event.numeric_value,
                text_value=event.text_value,
                supersedes_id=event.supersedes_event_id,
            )
        )

    return sorted(
        entries,
        key=lambda item: (item.occurred_at, item.recorded_at, item.id),
    )


def ft011_eligibility(position: Position) -> Ft011Eligibility:
    if position.is_closed:
        return Ft011Eligibility(
            trade_id=position.trade_id,
            eligible=True,
            reason="trade position is fully closed",
        )
    return Ft011Eligibility(
        trade_id=position.trade_id,
        eligible=False,
        reason="trade position still has open quantity",
    )
