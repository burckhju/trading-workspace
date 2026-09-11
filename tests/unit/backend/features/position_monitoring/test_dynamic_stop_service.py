from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.features.position_monitoring.service.dynamic_stop import DynamicStopService
from app.features.position_monitoring.service.phase_engine import (
    PHASE_POLICY_VERSION,
    PositionPhase,
    PositionPhaseProjection,
)
from app.features.position_monitoring.service.position_analytics import (
    PositionAnalytics,
    PositionAnalyticsStatus,
)
from app.features.position_monitoring.service.score_engine import (
    SCORE_POLICY_VERSION,
    PositionScoreProjection,
)


class AnalyticsStub:
    def __init__(self, value: PositionAnalytics | None) -> None:
        self.value = value

    async def for_trade(self, trade_id: UUID) -> PositionAnalytics | None:
        return self.value


class PhaseStub:
    def __init__(self, value: PositionPhaseProjection | None) -> None:
        self.value = value

    async def for_trade(self, trade_id: UUID) -> PositionPhaseProjection | None:
        return self.value


class ScoreStub:
    def __init__(self, value: PositionScoreProjection | None) -> None:
        self.value = value

    async def for_trade(self, trade_id: UUID) -> PositionScoreProjection | None:
        return self.value


class SessionStub:
    def __init__(self, run: object | None) -> None:
        self.run = run

    async def scalar(self, statement: object) -> object | None:
        return self.run


class DatabaseStub:
    def __init__(self, run: object | None) -> None:
        self.run = run

    @asynccontextmanager
    async def session_context(self):
        yield SessionStub(self.run)


def analytics(
    *,
    status: PositionAnalyticsStatus = PositionAnalyticsStatus.AVAILABLE,
    reason: str = "POSITION_ANALYTICS_AVAILABLE",
    run_id: UUID | None = None,
    peak: Decimal | None = Decimal("125"),
) -> PositionAnalytics:
    return PositionAnalytics(
        trade_id=uuid4(),
        position_id=uuid4(),
        entry_executed_at=datetime(2026, 9, 1, tzinfo=UTC),
        highest_high_since_entry=peak,
        analysis_run_id=run_id or uuid4(),
        market_data_observed_at=datetime(2026, 9, 10, tzinfo=UTC),
        quality_status=status,
        reason=reason,
        sessions_since_entry=12,
    )


def phase(
    value: PositionAnalytics,
    *,
    status: PositionAnalyticsStatus = PositionAnalyticsStatus.AVAILABLE,
    phase_value: PositionPhase | None = PositionPhase.TREND,
    run_id: UUID | None = None,
    reason: str = "POSITION_PHASE_TREND",
) -> PositionPhaseProjection:
    return PositionPhaseProjection(
        trade_id=value.trade_id,
        position_id=value.position_id,
        phase=phase_value,
        quality_status=status,
        reason=reason,
        policy_version=PHASE_POLICY_VERSION,
        analysis_run_id=value.analysis_run_id if run_id is None else run_id,
        sessions_since_entry=value.sessions_since_entry,
    )


def scores(
    value: PositionAnalytics,
    *,
    status: PositionAnalyticsStatus = PositionAnalyticsStatus.AVAILABLE,
    trend_score: int | None = 80,
    peak_score: int | None = 50,
    run_id: UUID | None = None,
    reason: str = "POSITION_SCORES_AVAILABLE",
) -> PositionScoreProjection:
    return PositionScoreProjection(
        trade_id=value.trade_id,
        position_id=value.position_id,
        trend_score=trend_score,
        peak_score=peak_score,
        trend_components={},
        peak_components={},
        quality_status=status,
        reason=reason,
        policy_version=SCORE_POLICY_VERSION,
        analysis_run_id=value.analysis_run_id if run_id is None else run_id,
        sessions_since_entry=value.sessions_since_entry,
    )


def service(
    value: PositionAnalytics,
    *,
    phase_value: PositionPhaseProjection | None = None,
    score_value: PositionScoreProjection | None = None,
    run: object | None = None,
) -> DynamicStopService:
    return DynamicStopService(
        database=DatabaseStub(run),  # type: ignore[arg-type]
        position_analytics=AnalyticsStub(value),  # type: ignore[arg-type]
        phase_service=PhaseStub(phase_value if phase_value is not None else phase(value)),  # type: ignore[arg-type]
        score_service=ScoreStub(score_value if score_value is not None else scores(value)),  # type: ignore[arg-type]
    )


@pytest.mark.asyncio
async def test_service_projects_dynamic_stop_from_matching_provenance() -> None:
    value = analytics()
    run = SimpleNamespace(metrics={"latest_price": "120", "atr_14": "4"})

    result = await service(value, run=run).for_trade(value.trade_id)

    assert result is not None
    assert result.quality_status is PositionAnalyticsStatus.AVAILABLE
    assert result.candidate_stop == Decimal("119.0")
    assert result.atr_multiple == Decimal("1.5")
    assert result.phase is PositionPhase.TREND
    assert result.trend_score == 80
    assert result.peak_score == 50
    assert result.breached is False
    assert result.reason == "DYNAMIC_STOP_AVAILABLE"


