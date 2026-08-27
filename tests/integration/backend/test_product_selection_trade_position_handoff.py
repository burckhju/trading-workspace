from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from app.features.product_selection.domain.enums import (
    CriterionOutcome,
    DataAvailability,
    EligibilityStatus,
)
from app.features.product_selection.domain.models import (
    CriterionResult,
    ModelReference,
    ProductEvaluation,
    ProductSelection,
    ProductSelectionRun,
)
from app.features.trade_plan.domain.enums import TradePlanStatus
from app.features.trade_position.domain.enums import TradeOrigin
from app.features.trade_position.service.application import TradePositionService
from app.features.trade_position.service.resolvers import ResolvedWorkspaceSelection


class TradePositionUow:
    def __init__(self) -> None:
        self.trades = SimpleNamespace(add=AsyncMock())
        self.executions = SimpleNamespace(add=AsyncMock())
        self.positions = SimpleNamespace(add=AsyncMock())
        self.management_events = SimpleNamespace()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.flush = AsyncMock()

    async def __aenter__(self) -> TradePositionUow:
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        if exc_type is not None:
            await self.rollback()


class ExactSelectionResolver:
    def __init__(
        self,
        *,
        run: ProductSelectionRun,
        evaluation: ProductEvaluation,
        selection: ProductSelection,
    ) -> None:
        self._run = run
        self._evaluation = evaluation
        self._selection = selection
        self.resolve = AsyncMock(side_effect=self._resolve)

    async def _resolve(
        self,
        workspace_id: UUID,
        product_selection_id: UUID,
    ) -> ResolvedWorkspaceSelection | None:
        if workspace_id != self._run.workspace_id:
            return None
        if product_selection_id != self._selection.id:
            return None
        return ResolvedWorkspaceSelection(
            workspace_id=self._run.workspace_id,
            product_id=self._evaluation.warrant_id,
            trade_plan_id=self._run.trade_plan_id,
            trade_plan_version_id=self._run.trade_plan_version_id,
            product_selection_id=self._selection.id,
            product_evaluation_id=self._evaluation.id,
        )


@pytest.mark.asyncio
async def test_product_selection_handoff_creates_trade_execution_and_position_with_pinned_provenance() -> None:
    selected_at = datetime(2026, 8, 27, 10, 30, tzinfo=UTC)
    executed_at = selected_at + timedelta(minutes=5)
    workspace_id = uuid4()
    trade_plan_id = uuid4()
    trade_plan_version_id = uuid4()
    underlying_id = uuid4()
    warrant_id = uuid4()
    actor = uuid4()
    model = ModelReference("FT008", "1.0.0")

    run = ProductSelectionRun(
        id=uuid4(),
        workspace_id=workspace_id,
        trade_plan_id=trade_plan_id,
        trade_plan_version_id=trade_plan_version_id,
        trade_plan_version_status=TradePlanStatus.APPROVED,
        underlying_id=underlying_id,
        evaluated_at=selected_at - timedelta(minutes=2),
        universe_model=model,
        eligibility_model=model,
        evaluation_model=model,
        created_at=selected_at - timedelta(minutes=2),
        created_by=actor,
    )
    evaluation = ProductEvaluation(
        id=uuid4(),
        run_id=run.id,
        warrant_id=warrant_id,
        warrant_terms_version_id=uuid4(),
        warrant_listing_id=uuid4(),
        evaluated_at=run.evaluated_at,
        eligibility_model=model,
        evaluation_model=model,
        inputs=(),
        criteria=(
            CriterionResult(
                criterion_id="direction",
                outcome=CriterionOutcome.FULFILLED,
                explanation="Warrant direction matches approved plan",
                data_availability=DataAvailability.AVAILABLE,
            ),
        ),
        metrics=(),
        eligibility_status=EligibilityStatus.ELIGIBLE,
        reasons=(),
    )
    selection = ProductSelection.from_user_decision(
        id=uuid4(),
        run=run,
        evaluation=evaluation,
        selected_at=selected_at,
        selected_by=actor,
        rationale="Explicit workspace purchase selection",
    )

    resolver = ExactSelectionResolver(run=run, evaluation=evaluation, selection=selection)
    uow = TradePositionUow()
    service = TradePositionService(uow=uow, workspace_selections=resolver)

    trade, execution, position = await service.record_initial_purchase(
        workspace_id=workspace_id,
        product_selection_id=selection.id,
        quantity=250,
        price_per_unit=Decimal("2.40"),
        executed_at=executed_at,
        actor=actor,
    )

    resolver.resolve.assert_awaited_once_with(workspace_id, selection.id)

    assert trade.origin is TradeOrigin.WORKSPACE_SELECTION
    assert trade.workspace_id == workspace_id
    assert trade.product_id == warrant_id
    assert trade.trade_plan_id == trade_plan_id
    assert trade.trade_plan_version_id == trade_plan_version_id
    assert trade.product_selection_id == selection.id
    assert trade.product_evaluation_id == evaluation.id

    assert execution.trade_id == trade.id
    assert execution.product_id == warrant_id
    assert execution.quantity == 250
    assert execution.price_per_unit == Decimal("2.40")
    assert execution.gross_amount == Decimal("600.00")
    assert execution.executed_at == executed_at
    assert execution.recorded_by == actor

    assert position.trade_id == trade.id
    assert position.product_id == warrant_id
    assert position.open_quantity == 250
    assert position.cost_basis == Decimal("600.00")
    assert position.average_entry_price == Decimal("2.40")

    uow.trades.add.assert_awaited_once_with(trade)
    uow.executions.add.assert_awaited_once_with(execution)
    uow.positions.add.assert_awaited_once_with(position)
    uow.commit.assert_awaited_once()

    # Later FT-008 activity must not retarget the already recorded real-world trade.
    later_selection_id = uuid4()
    later_evaluation_id = uuid4()
    assert trade.product_selection_id != later_selection_id
    assert trade.product_evaluation_id != later_evaluation_id
    assert trade.trade_plan_version_id == run.trade_plan_version_id
