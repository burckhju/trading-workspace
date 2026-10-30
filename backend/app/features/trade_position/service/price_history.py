"""Read-only composition of market evidence and exact, effective owner executions."""

from dataclasses import dataclass, fields
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from app.features.market_data.service.warrant_price_history import WarrantPriceHistory
from app.features.trade_position.domain.enums import ExecutionSide
from app.features.trade_position.domain.models import ExecutionRecord, Position


@dataclass(frozen=True)
class HistoricalExecutionEvent:
    id: UUID
    side: ExecutionSide
    occurred_at: datetime | None
    executed_on: date | None
    execution_timezone: str | None
    price: Decimal
    currency: str | None
    currency_source: str
    quantity: int
    plottable: bool
    reason: str | None


@dataclass(frozen=True, kw_only=True)
class PositionPriceHistory(WarrantPriceHistory):
    trade_id: UUID
    position_id: UUID
    events: tuple[HistoricalExecutionEvent, ...]


def compose_price_history(
    position: Position, executions: tuple[ExecutionRecord, ...], history: WarrantPriceHistory
) -> PositionPriceHistory:
    if position.product_id != history.warrant_id or any(
        fact.trade_id != position.trade_id or fact.product_id != position.product_id
        for fact in executions
    ):
        raise ValueError("position history identity mismatch")
    currencies = {series.currency for series in history.series}
    events = []
    for fact in executions:
        # A calendar-date execution's internal midnight anchor is never a chart time.
        if fact.executed_on is not None and fact.execution_timezone is not None:
            zone = ZoneInfo(fact.execution_timezone)
            if fact.executed_on > history.window_end.astimezone(zone).date() or (
                history.window_start is not None
                and fact.executed_on < history.window_start.astimezone(zone).date()
            ):
                continue
        elif fact.executed_at > history.window_end or (
            history.window_start is not None and fact.executed_at < history.window_start
        ):
            continue
        resolution = fact.currency_resolution
        currency = resolution.currency_code
        reason = None
        if fact.executed_on is not None:
            reason = "DATE_ONLY"
        elif not currency or resolution.source in {"UNKNOWN", "MIXED", "CONFLICT"}:
            reason = "CURRENCY_UNKNOWN"
        elif currency not in currencies:
            reason = "NO_MATCHING_QUOTE_CURRENCY"
        events.append(
            HistoricalExecutionEvent(
                fact.id,
                fact.side,
                fact.executed_at if fact.executed_on is None else None,
                fact.executed_on,
                fact.execution_timezone,
                fact.price_per_unit,
                currency,
                resolution.source,
                fact.quantity,
                reason is None,
                reason,
            )
        )
    return PositionPriceHistory(
        **{field.name: getattr(history, field.name) for field in fields(history)},
        trade_id=position.trade_id,
        position_id=position.id,
        events=tuple(events),
    )
