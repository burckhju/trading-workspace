from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.features.trade_position.domain.enums import TradeOrigin
from app.features.trade_position.domain.models import ExecutionRecord, Position, Trade
from app.features.trade_position.service.application import TradePositionService


NOW = datetime(2026, 8, 17, 8, 0, tzinfo=UTC)


class FakeUow:
    def __init__(self) -> None:
        self.trades = SimpleNamespace(
            add=AsyncMock(),
            get=AsyncMock(),
        )
        self.executions = SimpleNamespace(
            add=AsyncMock(),
        )
        self.positions = SimpleNamespace(
            add=AsyncMock(),
            get_for_trade=AsyncMock(),
            replace=AsyncMock(),
        )
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.flush = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type:
            await self.rollback()


class FakeWorkspaceSelections:
    def __init__(self) -> None:
        self.workspace_id = uuid4()
        self.product_id = uuid4()
        self.trade_plan_id = uuid4()
        self.trade_plan_version_id = uuid4()
        self.product_selection_id = uuid4()
        self.product_evaluation_id = uuid4()

        self.resolve = AsyncMock(
            return_value=SimpleNamespace(
                workspace_id=self.workspace_id,
                product_id=self.product_id,
                trade_plan_id=self.trade_plan_id,
                trade_plan_version_id=self.trade_plan_version_id,
                product_selection_id=self.product_selection_id,
                product_evaluation_id=self.product_evaluation_id,
            )
        )


@pytest.mark.asyncio
async def test_record_initial_purchase_from_workspace_selection() -> None:
    uow = FakeUow()
    selections = FakeWorkspaceSelections()
    service = TradePositionService(
        uow=uow,
        workspace_selections=selections,
    )
    actor = uuid4()

    trade, execution, position = await service.record_initial_purchase(
        workspace_id=selections.workspace_id,
        product_selection_id=selections.product_selection_id,
        quantity=400,
        price_per_unit=Decimal("2.48"),
        executed_at=NOW,
        actor=actor,
    )

    selections.resolve.assert_awaited_once_with(
        selections.workspace_id,
        selections.product_selection_id,
    )

    assert trade.origin is TradeOrigin.WORKSPACE_SELECTION
    assert trade.workspace_id == selections.workspace_id
    assert trade.product_id == selections.product_id
    assert trade.trade_plan_id == selections.trade_plan_id
    assert trade.trade_plan_version_id == selections.trade_plan_version_id
    assert trade.product_selection_id == selections.product_selection_id
    assert trade.product_evaluation_id == selections.product_evaluation_id

    assert execution.trade_id == trade.id
    assert execution.quantity == 400
    assert execution.price_per_unit == Decimal("2.48")
    assert execution.gross_amount == Decimal("992.00")
    assert execution.recorded_by == actor

    assert position.trade_id == trade.id
    assert position.open_quantity == 400
    assert position.cost_basis == Decimal("992.00")

    uow.trades.add.assert_awaited_once_with(trade)
    uow.executions.add.assert_awaited_once_with(execution)
    uow.positions.add.assert_awaited_once_with(position)
    uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_record_additional_purchase_updates_existing_position() -> None:
    uow = FakeUow()
    selections = FakeWorkspaceSelections()
    service = TradePositionService(
        uow=uow,
        workspace_selections=selections,
    )
    actor = uuid4()

    trade = Trade(
        id=uuid4(),
        workspace_id=selections.workspace_id,
        product_id=selections.product_id,
        origin=TradeOrigin.WORKSPACE_SELECTION,
        created_at=NOW - timedelta(hours=1),
        created_by=actor,
        trade_plan_id=selections.trade_plan_id,
        trade_plan_version_id=selections.trade_plan_version_id,
        product_selection_id=selections.product_selection_id,
        product_evaluation_id=selections.product_evaluation_id,
    )
    first = ExecutionRecord(
        id=uuid4(),
        trade_id=trade.id,
        product_id=trade.product_id,
        quantity=400,
        price_per_unit=Decimal("2.48"),
        executed_at=NOW - timedelta(minutes=30),
        recorded_at=NOW - timedelta(minutes=29),
        recorded_by=actor,
    )
    position = Position.from_execution(
        id=uuid4(),
        trade=trade,
        execution=first,
    )

    uow.trades.get.return_value = trade
    uow.positions.get_for_trade.return_value = position

    execution, updated = await service.record_additional_purchase(
        workspace_id=trade.workspace_id,
        trade_id=trade.id,
        quantity=200,
        price_per_unit=Decimal("2.70"),
        executed_at=NOW,
        actor=actor,
    )

    uow.trades.get.assert_awaited_once_with(
        trade.workspace_id,
        trade.id,
    )
    uow.positions.get_for_trade.assert_awaited_once_with(
        trade.workspace_id,
        trade.id,
    )

    assert execution.trade_id == trade.id
    assert execution.quantity == 200
    assert execution.gross_amount == Decimal("540.00")

    assert updated.id == position.id
    assert updated.open_quantity == 600
    assert updated.cost_basis == Decimal("1532.00")
    assert updated.average_entry_price == Decimal(
        "2.553333333333333333333333333"
    )

    uow.executions.add.assert_awaited_once_with(execution)
    uow.positions.replace.assert_awaited_once_with(updated)
    uow.trades.add.assert_not_awaited()
    uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_additional_purchase_rejects_unknown_trade() -> None:
    uow = FakeUow()
    selections = FakeWorkspaceSelections()
    service = TradePositionService(
        uow=uow,
        workspace_selections=selections,
    )

    uow.trades.get.return_value = None

    with pytest.raises(ValueError, match="trade not found"):
        await service.record_additional_purchase(
            workspace_id=selections.workspace_id,
            trade_id=uuid4(),
            quantity=1,
            price_per_unit=Decimal("1.00"),
            executed_at=NOW,
            actor=uuid4(),
        )

    uow.executions.add.assert_not_awaited()
    uow.positions.replace.assert_not_awaited()
    uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_additional_purchase_rejects_missing_position() -> None:
    uow = FakeUow()
    selections = FakeWorkspaceSelections()
    service = TradePositionService(
        uow=uow,
        workspace_selections=selections,
    )

    trade = Trade(
        id=uuid4(),
        workspace_id=selections.workspace_id,
        product_id=selections.product_id,
        origin=TradeOrigin.EXTERNAL,
        created_at=NOW,
        created_by=uuid4(),
    )

    uow.trades.get.return_value = trade
    uow.positions.get_for_trade.return_value = None

    with pytest.raises(ValueError, match="position not found"):
        await service.record_additional_purchase(
            workspace_id=trade.workspace_id,
            trade_id=trade.id,
            quantity=1,
            price_per_unit=Decimal("1.00"),
            executed_at=NOW + timedelta(minutes=1),
            actor=uuid4(),
        )

    uow.executions.add.assert_not_awaited()
    uow.positions.replace.assert_not_awaited()
    uow.commit.assert_not_awaited()


