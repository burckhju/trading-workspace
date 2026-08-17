from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.features.trade_position.domain.enums import ExecutionSide, TradeOrigin
from app.features.trade_position.domain.models import ExecutionRecord, Position, Trade
from app.features.trade_position.service.application import TradePositionService

NOW = datetime(2026, 8, 17, 10, 0, tzinfo=UTC)


class MemoryUow:
    def __init__(self, trade: Trade, position: Position) -> None:
        self.trade = trade
        self.position = position
        self.execution_rows = []
        self.management_rows = []

        self.trades = SimpleNamespace(get=self._get_trade)
        self.positions = SimpleNamespace(
            get_for_trade=self._get_position,
            replace=self._replace_position,
        )
        self.executions = SimpleNamespace(
            add=self._add_execution,
            list_for_trade=self._list_executions,
            list_effective_for_trade=self._list_effective_executions,
        )
        self.management_events = SimpleNamespace(
            add=self._add_management_event,
            list_for_trade=self._list_management_events,
            list_effective_for_trade=self._list_effective_management_events,
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None

    async def _get_trade(self, workspace_id, trade_id):
        if workspace_id == self.trade.workspace_id and trade_id == self.trade.id:
            return self.trade
        return None

    async def _get_position(self, workspace_id, trade_id):
        if workspace_id == self.trade.workspace_id and trade_id == self.trade.id:
            return self.position
        return None

    async def _replace_position(self, position: Position) -> None:
        self.position = position

    async def _add_execution(self, execution) -> None:
        self.execution_rows.append(execution)

    async def _list_executions(self, trade_id):
        return [item for item in self.execution_rows if item.trade_id == trade_id]

    async def _list_effective_executions(self, trade_id):
        rows = await self._list_executions(trade_id)
        superseded = {
            item.supersedes_execution_id
            for item in rows
            if item.supersedes_execution_id
        }
        return [item for item in rows if item.id not in superseded]

    async def _add_management_event(self, event) -> None:
        self.management_rows.append(event)

    async def _list_management_events(self, trade_id):
        return [item for item in self.management_rows if item.trade_id == trade_id]

    async def _list_effective_management_events(self, trade_id):
        rows = await self._list_management_events(trade_id)
        superseded = {
            item.supersedes_event_id for item in rows if item.supersedes_event_id
        }
        return [item for item in rows if item.id not in superseded]


@pytest.mark.asyncio
async def test_ft010_historical_sale_correction_timeline_and_ft011_handoff_without_provider() -> (
    None
):
    trade = Trade(
        id=uuid4(),
        workspace_id=uuid4(),
        product_id=uuid4(),
        origin=TradeOrigin.EXTERNAL,
        created_at=NOW,
        created_by=uuid4(),
    )
    initial_execution = ExecutionRecord(
        id=uuid4(),
        trade_id=trade.id,
        product_id=trade.product_id,
        side=ExecutionSide.BUY,
        quantity=100,
        price_per_unit=Decimal("2.00"),
        executed_at=NOW,
        recorded_at=NOW,
        recorded_by=uuid4(),
        supersedes_execution_id=None,
    )
    position = Position(
        id=uuid4(),
        trade_id=trade.id,
        product_id=trade.product_id,
        open_quantity=100,
        cost_basis=Decimal("200.00"),
        average_entry_price=Decimal("2.00"),
        opened_at=NOW,
        last_execution_at=NOW,
    )
    uow = MemoryUow(trade, position)
    uow.execution_rows.append(initial_execution)

    # No provider, broker, quote or market-data dependency is injected into FT-010.
    service = TradePositionService(
        uow=uow,
        workspace_selections=SimpleNamespace(resolve=AsyncMock()),
    )
    actor = uuid4()

    partial_sale, partial_position = await service.record_sale(
        workspace_id=trade.workspace_id,
        trade_id=trade.id,
        quantity=40,
        price_per_unit=Decimal("2.50"),
        executed_at=NOW,
        actor=actor,
    )
    assert partial_position.open_quantity == 60
    assert partial_position.realized_gross_pnl == Decimal("20.00")
    assert (
        await service.get_ft011_eligibility(
            workspace_id=trade.workspace_id,
            trade_id=trade.id,
        )
    ).eligible is False

    corrected_sale, corrected_position = await service.correct_execution(
        workspace_id=trade.workspace_id,
        trade_id=trade.id,
        execution_id=partial_sale.id,
        side=ExecutionSide.SELL,
        quantity=40,
        price_per_unit=Decimal("2.25"),
        executed_at=NOW,
        actor=actor,
    )
    assert corrected_sale.supersedes_execution_id == partial_sale.id
    assert corrected_position.open_quantity == 60
    assert corrected_position.realized_gross_pnl == Decimal("10.00")

    await service.change_stop(
        workspace_id=trade.workspace_id,
        trade_id=trade.id,
        stop_price=Decimal("1.90"),
        effective_at=NOW,
        actor=actor,
    )
    timeline = await service.get_trade_timeline(
        workspace_id=trade.workspace_id,
        trade_id=trade.id,
    )
    sell_entries = [
        item for item in timeline if item.execution_side is ExecutionSide.SELL
    ]
    assert len(sell_entries) == 2  # original audit fact + immutable correction
    assert all(item.management_event_type is None for item in sell_entries)

    _final_sale, closed = await service.record_sale(
        workspace_id=trade.workspace_id,
        trade_id=trade.id,
        quantity=60,
        price_per_unit=Decimal("2.40"),
        executed_at=NOW,
        actor=actor,
    )
    assert closed.is_closed
    assert closed.open_quantity == 0
    assert (
        await service.get_ft011_eligibility(
            workspace_id=trade.workspace_id,
            trade_id=trade.id,
        )
    ).eligible is True
