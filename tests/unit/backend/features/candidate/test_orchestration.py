from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.features.analysis.domain.enums import AnalysisQualityStatus, AnalysisStatus
from app.features.analysis.persistence.models import (
    MarketAnalysisCriterionModel,
    MarketAnalysisModel,
    MarketAnalysisRunModel,
    MarketAnalysisSnapshotRowModel,
)
from app.features.candidate.domain.enums import CandidateQualification
from app.features.candidate.domain.qualification import evaluate_candidate
from app.features.candidate.service.orchestration import (
    StoredAnalysisReference,
    TopDownEvaluationOrchestrator,
    _ResolvedAnalysis,
)


def _resolved(
    *, underlying_id=None, end=Decimal("110"), status=AnalysisStatus.COMPLETED.value
):
    underlying_id = underlying_id or uuid4()
    analysis_id = uuid4()
    run_id = uuid4()
    analysis = MarketAnalysisModel(
        id=analysis_id,
        workspace_id=uuid4(),
        underlying_id=underlying_id,
        listing_id=uuid4(),
        created_at=datetime.now(UTC),
        created_by="test",
    )
    run = MarketAnalysisRunModel(
        id=run_id,
        analysis_id=analysis_id,
        version=3,
        status=status,
        quality_status=AnalysisQualityStatus.GOOD.value,
        model_id="EOD_TREND_MOMENTUM",
        model_version="1.0.0",
        parameters={},
        metrics={},
        notes=[],
        data_sources=["test"],
        input_hash="a" * 64,
        observation_count=61,
        analysis_time=datetime.now(UTC),
        correlation_id=None,
        error_message=None,
    )
    classifications = {
        "LONG_TREND": "POSITIVE",
        "MEDIUM_TREND": "POSITIVE",
        "SHORT_TREND": "POSITIVE",
        "MOMENTUM_60": "POSITIVE",
        "VOLATILITY": "NEUTRAL",
        "RANGE_POSITION": "POSITIVE",
    }
    values = {"VOLATILITY": Decimal("0.30"), "RANGE_POSITION": Decimal("0.70")}
    criteria = {
        code: MarketAnalysisCriterionModel(
            id=uuid4(),
            run_id=run_id,
            code=code,
            classification=classification,
            value=values.get(code),
            explanation="test",
        )
        for code, classification in classifications.items()
    }
    start = date(2026, 1, 1)
    rows = []
    for index in range(61):
        value = Decimal("100") if index < 60 else end
        rows.append(
            MarketAnalysisSnapshotRowModel(
                id=uuid4(),
                run_id=run_id,
                trading_date=start + timedelta(days=index),
                open=value,
                high=value,
                low=value,
                close=value,
                adjusted_close=value,
                volume=Decimal("1"),
                currency="EUR",
                provider="TEST",
                provider_symbol="TEST",
                quality_status="GOOD",
                warnings=[],
            )
        )
    return _ResolvedAnalysis(analysis, run, criteria, tuple(rows))


@pytest.mark.asyncio
async def test_orchestrator_derives_inputs_and_provenance_from_stored_analyses() -> (
    None
):
    workspace_id = uuid4()
    candidate_underlying_id = uuid4()
    market = _resolved(end=Decimal("105"))
    sector = _resolved(end=Decimal("108"))
    underlying = _resolved(underlying_id=candidate_underlying_id, end=Decimal("111"))
    for item in (market, sector, underlying):
        item.analysis.workspace_id = workspace_id

    orchestrator = TopDownEvaluationOrchestrator.__new__(TopDownEvaluationOrchestrator)
    mapping = {
        market.analysis.id: market,
        sector.analysis.id: sector,
        underlying.analysis.id: underlying,
    }

    async def load(_workspace_id, ref):
        assert _workspace_id == workspace_id
        return mapping[ref.analysis_id]

    orchestrator._load = load  # type: ignore[method-assign]
    result = await orchestrator.resolve(
        workspace_id=workspace_id,
        candidate_underlying_id=candidate_underlying_id,
        market=StoredAnalysisReference(market.analysis.id, 3),
        sector=StoredAnalysisReference(sector.analysis.id, 3),
        underlying=StoredAnalysisReference(underlying.analysis.id, 3),
    )

    evaluation = evaluate_candidate(result.value)
    assert evaluation.qualification is CandidateQualification.QUALIFIED
    assert result.sources["UNDERLYING"].model_id == "EOD_TREND_MOMENTUM"
    assert result.sources["UNDERLYING"].version == 3


@pytest.mark.asyncio
async def test_orchestrator_rejects_underlying_analysis_for_other_underlying() -> None:
    workspace_id = uuid4()
    candidate_underlying_id = uuid4()
    market = _resolved(end=Decimal("105"))
    sector = _resolved(end=Decimal("108"))
    underlying = _resolved(end=Decimal("111"))
    for item in (market, sector, underlying):
        item.analysis.workspace_id = workspace_id

    orchestrator = TopDownEvaluationOrchestrator.__new__(TopDownEvaluationOrchestrator)
    mapping = {
        market.analysis.id: market,
        sector.analysis.id: sector,
        underlying.analysis.id: underlying,
    }

    async def load(_workspace_id, ref):
        return mapping[ref.analysis_id]

    orchestrator._load = load  # type: ignore[method-assign]
    with pytest.raises(ValueError, match="does not belong"):
        await orchestrator.resolve(
            workspace_id=workspace_id,
            candidate_underlying_id=candidate_underlying_id,
            market=StoredAnalysisReference(market.analysis.id, 3),
            sector=StoredAnalysisReference(sector.analysis.id, 3),
            underlying=StoredAnalysisReference(underlying.analysis.id, 3),
        )
