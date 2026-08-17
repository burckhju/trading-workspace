from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.features.trade_position.domain.enums import (
    ExecutionSide,
    TradeManagementEventType,
    TradeOrigin,
)
from app.features.trade_position.domain.models import (
    ExecutionRecord,
    Position,
    Trade,
    TradeManagementEvent,
)
from app.features.trade_position.domain.timeline import (
    TradeTimelineEntryKind,
    ft011_eligibility,
)
from app.features.trade_position.service.application import TradePositionService

NOW = datetime(2026, 8, 17, 8, 0, tzinfo=UTC)


class UowWrapper:
    def __init__(self, uow: SimpleNamespace) -> None:
        self.uow = uow

    async def __aenter__(self):
        return self.uow

    async def __aexit__(self, exc_type, exc, tb):
        if exc_type:
            await self.uow.rollback()


def _trade() -> Trade:
    return Trade(
        id=uuid4(),
        workspace_id=uuid4(),
        product_id=uuid4(),
        origin=TradeOrigin.EXTERNAL,
        created_at=NOW,
        created_by=uuid4(),
    )


def _execution(
    trade: Trade,
    *,
    side: ExecutionSide = ExecutionSide.BUY,
    quantity: int = 100,
    price: str = "1.00",
    minutes: int = 0,
    supersedes_execution_id=None,
) -> ExecutionRecord:
    at = NOW + timedelta(minutes=minutes)
    return ExecutionRecord(
        id=uuid4(),
        trade_id=trade.id,
        product_id=trade.product_id,
        side=side,
        quantity=quantity,
        price_per_unit=Decimal(price),
        executed_at=at,
        recorded_at=at,
        recorded_by=uuid4(),
        supersedes_execution_id=supersedes_execution_id,
    )