@pytest.mark.asyncio
async def test_service_preserves_unavailable_upstream_health() -> None:
    value = analytics(status=PositionAnalyticsStatus.STALE, reason="MARKET_DATA_STALE")

    result = await service(value).for_trade(value.trade_id)

    assert result is not None
    assert result.quality_status is PositionAnalyticsStatus.STALE
    assert result.reason == "MARKET_DATA_STALE"
    assert result.candidate_stop is None


@pytest.mark.asyncio
async def test_service_fails_closed_when_dependency_is_missing() -> None:
    value = analytics()
    result = await DynamicStopService(
        database=DatabaseStub(None),  # type: ignore[arg-type]
        position_analytics=AnalyticsStub(value),  # type: ignore[arg-type]
        phase_service=PhaseStub(None),  # type: ignore[arg-type]
        score_service=ScoreStub(scores(value)),  # type: ignore[arg-type]
    ).for_trade(value.trade_id)

    assert result is not None
    assert result.reason == "STOP_DEPENDENCY_MISSING"
    assert result.quality_status is PositionAnalyticsStatus.ERROR


@pytest.mark.asyncio
async def test_service_propagates_phase_failure() -> None:
    value = analytics()
    phase_value = phase(
        value,
        status=PositionAnalyticsStatus.INSUFFICIENT,
        phase_value=None,
        reason="NO_COMPLETED_SESSION_SINCE_ENTRY",
    )

    result = await service(value, phase_value=phase_value).for_trade(value.trade_id)

    assert result is not None
    assert result.quality_status is PositionAnalyticsStatus.INSUFFICIENT
    assert result.reason == "NO_COMPLETED_SESSION_SINCE_ENTRY"


@pytest.mark.asyncio
async def test_service_propagates_score_failure() -> None:
    value = analytics()
    score_value = scores(
        value,
        status=PositionAnalyticsStatus.MISSING,
        trend_score=None,
        peak_score=None,
        reason="SCORE_ANALYSIS_RUN_MISSING",
    )

    result = await service(value, score_value=score_value).for_trade(value.trade_id)

    assert result is not None
    assert result.quality_status is PositionAnalyticsStatus.MISSING
    assert result.reason == "SCORE_ANALYSIS_RUN_MISSING"


@pytest.mark.asyncio
async def test_service_rejects_incomplete_and_mismatched_dependencies() -> None:
    value = analytics()
    incomplete = phase(value, phase_value=None)
    result = await service(value, phase_value=incomplete).for_trade(value.trade_id)
    assert result is not None
    assert result.reason == "STOP_DEPENDENCY_INCOMPLETE"

    mismatch = phase(value, run_id=uuid4())
    result = await service(value, phase_value=mismatch).for_trade(value.trade_id)
    assert result is not None
    assert result.reason == "STOP_PROVENANCE_MISMATCH"


@pytest.mark.asyncio
async def test_service_rejects_missing_run_invalid_metrics_and_non_positive_atr() -> None:
    value = analytics()

    result = await service(value, run=None).for_trade(value.trade_id)
    assert result is not None
    assert result.reason == "STOP_ANALYSIS_RUN_MISSING"

    invalid_run = SimpleNamespace(metrics={"latest_price": "bad", "atr_14": "4"})
    result = await service(value, run=invalid_run).for_trade(value.trade_id)
    assert result is not None
    assert result.reason == "STOP_REQUIRED_METRICS_INVALID"

    zero_atr_run = SimpleNamespace(metrics={"latest_price": "120", "atr_14": "0"})
    result = await service(value, run=zero_atr_run).for_trade(value.trade_id)
    assert result is not None
    assert result.reason == "STOP_ATR_NON_POSITIVE"


@pytest.mark.asyncio
async def test_service_rejects_non_positive_candidate_and_reports_breach() -> None:
    value = analytics(peak=Decimal("2"))
    result = await service(
        value,
        run=SimpleNamespace(metrics={"latest_price": "1", "atr_14": "4"}),
    ).for_trade(value.trade_id)
    assert result is not None
    assert result.reason == "STOP_CANDIDATE_NON_POSITIVE"

    value = analytics(peak=Decimal("125"))
    result = await service(
        value,
        run=SimpleNamespace(metrics={"latest_price": "119", "atr_14": "4"}),
    ).for_trade(value.trade_id)
    assert result is not None
    assert result.breached is True
    assert result.reason == "DYNAMIC_STOP_BREACHED"


def test_parse_market_inputs_fails_closed() -> None:
    assert DynamicStopService._parse_market_inputs({}) is None
    assert DynamicStopService._parse_market_inputs({"latest_price": "0", "atr_14": "4"}) is None
    assert DynamicStopService._parse_market_inputs({"latest_price": "120", "atr_14": "-1"}) is None
    assert DynamicStopService._parse_market_inputs({"latest_price": "120", "atr_14": "4"}) == (
        Decimal("120"),
        Decimal("4"),
    )
