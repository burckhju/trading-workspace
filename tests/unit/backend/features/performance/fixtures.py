"""Explicit synthetic execution facts and declarations, never inferred currencies."""

from datetime import UTC, date, datetime, time
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from app.features.performance.domain.models import (
    Confirmation,
    CurrencyReference,
    ExecutionFact,
    ReportFilters,
    ReportSnapshot,
    TradeFact,
)
from app.features.trade_position.domain.enums import TradeOrigin
from app.features.trade_position.domain.models import Trade

WORKSPACE = UUID(int=2)
ACTOR = UUID(int=4)
RECORDED = datetime(2031, 1, 1, 12, tzinfo=UTC)
SEPTEMBER = ReportFilters(date(2026, 9, 1), date(2026, 9, 30), "EUR", "Europe/Berlin")


def trade_fact(number: int = 1) -> TradeFact:
    return TradeFact(
        Trade(
            id=UUID(int=number),
            workspace_id=WORKSPACE,
            product_id=UUID(int=number + 1000),
            origin=TradeOrigin.EXTERNAL,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            created_by=ACTOR,
        ),
        "Synthetic current product display",
        UUID(int=number + 2000),
    )


def execution(
    number: int,
    side: str,
    quantity: int,
    price: str,
    day: str,
    *,
    trade: TradeFact | None = None,
    zone: str | None = "Europe/Berlin",
) -> ExecutionFact:
    owner = trade or trade_fact()
    executed_on = date.fromisoformat(day)
    anchor = (
        datetime.combine(executed_on, time.min, ZoneInfo(zone))
        if zone
        else (datetime.combine(executed_on, time(12), UTC))
    )
    return ExecutionFact(
        id=UUID(int=number),
        trade_id=owner.trade.id,
        product_id=owner.trade.product_id,
        side=side,
        quantity=quantity,
        price_per_unit=Decimal(price),
        executed_at=anchor.astimezone(UTC),
        recorded_at=RECORDED,
        recorded_by=ACTOR,
        supersedes_execution_id=None,
        executed_on=executed_on if zone else None,
        execution_timezone=zone,
    )


def reference() -> tuple[ExecutionFact, ...]:
    return (
        execution(101, "BUY", 100, "2.00", "2026-08-05"),
        execution(102, "SELL", 20, "2.50", "2026-08-12"),
        execution(103, "SELL", 30, "3.00", "2026-09-02"),
        execution(104, "BUY", 50, "4.00", "2026-09-06"),
        execution(105, "SELL", 40, "2.50", "2026-09-12"),
        execution(106, "SELL", 60, "3.50", "2026-10-03"),
    )


def confirmed(fact: ExecutionFact, currency: str = "EUR") -> Confirmation:
    return Confirmation(
        id=UUID(int=fact.id.int + 10_000),
        workspace_id=WORKSPACE,
        trade_id=fact.trade_id,
        execution_id=fact.id,
        currency_code=currency,
        source="USER_CONFIRMED",
        note="Explicit synthetic declaration",
        confirmed_at=RECORDED,
        confirmed_by=ACTOR,
        supersedes_confirmation_id=None,
        request_id=UUID(int=fact.id.int + 20_000),
    )


def snapshot(
    executions: tuple[ExecutionFact, ...] | None = None,
    *,
    confirmations: tuple[Confirmation, ...] | None = None,
    trades: tuple[TradeFact, ...] | None = None,
    currency: str = "EUR",
    minor_unit: int = 2,
) -> ReportSnapshot:
    facts = reference() if executions is None else executions
    return ReportSnapshot(
        workspace_id=WORKSPACE,
        trades=trades or (trade_fact(),),
        executions=facts,
        confirmations=(
            tuple(confirmed(fact, currency) for fact in facts)
            if confirmations is None
            else confirmations
        ),
        currency=CurrencyReference(currency, minor_unit, "SYNTHETIC-REFERENCE-v1"),
        read_started_at=RECORDED,
        read_completed_at=RECORDED,
    )


def closed_statistics_snapshot(
    sell_prices: tuple[str, ...] = ("1100", "950", "1000", "1200"),
) -> ReportSnapshot:
    """Buy one at 1000 each; the default independent results are 100/-50/0/200."""
    trades = tuple(trade_fact(index + 1) for index in range(len(sell_prices)))
    facts = tuple(
        fact
        for index, (trade, price) in enumerate(zip(trades, sell_prices, strict=True))
        for fact in (
            execution(101 + index * 100, "BUY", 1, "1000", "2026-08-01", trade=trade),
            execution(102 + index * 100, "SELL", 1, price, "2026-10-03", trade=trade),
        )
    )
    return snapshot(
        facts,
        confirmations=tuple(confirmed(fact) for fact in facts if fact.side == "BUY"),
        trades=trades,
    )
