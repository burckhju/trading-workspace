from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.features.trade_position.domain.enums import ExecutionSide, TradeOrigin
from app.features.trade_position.domain.models import ExecutionRecord, Position, Trade
from app.features.trade_position.persistence.models import (
    ExecutionRecordModel,
    PositionModel,
    TradeModel,
)
from app.features.trade_position.persistence.repositories import (
    SqlAlchemyExecutionRecordRepository,
    SqlAlchemyPositionRepository,
    SqlAlchemyTradeRepository,
)

NOW = datetime(2026, 8, 17, 8, 0, tzinfo=UTC)


def _session():
    session = Mock()
    session.add = Mock()
    session.flush = AsyncMock()
    session.scalar = AsyncMock()
    session.scalars = AsyncMock()
    return session


def _trade() -> Trade:
    return Trade(
        id=uuid4(),
        workspace_id=uuid4(),
        product_id=uuid4(),
        origin=TradeOrigin.EXTERNAL,
        created_at=NOW,
        created_by=uuid4(),
    )


def _execution(trade: Trade) -> ExecutionRecord:
    return ExecutionRecord(
        id=uuid4(),
        trade_id=trade.id,
        product_id=trade.product_id,
        quantity=10,
        price_per_unit=Decimal("2.50"),
        executed_at=NOW,
        recorded_at=NOW,
        recorded_by=uuid4(),
    )


def _position(trade: Trade, execution: ExecutionRecord) -> Position:
    return Position.from_execution(
        id=uuid4(),
        trade=trade,
        execution=execution,
    )


@pytest.mark.asyncio
async def test_trade_repository_add_maps_domain_to_model() -> None:
    session = _session()
    repo = SqlAlchemyTradeRepository(session)
    trade = _trade()
    session.scalar.side_effect = [trade.product_id, None]

    await repo.add(trade)

    model = session.add.call_args.args[0]
    assert isinstance(model, TradeModel)
    assert model.id == trade.id
    assert model.workspace_id == trade.workspace_id
    assert model.product_id == trade.product_id
    assert model.origin == TradeOrigin.EXTERNAL.value
    session.flush.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_trade_repository_get_returns_domain_trade() -> None:
    session = _session()
    repo = SqlAlchemyTradeRepository(session)
    trade = _trade()

    session.scalar.return_value = TradeModel(
        id=trade.id,
        workspace_id=trade.workspace_id,
        product_id=trade.product_id,
        origin=trade.origin.value,
        created_at=trade.created_at,
        created_by=trade.created_by,
        trade_plan_id=None,
        trade_plan_version_id=None,
        product_selection_id=None,
        product_evaluation_id=None,
    )

    result = await repo.get(trade.workspace_id, trade.id)

    assert result == trade


@pytest.mark.asyncio
async def test_trade_repository_get_returns_none_when_missing() -> None:
    session = _session()
    repo = SqlAlchemyTradeRepository(session)
    trade = _trade()
    session.scalar.return_value = None

    assert await repo.get(trade.workspace_id, trade.id) is None


@pytest.mark.asyncio
async def test_execution_repository_add_maps_domain_to_model() -> None:
    session = _session()
    repo = SqlAlchemyExecutionRecordRepository(session)
    trade = _trade()
    execution = _execution(trade)

    await repo.add(execution)

    model = session.add.call_args.args[0]
    assert isinstance(model, ExecutionRecordModel)
    assert model.id == execution.id
    assert model.side == ExecutionSide.BUY.value
    assert model.quantity == execution.quantity
    assert model.price_per_unit == execution.price_per_unit


@pytest.mark.asyncio
async def test_execution_repository_lists_effective_records() -> None:
    session = _session()
    repo = SqlAlchemyExecutionRecordRepository(session)
    trade = _trade()
    execution = _execution(trade)
    model = ExecutionRecordModel(
        id=execution.id,
        trade_id=execution.trade_id,
        product_id=execution.product_id,
        side=execution.side.value,
        supersedes_execution_id=None,
        quantity=execution.quantity,
        price_per_unit=execution.price_per_unit,
        executed_at=execution.executed_at,
        recorded_at=execution.recorded_at,
        recorded_by=execution.recorded_by,
    )
    result = Mock()
    result.all.return_value = [model]
    session.scalars.return_value = result

    records = await repo.list_effective_for_trade(trade.id)

    assert records == [execution]


