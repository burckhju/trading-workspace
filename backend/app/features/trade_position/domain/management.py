"""Deterministic FT-010 current management state projection."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.features.trade_position.domain.enums import TradeManagementEventType
from app.features.trade_position.domain.models import TradeManagementEvent
from app.features.trade_position.domain.price_binding import PriceBinding


@dataclass(frozen=True, slots=True)
class TradeManagementState:
    trade_id: UUID
    stop_price: Decimal | None = None
    target_price: Decimal | None = None
    thesis: str | None = None
    notes: tuple[str, ...] = ()
    last_event_at: datetime | None = None
    stop_price_binding: PriceBinding | None = None
    target_price_binding: PriceBinding | None = None


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

            state = replace(state, last_event_at=event.effective_at)
            if event.event_type is TradeManagementEventType.STOP_CHANGED:
                state = replace(
                    state, stop_price=event.numeric_value, stop_price_binding=event.price_binding
                )
            elif event.event_type is TradeManagementEventType.TARGET_CHANGED:
                state = replace(
                    state,
                    target_price=event.numeric_value,
                    target_price_binding=event.price_binding,
                )
            elif event.event_type is TradeManagementEventType.THESIS_UPDATED:
                state = replace(state, thesis=event.text_value)
            else:
                state = replace(state, notes=(*state.notes, event.text_value or ""))

        return state