class FakeProducts:
    def __init__(self) -> None:
        self.resolve = AsyncMock()


@pytest.mark.asyncio
async def test_record_external_purchase_creates_trade_without_selection_provenance() -> None:
    uow = FakeUow()
    selections = FakeWorkspaceSelections()
    products = FakeProducts()

    workspace_id = uuid4()
    product_id = uuid4()
    actor = uuid4()

    products.resolve.return_value = SimpleNamespace(
        workspace_id=workspace_id,
        product_id=product_id,
    )

    service = TradePositionService(
        uow=uow,
        workspace_selections=selections,
        products=products,
    )

    trade, execution, position = await service.record_external_purchase(
        workspace_id=workspace_id,
        product_id=product_id,
        quantity=100,
        price_per_unit=Decimal("1.25"),
        executed_at=NOW,
        actor=actor,
    )

    products.resolve.assert_awaited_once_with(
        workspace_id,
        product_id,
    )

    assert trade.origin is TradeOrigin.EXTERNAL
    assert trade.workspace_id == workspace_id
    assert trade.product_id == product_id
    assert trade.trade_plan_id is None
    assert trade.trade_plan_version_id is None
    assert trade.product_selection_id is None
    assert trade.product_evaluation_id is None

    assert execution.trade_id == trade.id
    assert execution.quantity == 100
    assert execution.price_per_unit == Decimal("1.25")
    assert execution.gross_amount == Decimal("125.00")

    assert position.trade_id == trade.id
    assert position.open_quantity == 100
    assert position.cost_basis == Decimal("125.00")

    uow.trades.add.assert_awaited_once_with(trade)
    uow.executions.add.assert_awaited_once_with(execution)
    uow.positions.add.assert_awaited_once_with(position)
    uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_external_purchase_rejects_unknown_product_before_persistence() -> None:
    uow = FakeUow()
    selections = FakeWorkspaceSelections()
    products = FakeProducts()

    workspace_id = uuid4()
    product_id = uuid4()

    products.resolve.return_value = None

    service = TradePositionService(
        uow=uow,
        workspace_selections=selections,
        products=products,
    )

    with pytest.raises(ValueError, match="product not found"):
        await service.record_external_purchase(
            workspace_id=workspace_id,
            product_id=product_id,
            quantity=1,
            price_per_unit=Decimal("1.00"),
            executed_at=NOW,
            actor=uuid4(),
        )

    uow.trades.add.assert_not_awaited()
    uow.executions.add.assert_not_awaited()
    uow.positions.add.assert_not_awaited()
    uow.commit.assert_not_awaited()
