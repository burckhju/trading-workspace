"""Independent arithmetic examples, not a currency-qualified period report.

The reference case assumes EUR solely for its synthetic prices. ExecutionRecord
does not itself establish that currency. Selecting the named September fixture
IDs below is an oracle for the example, not a production period/date contract.
"""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from app.features.trade_position.domain.enums import ExecutionSide, TradeOrigin
from app.features.trade_position.domain.models import ExecutionRecord, Trade
from app.features.trade_position.domain.projector import (
    PositionProjectionTrace,
    PositionProjector,
)

POSITION_ID = UUID(int=5)
RECORDED_AT = datetime(2026, 10, 17, 12, tzinfo=UTC)


def _trade() -> Trade:
    return Trade(
        id=UUID(int=1),
        workspace_id=UUID(int=2),
        product_id=UUID(int=3),
        origin=TradeOrigin.EXTERNAL,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        created_by=UUID(int=4),
    )


def _execution(
    trade: Trade,
    *,
    number: int,
    side: ExecutionSide,
    quantity: int,
    price: str,
    day: str,
) -> ExecutionRecord:
    return ExecutionRecord(
        id=UUID(int=number),
        trade_id=trade.id,
        product_id=trade.product_id,
        quantity=quantity,
        price_per_unit=Decimal(price),
        executed_at=datetime.fromisoformat(f"{day}T12:00:00+00:00"),
        recorded_at=RECORDED_AT,
        recorded_by=trade.created_by,
        side=side,
    )


def _reference_history(trade: Trade) -> list[ExecutionRecord]:
    rows = [
        (10, ExecutionSide.BUY, 100, "2.00", "2026-08-05"),
        (11, ExecutionSide.SELL, 20, "2.50", "2026-08-12"),
        (12, ExecutionSide.SELL, 30, "3.00", "2026-09-02"),
        (13, ExecutionSide.BUY, 50, "4.00", "2026-09-06"),
        (14, ExecutionSide.SELL, 40, "2.50", "2026-09-12"),
        (15, ExecutionSide.SELL, 60, "3.50", "2026-10-03"),
    ]
    return [
        _execution(trade, number=number, side=side, quantity=quantity, price=price, day=day)
        for number, side, quantity, price, day in rows
    ]


def _trace(trade: Trade, history: list[ExecutionRecord]) -> PositionProjectionTrace:
    result = PositionProjector.project_with_trace(id=POSITION_ID, trade=trade, executions=history)
    assert result.position == PositionProjector.project(
        id=POSITION_ID, trade=trade, executions=history
    )
    assert (
        sum((sale.realized_gross_pnl_delta for sale in result.sells), Decimal("0"))
        == result.position.realized_gross_pnl
    )
    return result


def test_reference_contributions_and_full_cost_basis_provenance() -> None:
    trade = _trade()
    history = _reference_history(trade)
    result = _trace(trade, list(reversed(history)))

    assert result.ordered_executions == tuple(history)
    assert [sale.execution_index for sale in result.sells] == [1, 2, 4, 5]
    assert [sale.realized_gross_pnl_delta for sale in result.sells] == [
        Decimal("10.00"),
        Decimal("30.00"),
        Decimal("-20.00"),
        Decimal("30.00"),
    ]
    assert [sale.average_cost_per_unit for sale in result.sells] == [
        Decimal("2.00"),
        Decimal("2.00"),
        Decimal("3.00"),
        Decimal("3.00"),
    ]
    assert [sale.open_quantity_before for sale in result.sells] == [100, 80, 100, 60]
    assert [sale.cost_basis_before for sale in result.sells] == [
        Decimal("200.00"),
        Decimal("160.00"),
        Decimal("300.00"),
        Decimal("180.00"),
    ]
    assert [sale.open_quantity_after for sale in result.sells] == [80, 50, 60, 0]
    assert [sale.cost_basis_after for sale in result.sells] == [
        Decimal("160.00"),
        Decimal("100.00"),
        Decimal("180.00"),
        Decimal("0"),
    ]
    assert [sale.cost_basis_before_close_reset for sale in result.sells] == [
        None,
        None,
        None,
        Decimal("0.00"),
    ]
    assert result.position.realized_gross_pnl == Decimal("50.00")
    assert result.position.is_closed

    september_ids = {UUID(int=12), UUID(int=14)}
    september = [
        sale
        for sale in result.sells
        if result.ordered_executions[sale.execution_index].id in september_ids
    ]
    assert len(september) == 2
    assert sum((sale.realized_gross_pnl_delta for sale in september), Decimal("0")) == Decimal(
        "10.00"
    )
    assert [
        tuple(execution.id for execution in result.ordered_executions[: sale.execution_index])
        for sale in september
    ] == [
        (UUID(int=10), UUID(int=11)),
        (UUID(int=10), UUID(int=11), UUID(int=12), UUID(int=13)),
    ]


