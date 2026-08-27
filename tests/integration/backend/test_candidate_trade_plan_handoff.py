from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from app.features.analysis.domain.enums import AnalysisQualityStatus, CriterionClassification
from app.features.analysis.domain.top_down import ContextClassification, TradingDirection
from app.features.candidate.domain.enums import CandidateQualification, CandidateStatus
from app.features.candidate.domain.models import CandidateEvaluationInput
from app.features.candidate.domain.qualification import evaluate_candidate
from app.features.trade_plan.domain.enums import EntryType, TradePlanOriginType, TradePlanStatus
from app.features.trade_plan.domain.models import (
    EntryPlan,
    InvalidationPlan,
    RiskAssumptions,
    Target,
)
from app.features.trade_plan.service.application import TradePlanService


class HandoffUow:
    def __init__(self) -> None:
        self.plans = SimpleNamespace(add=AsyncMock())
        self.versions = SimpleNamespace(add=AsyncMock())
        self.events = SimpleNamespace(add=AsyncMock())
        self.approvals = SimpleNamespace()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()

    async def __aenter__(self) -> HandoffUow:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type is not None:
            await self.rollback()


class CandidateOriginGateway:
    def __init__(self, underlying_id: UUID) -> None:
        self.underlying_id = underlying_id
        self.candidate_origin = AsyncMock(return_value=underlying_id)
        self.manual_underlying = AsyncMock(return_value=underlying_id)


def _qualified_candidate_input() -> CandidateEvaluationInput:
    return CandidateEvaluationInput(
        direction=TradingDirection.LONG,
        market_context=ContextClassification.FAVORABLE,
        market_quality=AnalysisQualityStatus.GOOD,
        sector_trend=CriterionClassification.POSITIVE,
        sector_relative_strength=CriterionClassification.POSITIVE,
        sector_quality=AnalysisQualityStatus.GOOD,
        underlying_long_trend=CriterionClassification.POSITIVE,
        underlying_medium_trend=CriterionClassification.POSITIVE,
        underlying_short_trend=CriterionClassification.POSITIVE,
        underlying_relative_strength=CriterionClassification.POSITIVE,
        underlying_quality=AnalysisQualityStatus.GOOD,
        momentum=CriterionClassification.POSITIVE,
        volatility=Decimal("0.18"),
        range_position=Decimal("0.72"),
    )


def _trade_plan_payload() -> dict[str, object]:
    return {
        "thesis": "Qualified top-down candidate with controlled continuation setup",
        "entry": EntryPlan(type=EntryType.PRICE, currency="EUR", price=Decimal("100")),
        "invalidation": InvalidationPlan(stop_price=Decimal("95")),
        "targets": (Target(sequence=1, price=Decimal("112")),),
        "risk_assumptions": RiskAssumptions(thesis_risk="Top-down setup invalidates"),
    }


@pytest.mark.asyncio
async def test_qualified_ready_candidate_handoff_keeps_exact_evaluation_provenance() -> None:
    workspace_id = uuid4()
    underlying_id = uuid4()
    candidate_id = uuid4()
    first_evaluation_id = uuid4()
    later_evaluation_id = uuid4()
    actor = uuid4()

    qualification = evaluate_candidate(_qualified_candidate_input())
    candidate_status = CandidateStatus.READY_FOR_PLANNING

    assert qualification.qualification is CandidateQualification.QUALIFIED
    assert candidate_status is CandidateStatus.READY_FOR_PLANNING

    uow = HandoffUow()
    origins = CandidateOriginGateway(underlying_id)
    service = TradePlanService(uow=uow, origins=origins)

    plan, version = await service.create_from_candidate(
        workspace_id=workspace_id,
        candidate_id=candidate_id,
        candidate_evaluation_id=first_evaluation_id,
        actor=actor,
        correlation_id="post-d01-golden-path-extension-02",
        **_trade_plan_payload(),
    )

    assert plan.workspace_id == workspace_id
    assert plan.underlying_id == underlying_id
    assert plan.origin_type is TradePlanOriginType.CANDIDATE_EVALUATION
    assert plan.candidate_id == candidate_id
    assert plan.candidate_evaluation_id == first_evaluation_id
    assert plan.candidate_evaluation_id != later_evaluation_id

    assert version.trade_plan_id == plan.id
    assert version.version == 1
    assert version.status is TradePlanStatus.DRAFT

    origins.candidate_origin.assert_awaited_once_with(
        workspace_id,
        candidate_id,
        first_evaluation_id,
    )
    uow.plans.add.assert_awaited_once_with(plan)
    uow.versions.add.assert_awaited_once_with(version)
    assert uow.events.add.await_count == 2
    uow.commit.assert_awaited_once_with()

    # A later immutable CandidateEvaluation exists independently. The already-created
    # TradePlan remains pinned to the exact evaluation selected at handoff time.
    assert later_evaluation_id != first_evaluation_id
    assert plan.candidate_evaluation_id == first_evaluation_id