@pytest.mark.asyncio
async def test_execution_repository_lists_all_records() -> None:
    session = _session()
    repo = SqlAlchemyExecutionRecordRepository(session)
    trade = _trade()
    execution = _execution(trade)
    model = ExecutionRecordModel(
        id=execution.id,
        trade_id=execution.trade_id,
        product_id=execution.product_id,
        side=execution.side.value,
        supersedes_execution_id=None,
        quantity=execution.quantity,
        price_per_unit=execution.price_per_unit,
        executed_at=execution.executed_at,
        recorded_at=execution.recorded_at,
        recorded_by=execution.recorded_by,
    )
    result = Mock()
    result.all.return_value = [model]
    session.scalars.return_value = result

    records = await repo.list_for_trade(trade.id)

    assert records == [execution]


@pytest.mark.asyncio
async def test_position_repository_add_maps_domain_to_model() -> None:
    session = _session()
    repo = SqlAlchemyPositionRepository(session)
    trade = _trade()
    execution = _execution(trade)
    position = _position(trade, execution)

    await repo.add(position)

    model = session.add.call_args.args[0]
    assert isinstance(model, PositionModel)
    assert model.id == position.id
    assert model.open_quantity == position.open_quantity
    assert model.cost_basis == position.cost_basis
    assert model.realized_gross_pnl == Decimal("0")


@pytest.mark.asyncio
async def test_position_repository_get_returns_domain_position() -> None:
    session = _session()
    repo = SqlAlchemyPositionRepository(session)
    trade = _trade()
    execution = _execution(trade)
    position = _position(trade, execution)

    session.scalar.return_value = PositionModel(
        id=position.id,
        trade_id=position.trade_id,
        product_id=position.product_id,
        open_quantity=position.open_quantity,
        cost_basis=position.cost_basis,
        average_entry_price=position.average_entry_price,
        opened_at=position.opened_at,
        last_execution_at=position.last_execution_at,
        realized_gross_pnl=position.realized_gross_pnl,
        closed_at=position.closed_at,
    )

    result = await repo.get_for_trade(trade.workspace_id, trade.id)

    assert result == position


@pytest.mark.asyncio
async def test_position_repository_get_returns_none_when_missing() -> None:
    session = _session()
    repo = SqlAlchemyPositionRepository(session)
    trade = _trade()
    session.scalar.return_value = None

    assert await repo.get_for_trade(trade.workspace_id, trade.id) is None


@pytest.mark.asyncio
async def test_position_repository_replace_updates_model() -> None:
    session = _session()
    repo = SqlAlchemyPositionRepository(session)
    trade = _trade()
    execution = _execution(trade)
    position = _position(trade, execution)
    model = PositionModel(
        id=position.id,
        trade_id=position.trade_id,
        product_id=position.product_id,
        open_quantity=1,
        cost_basis=Decimal("1"),
        average_entry_price=Decimal("1"),
        opened_at=position.opened_at,
        last_execution_at=position.last_execution_at,
        realized_gross_pnl=Decimal("0"),
        closed_at=None,
    )
    session.scalar.return_value = model

    await repo.replace(position)

    assert model.open_quantity == position.open_quantity
    assert model.cost_basis == position.cost_basis
    assert model.average_entry_price == position.average_entry_price


@pytest.mark.asyncio
async def test_position_repository_replace_rejects_missing_position() -> None:
    session = _session()
    repo = SqlAlchemyPositionRepository(session)
    trade = _trade()
    execution = _execution(trade)
    position = _position(trade, execution)
    session.scalar.return_value = None

    with pytest.raises(LookupError, match="position not found"):
        await repo.replace(position)
