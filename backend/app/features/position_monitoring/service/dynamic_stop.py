"""Read-only dynamic stop projection over phase and score contracts."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy import select

from app.database import DatabaseManager
from app.features.analysis.persistence.models import MarketAnalysisRunModel
from app.features.position_monitoring.service.phase_engine import (
    PHASE_POLICY_VERSION,
    PositionPhase,
    PositionPhaseService,
)
from app.features.position_monitoring.service.position_analytics import (
    PositionAnalytics,
    PositionAnalyticsStatus,
    PositionAwareAnalyticsService,
)
from app.features.position_monitoring.service.score_engine import (
    SCORE_POLICY_VERSION,
    PositionScoreService,
)

DYNAMIC_STOP_POLICY_VERSION = "DYNAMIC_STOP_V1"
TREND_TIGHTEN_SCORE = 80
PEAK_TIGHTEN_SCORE = 75

PHASE_BASE_ATR_MULTIPLES: dict[PositionPhase, Decimal] = {
    PositionPhase.BUILDING: Decimal("3"),
    PositionPhase.CONFIRMED: Decimal("2.5"),
    PositionPhase.TREND: Decimal("2"),
    PositionPhase.PEAK_PROTECTION: Decimal("1.5"),
}


@dataclass(frozen=True, slots=True)
class DynamicStopInputs:
    phase: PositionPhase
    trend_score: int
    peak_score: int
    latest_price: Decimal
    atr_14: Decimal
    highest_high_since_entry: Decimal


@dataclass(frozen=True, slots=True)
class DynamicStopResult:
    candidate_stop: Decimal
    atr_multiple: Decimal
    breached: bool
    distance_to_stop: Decimal


@dataclass(frozen=True, slots=True)
class DynamicStopProjection:
    trade_id: UUID
    position_id: UUID
    candidate_stop: Decimal | None
    atr_multiple: Decimal | None
    latest_price: Decimal | None
    atr_14: Decimal | None
    highest_high_since_entry: Decimal | None
    breached: bool | None
    distance_to_stop: Decimal | None
    phase: PositionPhase | None
    trend_score: int | None
    peak_score: int | None
    quality_status: PositionAnalyticsStatus
    reason: str
    policy_version: str
    phase_policy_version: str
    score_policy_version: str
    analysis_run_id: UUID | None


def resolve_atr_multiple(inputs: DynamicStopInputs) -> Decimal:
    """Resolve the explicit DYNAMIC_STOP_V1 ATR distance."""
    multiple = PHASE_BASE_ATR_MULTIPLES[inputs.phase]
    if inputs.phase is PositionPhase.TREND and inputs.trend_score >= TREND_TIGHTEN_SCORE:
        return Decimal("1.5")
    if inputs.phase is PositionPhase.PEAK_PROTECTION and inputs.peak_score >= PEAK_TIGHTEN_SCORE:
        return Decimal("1")
    return multiple


def calculate_dynamic_stop(inputs: DynamicStopInputs) -> DynamicStopResult:
    """Calculate an indicative stop candidate without mutating position state."""
    atr_multiple = resolve_atr_multiple(inputs)
    candidate_stop = inputs.highest_high_since_entry - inputs.atr_14 * atr_multiple
    return DynamicStopResult(
        candidate_stop=candidate_stop,
        atr_multiple=atr_multiple,
        breached=inputs.latest_price <= candidate_stop,
        distance_to_stop=inputs.latest_price - candidate_stop,
    )


class DynamicStopService:
    """Compose analytics, phase and scores into a read-only stop projection."""

    def __init__(
        self,
        *,
        database: DatabaseManager,
        position_analytics: PositionAwareAnalyticsService,
        phase_service: PositionPhaseService,
        score_service: PositionScoreService,
    ) -> None:
        self._database = database
        self._position_analytics = position_analytics
        self._phase_service = phase_service
        self._score_service = score_service

    async def for_trade(self, trade_id: UUID) -> DynamicStopProjection | None:
        analytics = await self._position_analytics.for_trade(trade_id)
        if analytics is None:
            return None
        if analytics.quality_status is not PositionAnalyticsStatus.AVAILABLE:
            return self._unavailable(analytics, analytics.quality_status, analytics.reason)

        phase = await self._phase_service.for_trade(trade_id)
        scores = await self._score_service.for_trade(trade_id)
        if phase is None or scores is None:
            return self._unavailable(
                analytics,
                PositionAnalyticsStatus.ERROR,
                "STOP_DEPENDENCY_MISSING",
            )
        if phase.quality_status is not PositionAnalyticsStatus.AVAILABLE:
            return self._unavailable(analytics, phase.quality_status, phase.reason)
        if scores.quality_status is not PositionAnalyticsStatus.AVAILABLE:
            return self._unavailable(analytics, scores.quality_status, scores.reason)
        if phase.phase is None or scores.trend_score is None or scores.peak_score is None:
            return self._unavailable(
                analytics,
                PositionAnalyticsStatus.ERROR,
                "STOP_DEPENDENCY_INCOMPLETE",
            )
        if (
            analytics.analysis_run_id is None
            or analytics.highest_high_since_entry is None
            or phase.analysis_run_id != analytics.analysis_run_id
            or scores.analysis_run_id != analytics.analysis_run_id
        ):
            return self._unavailable(
                analytics,
                PositionAnalyticsStatus.ERROR,
                "STOP_PROVENANCE_MISMATCH",
            )

        async with self._database.session_context() as session:
            run = await session.scalar(
                select(MarketAnalysisRunModel).where(
                    MarketAnalysisRunModel.id == analytics.analysis_run_id
                )
            )
        if run is None:
            return self._unavailable(
                analytics,
                PositionAnalyticsStatus.MISSING,
                "STOP_ANALYSIS_RUN_MISSING",
            )

        parsed = self._parse_market_inputs(run.metrics)
        if parsed is None:
            return self._unavailable(
                analytics,
                PositionAnalyticsStatus.ERROR,
                "STOP_REQUIRED_METRICS_INVALID",
            )
        latest_price, atr_14 = parsed
        if atr_14 <= 0:
            return self._unavailable(
                analytics,
                PositionAnalyticsStatus.ERROR,
                "STOP_ATR_NON_POSITIVE",
            )

        inputs = DynamicStopInputs(
            phase=phase.phase,
            trend_score=scores.trend_score,
            peak_score=scores.peak_score,
            latest_price=latest_price,
            atr_14=atr_14,
            highest_high_since_entry=analytics.highest_high_since_entry,
        )
        result = calculate_dynamic_stop(inputs)
        if result.candidate_stop <= 0:
            return self._unavailable(
                analytics,
                PositionAnalyticsStatus.ERROR,
                "STOP_CANDIDATE_NON_POSITIVE",
            )

        return DynamicStopProjection(
            trade_id=analytics.trade_id,
            position_id=analytics.position_id,
            candidate_stop=result.candidate_stop,
            atr_multiple=result.atr_multiple,
            latest_price=latest_price,
            atr_14=atr_14,
            highest_high_since_entry=analytics.highest_high_since_entry,
            breached=result.breached,
            distance_to_stop=result.distance_to_stop,
            phase=phase.phase,
            trend_score=scores.trend_score,
            peak_score=scores.peak_score,
            quality_status=PositionAnalyticsStatus.AVAILABLE,
            reason=("DYNAMIC_STOP_BREACHED" if result.breached else "DYNAMIC_STOP_AVAILABLE"),
            policy_version=DYNAMIC_STOP_POLICY_VERSION,
            phase_policy_version=PHASE_POLICY_VERSION,
            score_policy_version=SCORE_POLICY_VERSION,
            analysis_run_id=analytics.analysis_run_id,
        )

    @staticmethod
    def _parse_market_inputs(metrics: dict[str, str | None]) -> tuple[Decimal, Decimal] | None:
        try:
            latest_raw = metrics.get("latest_price")
            atr_raw = metrics.get("atr_14")
            if latest_raw is None or atr_raw is None:
                return None
            latest_price = Decimal(latest_raw)
            atr_14 = Decimal(atr_raw)
        except (InvalidOperation, TypeError):
            return None
        if latest_price <= 0 or atr_14 < 0:
            return None
        return latest_price, atr_14

    @staticmethod
    def _unavailable(
        analytics: PositionAnalytics,
        status: PositionAnalyticsStatus,
        reason: str,
    ) -> DynamicStopProjection:
        return DynamicStopProjection(
            trade_id=analytics.trade_id,
            position_id=analytics.position_id,
            candidate_stop=None,
            atr_multiple=None,
            latest_price=None,
            atr_14=None,
            highest_high_since_entry=analytics.highest_high_since_entry,
            breached=None,
            distance_to_stop=None,
            phase=None,
            trend_score=None,
            peak_score=None,
            quality_status=status,
            reason=reason,
            policy_version=DYNAMIC_STOP_POLICY_VERSION,
            phase_policy_version=PHASE_POLICY_VERSION,
            score_policy_version=SCORE_POLICY_VERSION,
            analysis_run_id=analytics.analysis_run_id,
        )
