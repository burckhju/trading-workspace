"""Deterministic FT-010 current management state projection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.features.trade_position.domain.enums import TradeManagementEventType
from app.features.trade_position.domain.models import TradeManagementEvent


@dataclass(frozen=True, slots=True)
class TradeManagementState:
    trade_id: UUID
    stop_price: Decimal | None = None
    target_price: Decimal | None = None
    thesis: str | None = None
    notes: tuple[str, ...] = ()
    last_event_at: datetime | None = None


class TradeManagementStateProjector:
    @staticmethod
    def project(
        *,
        trade_id: UUID,
        events: list[TradeManagementEvent],
    ) -> TradeManagementState:
        state = TradeManagementState(trade_id=trade_id)

        for event in sorted(
            events,
            key=lambda item: (
                item.effective_at,
                item.recorded_at,
                item.id,
            ),
        ):
            if event.trade_id != trade_id:
                raise ValueError("management event does not belong to trade")

            if event.event_type is TradeManagementEventType.STOP_CHANGED:
                state = TradeManagementState(
                    trade_id=trade_id,
                    stop_price=event.numeric_value,
                    target_price=state.target_price,
                    thesis=state.thesis,
                    notes=state.notes,
                    last_event_at=event.effective_at,
                )
            elif event.event_type is TradeManagementEventType.TARGET_CHANGED:
                state = TradeManagementState(
                    trade_id=trade_id,
                    stop_price=state.stop_price,
                    target_price=event.numeric_value,
                    thesis=state.thesis,
                    notes=state.notes,
                    last_event_at=event.effective_at,
                )
            elif event.event_type is TradeManagementEventType.THESIS_UPDATED:
                state = TradeManagementState(
                    trade_id=trade_id,
                    stop_price=state.stop_price,
                    target_price=state.target_price,
                    thesis=event.text_value,
                    notes=state.notes,
                    last_event_at=event.effective_at,
                )
            else:
                state = TradeManagementState(
                    trade_id=trade_id,
                    stop_price=state.stop_price,
                    target_price=state.target_price,
                    thesis=state.thesis,
                    notes=(*state.notes, event.text_value or ""),
                    last_event_at=event.effective_at,
                )

        return state