def test_reference_september_sales_already_exist_while_trade_is_open() -> None:
    trade = _trade()
    result = _trace(trade, _reference_history(trade)[:-1])

    assert not result.position.is_closed
    assert result.position.closed_at is None
    assert result.position.open_quantity == 60
    assert result.position.cost_basis == Decimal("180.00")
    assert result.position.average_entry_price == Decimal("3.00")
    assert result.position.realized_gross_pnl == Decimal("20.00")
    assert [sale.realized_gross_pnl_delta for sale in result.sells] == [
        Decimal("10.00"),
        Decimal("30.00"),
        Decimal("-20.00"),
    ]


def test_explicit_effective_correction_preserves_original_and_changes_only_current_trace() -> None:
    trade = _trade()
    history = _reference_history(trade)
    original_result = _trace(trade, history)
    original = history[4]
    replacement = replace(
        original,
        id=UUID(int=16),
        price_per_unit=Decimal("3.00"),
        recorded_at=RECORDED_AT + timedelta(hours=1),
        supersedes_execution_id=original.id,
    )
    # The repository owns effectiveness. This unit fixture explicitly supplies its
    # expected effective result; no SQL or supersession selection is simulated here.
    effective = [history[0], history[1], history[2], history[3], replacement, history[5]]
    result = _trace(trade, effective)

    assert [sale.realized_gross_pnl_delta for sale in result.sells] == [
        Decimal("10.00"),
        Decimal("30.00"),
        Decimal("0.00"),
        Decimal("30.00"),
    ]
    assert result.position.realized_gross_pnl == Decimal("70.00")
    assert result.sells[1].realized_gross_pnl_delta + result.sells[2].realized_gross_pnl_delta == (
        Decimal("30.00")
    )
    assert original not in result.ordered_executions
    assert result.ordered_executions[4] is replacement
    assert result.ordered_executions[4].supersedes_execution_id == original.id
    assert original.price_per_unit == Decimal("2.50")
    assert original.recorded_at == RECORDED_AT
    assert original_result.ordered_executions[4] is original
    assert original_result.sells[2].realized_gross_pnl_delta == Decimal("-20.00")
    assert original_result.position.realized_gross_pnl == Decimal("50.00")


def test_buy_only_has_no_sell_contributions() -> None:
    trade = _trade()
    history = _reference_history(trade)
    result = _trace(trade, [history[0], history[3]])

    assert result.sells == ()
    assert result.position.realized_gross_pnl == Decimal("0")
    assert result.position.open_quantity == 150
    assert result.position.cost_basis == Decimal("400.00")


def test_repeating_decimals_preserve_original_operations_and_expose_close_residue() -> None:
    trade = _trade()
    rows = [
        (ExecutionSide.BUY, 1, "1"),
        (ExecutionSide.BUY, 2, "2"),
        (ExecutionSide.SELL, 1, "2"),
        (ExecutionSide.BUY, 1, "1"),
        (ExecutionSide.SELL, 1, "2"),
        (ExecutionSide.SELL, 2, "2"),
    ]
    history = [
        _execution(
            trade,
            number=20 + index,
            side=side,
            quantity=quantity,
            price=price,
            day=f"2026-01-{index + 1:02d}",
        )
        for index, (side, quantity, price) in enumerate(rows)
    ]

    # Fixed independent golden values for the existing default Decimal contract.
    # This local test context does not change the production projector's context.
    with localcontext() as context:
        context.prec = 28
        context.rounding = ROUND_HALF_EVEN
        result = _trace(trade, history)

    assert [sale.average_cost_per_unit for sale in result.sells] == [
        Decimal("1.666666666666666666666666667"),
        Decimal("1.444444444444444444444444444"),
        Decimal("1.444444444444444444444444444"),
    ]
    assert [sale.realized_gross_pnl_delta for sale in result.sells] == [
        Decimal("0.333333333333333333333333333"),
        Decimal("0.555555555555555555555555556"),
        Decimal("1.111111111111111111111111112"),
    ]
    assert result.sells[2].cost_basis_before == Decimal("2.888888888888888888888888889")
    assert result.sells[2].cost_basis_before_close_reset == Decimal("0.000000000000000000000000001")
    assert result.sells[2].cost_basis_after == Decimal("0")
    assert result.position.cost_basis == Decimal("0")
    assert result.position.realized_gross_pnl == Decimal("2.000000000000000000000000001")


