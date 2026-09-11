"""Deterministic explainable TrendScore and PeakScore projections."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy import select

from app.database import DatabaseManager
from app.features.analysis.persistence.models import MarketAnalysisRunModel
from app.features.position_monitoring.service.position_analytics import (
    PositionAnalytics,
    PositionAnalyticsStatus,
    PositionAwareAnalyticsService,
)

SCORE_POLICY_VERSION = "POSITION_SCORE_V1"
TREND_MIN_SESSIONS = 10
TREND_RSI_FLOOR = Decimal("50")
PEAK_RSI_THRESHOLD = Decimal("70")
PEAK_ATR_DISTANCE_MULTIPLE = Decimal("1")


@dataclass(frozen=True, slots=True)
class ScoreInputs:
    sessions_since_entry: int
    latest_price: Decimal
    sma_20: Decimal
    sma_50: Decimal
    sma_200: Decimal
    atr_14: Decimal
    rsi_14: Decimal
    highest_high_since_entry: Decimal


@dataclass(frozen=True, slots=True)
class ScoreResult:
    value: int
    components: dict[str, int]


@dataclass(frozen=True, slots=True)
class PositionScoreProjection:
    trade_id: UUID
    position_id: UUID
    trend_score: int | None
    peak_score: int | None
    trend_components: dict[str, int]
    peak_components: dict[str, int]
    quality_status: PositionAnalyticsStatus
    reason: str
    policy_version: str
    analysis_run_id: UUID | None
    sessions_since_entry: int | None


def calculate_trend_score(inputs: ScoreInputs) -> ScoreResult:
    """Return an additive 0-100 trend-quality score under POSITION_SCORE_V1."""
    components = {
        "maturity": 20 if inputs.sessions_since_entry >= TREND_MIN_SESSIONS else 0,
        "price_above_sma20": 20 if inputs.latest_price > inputs.sma_20 else 0,
        "sma20_above_sma50": 20 if inputs.sma_20 > inputs.sma_50 else 0,
        "sma50_above_sma200": 20 if inputs.sma_50 > inputs.sma_200 else 0,
        "rsi_support": 20 if inputs.rsi_14 >= TREND_RSI_FLOOR else 0,
    }
    return ScoreResult(value=sum(components.values()), components=components)


def calculate_peak_score(inputs: ScoreInputs) -> ScoreResult:
    """Return an additive 0-100 peak-protection readiness score under V1."""
    trend_structure = inputs.latest_price > inputs.sma_20 > inputs.sma_50 > inputs.sma_200
    peak_distance = inputs.highest_high_since_entry - inputs.latest_price
    near_peak = (
        peak_distance >= 0
        and peak_distance <= inputs.atr_14 * PEAK_ATR_DISTANCE_MULTIPLE
    )
    components = {
        "trend_structure": 25 if trend_structure else 0,
        "maturity": 25 if inputs.sessions_since_entry >= TREND_MIN_SESSIONS else 0,
        "rsi_hot": 25 if inputs.rsi_14 >= PEAK_RSI_THRESHOLD else 0,
        "near_peak": 25 if near_peak else 0,
    }
    return ScoreResult(value=sum(components.values()), components=components)


class PositionScoreService:
    """Read-only score projection over immutable position-aware analytics."""

    def __init__(
        self,
        *,
        database: DatabaseManager,
        position_analytics: PositionAwareAnalyticsService,
    ) -> None:
        self._database = database
        self._position_analytics = position_analytics

    async def for_trade(self, trade_id: UUID) -> PositionScoreProjection | None:
        analytics = await self._position_analytics.for_trade(trade_id)
        if analytics is None:
            return None
        if analytics.quality_status is not PositionAnalyticsStatus.AVAILABLE:
            return self._unavailable(analytics, analytics.quality_status, analytics.reason)
        if (
            analytics.analysis_run_id is None
            or analytics.sessions_since_entry is None
            or analytics.highest_high_since_entry is None
        ):
            return self._unavailable(
                analytics,
                PositionAnalyticsStatus.ERROR,
                "SCORE_INPUTS_INCOMPLETE",
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
                "SCORE_ANALYSIS_RUN_MISSING",
            )
        if run.metrics.get("indicator_set_version") != "POSITION_ANALYTICS_V1":
            return self._unavailable(
                analytics,
                PositionAnalyticsStatus.ERROR,
                "SCORE_INDICATOR_SET_UNSUPPORTED",
            )

        inputs = self._parse_inputs(analytics, run.metrics)
        if inputs is None:
            return self._unavailable(
                analytics,
                PositionAnalyticsStatus.ERROR,
                "SCORE_REQUIRED_METRICS_INVALID",
            )

        trend = calculate_trend_score(inputs)
        peak = calculate_peak_score(inputs)
        return PositionScoreProjection(
            trade_id=analytics.trade_id,
            position_id=analytics.position_id,
            trend_score=trend.value,
            peak_score=peak.value,
            trend_components=trend.components,
            peak_components=peak.components,
            quality_status=PositionAnalyticsStatus.AVAILABLE,
            reason="POSITION_SCORES_AVAILABLE",
            policy_version=SCORE_POLICY_VERSION,
            analysis_run_id=analytics.analysis_run_id,
            sessions_since_entry=analytics.sessions_since_entry,
        )

    @staticmethod
    def _parse_inputs(
        analytics: PositionAnalytics,
        metrics: dict[str, str | None],
    ) -> ScoreInputs | None:
        required = (
            "latest_price",
            "sma_20",
            "sma_50",
            "sma_200",
            "atr_14",
            "rsi_14",
        )
        values: dict[str, Decimal] = {}
        try:
            for key in required:
                raw = metrics.get(key)
                if raw is None:
                    return None
                values[key] = Decimal(raw)
        except (InvalidOperation, TypeError):
            return None

        if values["atr_14"] < 0 or not Decimal("0") <= values["rsi_14"] <= Decimal("100"):
            return None
        if analytics.sessions_since_entry is None or analytics.highest_high_since_entry is None:
            return None
        return ScoreInputs(
            sessions_since_entry=analytics.sessions_since_entry,
            latest_price=values["latest_price"],
            sma_20=values["sma_20"],
            sma_50=values["sma_50"],
            sma_200=values["sma_200"],
            atr_14=values["atr_14"],
            rsi_14=values["rsi_14"],
            highest_high_since_entry=analytics.highest_high_since_entry,
        )

    @staticmethod
    def _unavailable(
        analytics: PositionAnalytics,
        status: PositionAnalyticsStatus,
        reason: str,
    ) -> PositionScoreProjection:
        return PositionScoreProjection(
            trade_id=analytics.trade_id,
            position_id=analytics.position_id,
            trend_score=None,
            peak_score=None,
            trend_components={},
            peak_components={},
            quality_status=status,
            reason=reason,
            policy_version=SCORE_POLICY_VERSION,
            analysis_run_id=analytics.analysis_run_id,
            sessions_since_entry=analytics.sessions_since_entry,
        )
