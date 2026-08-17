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

    await repo.add(trade)

    model = session.add.call_args.args[0]
    assert isinstance(model, TradeModel)
    assert model.id == trade.id
    assert model.workspace_id == trade.workspace_id
    assert model.product_id == trade.product_id
    assert model.origin == TradeOrigin.EXTERNAL.value


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
async def test_trade_repository_get_returns_none_for_unknown_trade() -> None:
    session = _session()
    repo = SqlAlchemyTradeRepository(session)
    session.scalar.return_value = None

    assert await repo.get(uuid4(), uuid4()) is None


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
    assert model.trade_id == execution.trade_id
    assert model.side == ExecutionSide.BUY.value
    assert model.quantity == execution.quantity
    assert model.price_per_unit == execution.price_per_unit
    assert model.supersedes_execution_id is None


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
    assert model.trade_id == position.trade_id
    assert model.open_quantity == position.open_quantity


@pytest.mark.asyncio
async def test_position_repository_get_for_trade_returns_domain_position() -> None:
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
    )

    result = await repo.get_for_trade(trade.workspace_id, trade.id)

    assert result == position


@pytest.mark.asyncio
async def test_position_replace_updates_persisted_snapshot() -> None:
    session = _session()
    repo = SqlAlchemyPositionRepository(session)

    trade = _trade()
    execution = _execution(trade)
    position = _position(trade, execution)

    persisted = PositionModel(
        id=position.id,
        trade_id=position.trade_id,
        product_id=position.product_id,
        open_quantity=1,
        cost_basis=Decimal("1.00"),
        average_entry_price=Decimal("1.00"),
        opened_at=position.opened_at,
        last_execution_at=position.opened_at,
    )
    session.scalar.return_value = persisted

    await repo.replace(position)

    assert persisted.open_quantity == position.open_quantity
    assert persisted.cost_basis == position.cost_basis
    assert persisted.average_entry_price == position.average_entry_price
    assert persisted.last_execution_at == position.last_execution_at


@pytest.mark.asyncio
async def test_execution_repository_add_maps_supersession_relation() -> None:
    session = _session()
    repo = SqlAlchemyExecutionRecordRepository(session)
    trade = _trade()
    original = _execution(trade)
    replacement = ExecutionRecord(
        id=uuid4(),
        trade_id=trade.id,
        product_id=trade.product_id,
        quantity=8,
        price_per_unit=Decimal("2.60"),
        executed_at=NOW,
        recorded_at=NOW,
        recorded_by=uuid4(),
        supersedes_execution_id=original.id,
    )

    await repo.add(replacement)

    model = session.add.call_args.args[0]
    assert model.supersedes_execution_id == original.id


@pytest.mark.asyncio
async def test_execution_repository_lists_full_audit_history() -> None:
    session = _session()
    repo = SqlAlchemyExecutionRecordRepository(session)
    trade = _trade()
    original = _execution(trade)
    replacement = ExecutionRecord(
        id=uuid4(),
        trade_id=trade.id,
        product_id=trade.product_id,
        quantity=8,
        price_per_unit=Decimal("2.60"),
        executed_at=NOW,
        recorded_at=NOW,
        recorded_by=uuid4(),
        supersedes_execution_id=original.id,
    )
    models = [
        ExecutionRecordModel(
            id=execution.id,
            trade_id=execution.trade_id,
            product_id=execution.product_id,
            side=execution.side.value,
            quantity=execution.quantity,
            price_per_unit=execution.price_per_unit,
            executed_at=execution.executed_at,
            recorded_at=execution.recorded_at,
            recorded_by=execution.recorded_by,
            supersedes_execution_id=execution.supersedes_execution_id,
        )
        for execution in (original, replacement)
    ]
    result = Mock()
    result.all.return_value = models
    session.scalars.return_value = result

    executions = await repo.list_for_trade(trade.id)

    assert executions == [original, replacement]


@pytest.mark.asyncio
async def test_execution_repository_effective_query_excludes_superseded_ids() -> None:
    session = _session()
    repo = SqlAlchemyExecutionRecordRepository(session)
    trade = _trade()
    effective = _execution(trade)
    model = ExecutionRecordModel(
        id=effective.id,
        trade_id=effective.trade_id,
        product_id=effective.product_id,
        side=effective.side.value,
        quantity=effective.quantity,
        price_per_unit=effective.price_per_unit,
        executed_at=effective.executed_at,
        recorded_at=effective.recorded_at,
        recorded_by=effective.recorded_by,
        supersedes_execution_id=None,
    )
    result = Mock()
    result.all.return_value = [model]
    session.scalars.return_value = result

    executions = await repo.list_effective_for_trade(trade.id)

    assert executions == [effective]
    statement = session.scalars.await_args.args[0]
    sql = str(statement)
    assert "supersedes_execution_id" in sql
    assert "NOT (EXISTS" in sql
