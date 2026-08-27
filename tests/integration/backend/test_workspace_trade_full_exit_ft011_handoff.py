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

NOW = datetime(2026, 8, 27, 11, 0, tzinfo=UTC)


class MemoryUow:
    def __init__(
        self,
        *,
        trade: Trade,
        position: Position,
        executions: list[ExecutionRecord],
    ) -> None:
        self.trade = trade
        self.position = position
        self.execution_rows = list(executions)
        self.trades = SimpleNamespace(get=self._get_trade)
        self.positions = SimpleNamespace(
            get_for_trade=self._get_position,
            replace=self._replace_position,
        )
        self.executions = SimpleNamespace(
            add=self._add_execution,
            list_effective_for_trade=self._list_effective_executions,
        )
        self.management_events = SimpleNamespace()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()

    async def __aenter__(self) -> MemoryUow:
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        if exc_type is not None:
            await self.rollback()

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

    async def _add_execution(self, execution: ExecutionRecord) -> None:
        self.execution_rows.append(execution)

    async def _list_effective_executions(self, trade_id):
        rows = [item for item in self.execution_rows if item.trade_id == trade_id]
        superseded = {
            item.supersedes_execution_id
            for item in rows
            if item.supersedes_execution_id is not None
        }
        return [item for item in rows if item.id not in superseded]


@pytest.mark.asyncio
async def test_workspace_trade_full_exit_preserves_provenance_and_enables_ft011() -> None:
    workspace_id = uuid4()
    product_id = uuid4()
    actor = uuid4()
    trade_plan_id = uuid4()
    trade_plan_version_id = uuid4()
    product_selection_id = uuid4()
    product_evaluation_id = uuid4()

    trade = Trade(
        id=uuid4(),
        workspace_id=workspace_id,
        product_id=product_id,
        origin=TradeOrigin.WORKSPACE_SELECTION,
        created_at=NOW,
        created_by=actor,
        trade_plan_id=trade_plan_id,
        trade_plan_version_id=trade_plan_version_id,
        product_selection_id=product_selection_id,
        product_evaluation_id=product_evaluation_id,
    )
    purchase = ExecutionRecord(
        id=uuid4(),
        trade_id=trade.id,
        product_id=product_id,
        side=ExecutionSide.BUY,
        quantity=250,
        price_per_unit=Decimal("2.40"),
        executed_at=NOW,
        recorded_at=NOW,
        recorded_by=actor,
    )
    position = Position.from_execution(
        id=uuid4(),
        trade=trade,
        execution=purchase,
    )
    uow = MemoryUow(trade=trade, position=position, executions=[purchase])
    service = TradePositionService(
        uow=uow,
        workspace_selections=SimpleNamespace(resolve=AsyncMock()),
    )

    before = await service.get_ft011_eligibility(
        workspace_id=workspace_id,
        trade_id=trade.id,
    )
    assert before.eligible is False
    assert before.reason == "trade position still has open quantity"

    sell, closed = await service.record_sale(
        workspace_id=workspace_id,
        trade_id=trade.id,
        quantity=250,
        price_per_unit=Decimal("2.90"),
        executed_at=NOW,
        actor=actor,
    )

    assert sell.side is ExecutionSide.SELL
    assert sell.trade_id == trade.id
    assert sell.product_id == product_id
    assert sell.quantity == 250
    assert sell.gross_amount == Decimal("725.00")

    assert closed.trade_id == trade.id
    assert closed.open_quantity == 0
    assert closed.cost_basis == Decimal("0.00")
    assert closed.realized_gross_pnl == Decimal("125.00")
    assert closed.is_closed is True
    assert closed.closed_at == NOW

    handoff = await service.get_ft011_eligibility(
        workspace_id=workspace_id,
        trade_id=trade.id,
    )
    assert handoff.trade_id == trade.id
    assert handoff.eligible is True
    assert handoff.reason == "trade position is fully closed"

    # Full economic exit changes derived position state, not historical origin facts.
    assert trade.origin is TradeOrigin.WORKSPACE_SELECTION
    assert trade.trade_plan_id == trade_plan_id
    assert trade.trade_plan_version_id == trade_plan_version_id
    assert trade.product_selection_id == product_selection_id
    assert trade.product_evaluation_id == product_evaluation_id

    assert uow.execution_rows == [purchase, sell]
    uow.commit.assert_awaited_once()