def test_equal_execution_instants_keep_recording_order_then_uuid_order() -> None:
    trade = _trade()
    history = [
        _execution(
            trade, number=30, side=ExecutionSide.BUY, quantity=3, price="1", day="2026-08-01"
        ),
        _execution(
            trade, number=10, side=ExecutionSide.SELL, quantity=1, price="2", day="2026-08-01"
        ),
        _execution(
            trade, number=20, side=ExecutionSide.BUY, quantity=2, price="3", day="2026-08-01"
        ),
        _execution(
            trade, number=40, side=ExecutionSide.SELL, quantity=1, price="4", day="2026-08-01"
        ),
    ]
    history[0] = replace(history[0], recorded_at=RECORDED_AT - timedelta(hours=1))
    result = _trace(trade, [history[3], history[2], history[0], history[1]])

    assert result.ordered_executions == tuple(history)
    assert [sale.execution_index for sale in result.sells] == [1, 3]
    assert [sale.realized_gross_pnl_delta for sale in result.sells] == [Decimal("1"), Decimal("2")]
    assert result.sells[1].cost_basis_before == Decimal("8")
    assert result.sells[1].average_cost_per_unit == Decimal("2")


@pytest.mark.parametrize(
    "day, anchor",
    [
        (date(2026, 3, 29), datetime(2026, 3, 28, 23, tzinfo=UTC)),
        (date(2026, 3, 30), datetime(2026, 3, 29, 22, tzinfo=UTC)),
        (date(2026, 10, 25), datetime(2026, 10, 24, 22, tzinfo=UTC)),
        (date(2026, 10, 26), datetime(2026, 10, 25, 23, tzinfo=UTC)),
    ],
)
def test_trace_retains_date_only_precision_and_dst_anchor(day: date, anchor: datetime) -> None:
    trade = _trade()
    bought = _reference_history(trade)[0]
    bought = replace(bought, executed_at=anchor - timedelta(days=1), recorded_at=anchor)
    sold = replace(
        bought,
        id=UUID(int=40),
        side=ExecutionSide.SELL,
        price_per_unit=Decimal("3.00"),
        executed_at=anchor,
        executed_on=day,
        execution_timezone="Europe/Berlin",
        recorded_at=anchor + timedelta(days=2),
    )
    result = _trace(trade, [sold, bought])

    assert result.ordered_executions == (bought, sold)
    source = result.ordered_executions[result.sells[0].execution_index]
    assert source is sold
    assert source.executed_on == day
    assert source.execution_timezone == "Europe/Berlin"
    assert source.executed_at == anchor
    assert source.executed_at.astimezone(ZoneInfo("Europe/Berlin")).date() == day
    assert source.recorded_at == anchor + timedelta(days=2)
    assert result.position.closed_on == day


def test_trace_snapshots_do_not_mutate_inputs_and_cannot_be_modified() -> None:
    trade = _trade()
    history = _reference_history(trade)
    input_list = list(reversed(history))
    before = tuple(input_list)
    result = _trace(trade, input_list)

    assert tuple(input_list) == before
    input_list.clear()
    assert result.ordered_executions == tuple(history)
    assert result.ordered_executions[0] is history[0]
    with pytest.raises(FrozenInstanceError):
        result.position = result.position
    with pytest.raises(FrozenInstanceError):
        result.sells[0].cost_basis_before = Decimal("999")
    with pytest.raises(FrozenInstanceError):
        result.ordered_executions[0].price_per_unit = Decimal("999")


@pytest.mark.parametrize(
    "case, error",
    [
        ("empty", "position projection requires execution history"),
        ("sell_first", "SELL execution requires prior open quantity"),
        ("oversell", "SELL quantity exceeds current open quantity"),
        ("reopen", "closed trade must not be reopened by BUY execution"),
        ("wrong_trade", "execution does not belong to trade"),
        ("wrong_product", "execution product does not match trade"),
    ],
)
def test_trace_preserves_existing_projection_rejections(case: str, error: str) -> None:
    trade = _trade()
    history = _reference_history(trade)
    cases = {
        "empty": [],
        "sell_first": [history[1]],
        "oversell": [history[0], replace(history[1], quantity=101)],
        "reopen": [history[0], replace(history[1], quantity=100), history[3]],
        "wrong_trade": [replace(history[0], trade_id=UUID(int=90))],
        "wrong_product": [replace(history[0], product_id=UUID(int=91))],
    }

    for project in (PositionProjector.project, PositionProjector.project_with_trace):
        with pytest.raises(ValueError, match=error):
            project(id=POSITION_ID, trade=trade, executions=cases[case])
