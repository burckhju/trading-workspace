from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.features.product_selection.domain.enums import CriterionOutcome, EligibilityStatus
from app.features.product_selection.domain.models import (
    CriterionResult,
    ModelReference,
    ProductEvaluation,
    ProductSelectionRun,
)
from app.features.product_selection.service.commands import ProductSelectionCommandService
from app.features.trade_plan.domain.enums import TradePlanStatus

NOW = datetime(2026, 8, 16, 10, 0, tzinfo=UTC)
MODEL = ModelReference("model", "1.0.0")


class FakeUow:
    def __init__(self):
        self.runs = Mock(get=AsyncMock())
        self.evaluations = Mock(get=AsyncMock())
        self.selections = Mock(get_for_run=AsyncMock(), add=AsyncMock())
        self.flush = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        if exc_type is not None:
            await self.rollback()


def run():
    return ProductSelectionRun(
        id=uuid4(),
        workspace_id=uuid4(),
        trade_plan_id=uuid4(),
        trade_plan_version_id=uuid4(),
        trade_plan_version_status=TradePlanStatus.APPROVED,
        underlying_id=uuid4(),
        evaluated_at=NOW,
        universe_model=MODEL,
        eligibility_model=MODEL,
        evaluation_model=MODEL,
        created_at=NOW,
        created_by=uuid4(),
    )


def evaluation(run_id, status=EligibilityStatus.ELIGIBLE):
    outcome = (
        CriterionOutcome.FULFILLED
        if status is EligibilityStatus.ELIGIBLE
        else CriterionOutcome.NOT_FULFILLED
    )
    return ProductEvaluation(
        id=uuid4(),
        run_id=run_id,
        warrant_id=uuid4(),
        warrant_terms_version_id=uuid4(),
        warrant_listing_id=uuid4(),
        evaluated_at=NOW,
        eligibility_model=MODEL,
        evaluation_model=MODEL,
        inputs=(),
        criteria=(
            CriterionResult(
                criterion_id="reference", outcome=outcome, explanation="reference rule"
            ),
        ),
        metrics=(),
        eligibility_status=status,
        reasons=() if status is EligibilityStatus.ELIGIBLE else ("excluded",),
    )


@pytest.mark.asyncio
async def test_select_product_persists_explicit_eligible_user_decision_atomically():
    uow = FakeUow()
    r = run()
    e = evaluation(r.id)
    uow.runs.get.return_value = r
    uow.selections.get_for_run.return_value = None
    uow.evaluations.get.return_value = e
    service = ProductSelectionCommandService(uow)
    actor = uuid4()

    result = await service.select_product(
        workspace_id=r.workspace_id,
        run_id=r.id,
        evaluation_id=e.id,
        actor=actor,
        rationale="chosen explicitly",
        selected_at=NOW,
    )

    assert (
        result.run_id == r.id
        and result.product_evaluation_id == e.id
        and result.selected_by == actor
    )
    uow.selections.add.assert_awaited_once_with(result)
    uow.flush.assert_awaited_once()
    uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_select_product_rejects_second_selection_before_loading_evaluation():
    uow = FakeUow()
    r = run()
    uow.runs.get.return_value = r
    uow.selections.get_for_run.return_value = Mock()
    service = ProductSelectionCommandService(uow)
    with pytest.raises(ValueError, match="already has a user selection"):
        await service.select_product(
            workspace_id=r.workspace_id, run_id=r.id, evaluation_id=uuid4(), actor=uuid4()
        )
    uow.evaluations.get.assert_not_awaited()
    uow.selections.add.assert_not_awaited()
    uow.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_select_product_rejects_non_eligible_evaluation():
    uow = FakeUow()
    r = run()
    e = evaluation(r.id, EligibilityStatus.INELIGIBLE)
    uow.runs.get.return_value = r
    uow.selections.get_for_run.return_value = None
    uow.evaluations.get.return_value = e
    service = ProductSelectionCommandService(uow)
    with pytest.raises(ValueError, match="requires an ELIGIBLE"):
        await service.select_product(
            workspace_id=r.workspace_id, run_id=r.id, evaluation_id=e.id, actor=uuid4()
        )
    uow.selections.add.assert_not_awaited()
    uow.commit.assert_not_awaited()
