from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.features.trade_position.domain.enums import ExecutionSide, TradeOrigin
from app.features.trade_position.domain.models import ExecutionRecord, Trade
from app.features.trade_position.domain.projector import PositionProjector

T0 = datetime(2026, 8, 17, 8, 0, tzinfo=UTC)


def _trade() -> Trade:
    return Trade(
        id=uuid4(),
        workspace_id=uuid4(),
        product_id=uuid4(),
        origin=TradeOrigin.EXTERNAL,
        created_at=T0,
        created_by=uuid4(),
    )


def _execution(
    trade: Trade,
    *,
    side: ExecutionSide,
    quantity: int,
    price: str,
    minutes: int,
) -> ExecutionRecord:
    executed_at = T0 + timedelta(minutes=minutes)
    return ExecutionRecord(
        id=uuid4(),
        trade_id=trade.id,
        product_id=trade.product_id,
        side=side,
        quantity=quantity,
        price_per_unit=Decimal(price),
        executed_at=executed_at,
        recorded_at=executed_at,
        recorded_by=uuid4(),
    )


def test_project_buy_buy_preserves_weighted_average_cost() -> None:
    trade = _trade()
    first = _execution(
        trade,
        side=ExecutionSide.BUY,
        quantity=100,
        price="1.00",
        minutes=0,
    )
    second = _execution(
        trade,
        side=ExecutionSide.BUY,
        quantity=100,
        price="1.20",
        minutes=1,
    )

    position = PositionProjector.project(
        id=uuid4(),
        trade=trade,
        executions=[second, first],
    )

    assert position.open_quantity == 200
    assert position.cost_basis == Decimal("220.00")
    assert position.average_entry_price == Decimal("1.10")
    assert position.realized_gross_pnl == Decimal("0")
    assert position.closed_at is None
    assert not position.is_closed


def test_project_partial_sell_uses_average_cost_and_keeps_position_open() -> None:
    trade = _trade()
    executions = [
        _execution(
            trade,
            side=ExecutionSide.BUY,
            quantity=100,
            price="1.00",
            minutes=0,
        ),
        _execution(
            trade,
            side=ExecutionSide.BUY,
            quantity=100,
            price="1.20",
            minutes=1,
        ),
        _execution(
            trade,
            side=ExecutionSide.SELL,
            quantity=50,
            price="1.30",
            minutes=2,
        ),
    ]

    position = PositionProjector.project(
        id=uuid4(),
        trade=trade,
        executions=executions,
    )

    assert position.open_quantity == 150
    assert position.cost_basis == Decimal("165.00")
    assert position.average_entry_price == Decimal("1.10")
    assert position.realized_gross_pnl == Decimal("10.00")
    assert position.closed_at is None


def test_project_full_exit_retains_average_entry_and_sets_closed_state() -> None:
    trade = _trade()
    buy = _execution(
        trade,
        side=ExecutionSide.BUY,
        quantity=100,
        price="1.10",
        minutes=0,
    )
    sell = _execution(
        trade,
        side=ExecutionSide.SELL,
        quantity=100,
        price="1.30",
        minutes=5,
    )

    position = PositionProjector.project(
        id=uuid4(),
        trade=trade,
        executions=[buy, sell],
    )

    assert position.open_quantity == 0
    assert position.cost_basis == Decimal("0")
    assert position.average_entry_price == Decimal("1.10")
    assert position.realized_gross_pnl == Decimal("20.00")
    assert position.closed_at == sell.executed_at
    assert position.is_closed


def test_project_rejects_over_sell() -> None:
    trade = _trade()
    executions = [
        _execution(
            trade,
            side=ExecutionSide.BUY,
            quantity=100,
            price="1.00",
            minutes=0,
        ),
        _execution(
            trade,
            side=ExecutionSide.SELL,
            quantity=101,
            price="1.10",
            minutes=1,
        ),
    ]

    with pytest.raises(ValueError, match="exceeds current open quantity"):
        PositionProjector.project(
            id=uuid4(),
            trade=trade,
            executions=executions,
        )


def test_project_rejects_sell_without_prior_buy() -> None:
    trade = _trade()
    sell = _execution(
        trade,
        side=ExecutionSide.SELL,
        quantity=1,
        price="1.10",
        minutes=0,
    )

    with pytest.raises(ValueError, match="requires prior open quantity"):
        PositionProjector.project(
            id=uuid4(),
            trade=trade,
            executions=[sell],
        )


def test_project_rejects_reopening_closed_trade() -> None:
    trade = _trade()
    executions = [
        _execution(
            trade,
            side=ExecutionSide.BUY,
            quantity=10,
            price="1.00",
            minutes=0,
        ),
        _execution(
            trade,
            side=ExecutionSide.SELL,
            quantity=10,
            price="1.10",
            minutes=1,
        ),
        _execution(
            trade,
            side=ExecutionSide.BUY,
            quantity=5,
            price="0.90",
            minutes=2,
        ),
    ]

    with pytest.raises(ValueError, match="must not be reopened"):
        PositionProjector.project(
            id=uuid4(),
            trade=trade,
            executions=executions,
        )


def test_project_rejects_execution_from_other_trade() -> None:
    trade = _trade()
    other = _trade()
    execution = _execution(
        other,
        side=ExecutionSide.BUY,
        quantity=10,
        price="1.00",
        minutes=0,
    )

    with pytest.raises(ValueError, match="does not belong to trade"):
        PositionProjector.project(
            id=uuid4(),
            trade=trade,
            executions=[execution],
        )