def _uow(
    trade: Trade, position: Position, history: list[ExecutionRecord]
) -> SimpleNamespace:
    return SimpleNamespace(
        trades=SimpleNamespace(get=AsyncMock(return_value=trade)),
        positions=SimpleNamespace(
            get_for_trade=AsyncMock(return_value=position),
            replace=AsyncMock(),
        ),
        executions=SimpleNamespace(
            add=AsyncMock(),
            list_for_trade=AsyncMock(return_value=history),
        ),
        management_events=SimpleNamespace(
            add=AsyncMock(),
            list_for_trade=AsyncMock(return_value=[]),
        ),
        commit=AsyncMock(),
        rollback=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_execution_correction_replaces_fact_and_reprojects_position() -> None:
    trade = _trade()
    original = _execution(trade, quantity=100, price="1.00")
    position = Position.from_execution(id=uuid4(), trade=trade, execution=original)
    uow = _uow(trade, position, [original])
    service = TradePositionService(
        uow=UowWrapper(uow),
        workspace_selections=SimpleNamespace(),
    )

    replacement, updated = await service.correct_execution(
        workspace_id=trade.workspace_id,
        trade_id=trade.id,
        execution_id=original.id,
        side=ExecutionSide.BUY,
        quantity=120,
        price_per_unit=Decimal("1.10"),
        executed_at=original.executed_at,
        actor=uuid4(),
    )

    assert replacement.supersedes_execution_id == original.id
    assert updated.open_quantity == 120
    assert updated.cost_basis == Decimal("132.00")
    assert updated.average_entry_price == Decimal("1.10")
    uow.executions.add.assert_awaited_once_with(replacement)
    uow.positions.replace.assert_awaited_once_with(updated)
    uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_execution_correction_rebuilds_realized_pnl_from_effective_history() -> (
    None
):
    trade = _trade()
    buy = _execution(trade, quantity=100, price="1.00")
    sale = _execution(
        trade,
        side=ExecutionSide.SELL,
        quantity=40,
        price="1.50",
        minutes=1,
    )
    position = Position(
        id=uuid4(),
        trade_id=trade.id,
        product_id=trade.product_id,
        open_quantity=60,
        cost_basis=Decimal("60.00"),
        average_entry_price=Decimal("1.00"),
        realized_gross_pnl=Decimal("20.00"),
        opened_at=buy.executed_at,
        last_execution_at=sale.executed_at,
    )
    uow = _uow(trade, position, [buy, sale])
    service = TradePositionService(
        uow=UowWrapper(uow),
        workspace_selections=SimpleNamespace(),
    )

    replacement, updated = await service.correct_execution(
        workspace_id=trade.workspace_id,
        trade_id=trade.id,
        execution_id=sale.id,
        side=ExecutionSide.SELL,
        quantity=40,
        price_per_unit=Decimal("1.25"),
        executed_at=sale.executed_at,
        actor=uuid4(),
    )

    assert replacement.supersedes_execution_id == sale.id
    assert updated.open_quantity == 60
    assert updated.realized_gross_pnl == Decimal("10.00")


@pytest.mark.asyncio
async def test_execution_correction_rejects_already_superseded_fact() -> None:
    trade = _trade()
    original = _execution(trade)
    replacement = _execution(
        trade,
        quantity=110,
        supersedes_execution_id=original.id,
    )
    position = Position.from_execution(id=uuid4(), trade=trade, execution=replacement)
    uow = _uow(trade, position, [original, replacement])
    service = TradePositionService(
        uow=UowWrapper(uow),
        workspace_selections=SimpleNamespace(),
    )

    with pytest.raises(ValueError, match="already superseded"):
        await service.correct_execution(
            workspace_id=trade.workspace_id,
            trade_id=trade.id,
            execution_id=original.id,
            side=ExecutionSide.BUY,
            quantity=120,
            price_per_unit=Decimal("1.00"),
            executed_at=NOW,
            actor=uuid4(),
        )

    uow.executions.add.assert_not_awaited()
    uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_management_event_correction_preserves_original_event_type() -> None:
    trade = _trade()
    buy = _execution(trade)
    position = Position.from_execution(id=uuid4(), trade=trade, execution=buy)
    original = TradeManagementEvent(
        id=uuid4(),
        trade_id=trade.id,
        event_type=TradeManagementEventType.STOP_CHANGED,
        effective_at=NOW,
        recorded_at=NOW,
        recorded_by=uuid4(),
        numeric_value=Decimal("0.90"),
    )
    uow = _uow(trade, position, [buy])
    uow.management_events.list_for_trade.return_value = [original]
    service = TradePositionService(
        uow=UowWrapper(uow),
        workspace_selections=SimpleNamespace(),
    )

    replacement = await service.correct_management_event(
        workspace_id=trade.workspace_id,
        trade_id=trade.id,
        event_id=original.id,
        effective_at=NOW,
        actor=uuid4(),
        numeric_value=Decimal("0.95"),
    )

    assert replacement.event_type is TradeManagementEventType.STOP_CHANGED
    assert replacement.numeric_value == Decimal("0.95")
    assert replacement.supersedes_event_id == original.id
    uow.management_events.add.assert_awaited_once_with(replacement)


@pytest.mark.asyncio
async def test_timeline_composes_execution_and_management_facts_without_sale_duplication() -> (
    None
):
    trade = _trade()
    buy = _execution(trade)
    sale = _execution(
        trade,
        side=ExecutionSide.SELL,
        quantity=20,
        price="1.20",
        minutes=1,
    )
    note = TradeManagementEvent(
        id=uuid4(),
        trade_id=trade.id,
        event_type=TradeManagementEventType.MANAGEMENT_NOTE,
        effective_at=NOW + timedelta(minutes=2),
        recorded_at=NOW + timedelta(minutes=2),
        recorded_by=uuid4(),
        text_value="reviewed exit",
    )
    position = Position(
        id=uuid4(),
        trade_id=trade.id,
        product_id=trade.product_id,
        open_quantity=80,
        cost_basis=Decimal("80.00"),
        average_entry_price=Decimal("1.00"),
        realized_gross_pnl=Decimal("4.00"),
        opened_at=NOW,
        last_execution_at=sale.executed_at,
    )
    uow = _uow(trade, position, [buy, sale])
    uow.management_events.list_for_trade.return_value = [note]
    service = TradePositionService(
        uow=UowWrapper(uow),
        workspace_selections=SimpleNamespace(),
    )

    timeline = await service.get_trade_timeline(
        workspace_id=trade.workspace_id,
        trade_id=trade.id,
    )

    assert [item.kind for item in timeline] == [
        TradeTimelineEntryKind.EXECUTION,
        TradeTimelineEntryKind.EXECUTION,
        TradeTimelineEntryKind.MANAGEMENT_EVENT,
    ]
    assert sum(item.execution_side is ExecutionSide.SELL for item in timeline) == 1


def test_ft011_handoff_requires_full_exit() -> None:
    trade = _trade()
    buy = _execution(trade)
    open_position = Position.from_execution(id=uuid4(), trade=trade, execution=buy)
    closed_position = Position(
        id=open_position.id,
        trade_id=trade.id,
        product_id=trade.product_id,
        open_quantity=0,
        cost_basis=Decimal("0"),
        average_entry_price=Decimal("1.00"),
        realized_gross_pnl=Decimal("15.00"),
        opened_at=NOW,
        last_execution_at=NOW + timedelta(minutes=1),
        closed_at=NOW + timedelta(minutes=1),
    )

    assert ft011_eligibility(open_position).eligible is False
    assert ft011_eligibility(closed_position).eligible is True
