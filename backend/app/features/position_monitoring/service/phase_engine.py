"""Deterministic read-only phase classification for open positions."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select

from app.database import DatabaseManager
from app.features.analysis.persistence.models import MarketAnalysisRunModel
from app.features.position_monitoring.service.position_analytics import (
    PositionAnalytics,
    PositionAnalyticsStatus,
    PositionAwareAnalyticsService,
)

PHASE_POLICY_VERSION = "POSITION_PHASE_V1"
MIN_CONFIRMED_SESSIONS = 3
MIN_TREND_SESSIONS = 10
TREND_RSI_FLOOR = Decimal("50")
PEAK_RSI_THRESHOLD = Decimal("70")
PEAK_ATR_DISTANCE_MULTIPLE = Decimal("1")


class PositionPhase(StrEnum):
    BUILDING = "BUILDING"
    CONFIRMED = "CONFIRMED"
    TREND = "TREND"
    PEAK_PROTECTION = "PEAK_PROTECTION"


@dataclass(frozen=True, slots=True)
class PhaseInputs:
    sessions_since_entry: int
    latest_price: Decimal
    sma_20: Decimal
    sma_50: Decimal
    sma_200: Decimal
    atr_14: Decimal
    rsi_14: Decimal
    highest_high_since_entry: Decimal


@dataclass(frozen=True, slots=True)
class PositionPhaseProjection:
    trade_id: UUID
    position_id: UUID
    phase: PositionPhase | None
    quality_status: PositionAnalyticsStatus
    reason: str
    policy_version: str
    analysis_run_id: UUID | None
    sessions_since_entry: int | None


def classify_phase(inputs: PhaseInputs) -> PositionPhase:
    """Classify one position from immutable analytics using the explicit V1 policy.

    V1 is intentionally monotonic in rule strength, not persisted lifecycle state:
    BUILDING -> CONFIRMED -> TREND -> PEAK_PROTECTION. Every call is reproducible
    from the supplied analytics and does not depend on prior classifications.
    """
    short_structure = inputs.latest_price > inputs.sma_20 > inputs.sma_50
    long_structure = short_structure and inputs.sma_50 > inputs.sma_200
    trend_ready = (
        inputs.sessions_since_entry >= MIN_TREND_SESSIONS
        and long_structure
        and inputs.rsi_14 >= TREND_RSI_FLOOR
    )
    peak_distance = inputs.highest_high_since_entry - inputs.latest_price
    peak_ready = (
        trend_ready
        and inputs.rsi_14 >= PEAK_RSI_THRESHOLD
        and peak_distance >= 0
        and peak_distance <= inputs.atr_14 * PEAK_ATR_DISTANCE_MULTIPLE
    )

    if peak_ready:
        return PositionPhase.PEAK_PROTECTION
    if trend_ready:
        return PositionPhase.TREND
    if inputs.sessions_since_entry >= MIN_CONFIRMED_SESSIONS and short_structure:
        return PositionPhase.CONFIRMED
    return PositionPhase.BUILDING


class PositionPhaseService:
    """Read-only phase projection layered on PositionAwareAnalyticsService."""

    def __init__(
        self,
        *,
        database: DatabaseManager,
        position_analytics: PositionAwareAnalyticsService,
    ) -> None:
        self._database = database
        self._position_analytics = position_analytics

    async def for_trade(self, trade_id: UUID) -> PositionPhaseProjection | None:
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
                "PHASE_INPUTS_INCOMPLETE",
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
                "PHASE_ANALYSIS_RUN_MISSING",
            )
        if run.metrics.get("indicator_set_version") != "POSITION_ANALYTICS_V1":
            return self._unavailable(
                analytics,
                PositionAnalyticsStatus.ERROR,
                "PHASE_INDICATOR_SET_UNSUPPORTED",
            )

        inputs = self._parse_inputs(analytics, run.metrics)
        if inputs is None:
            return self._unavailable(
                analytics,
                PositionAnalyticsStatus.ERROR,
                "PHASE_REQUIRED_METRICS_INVALID",
            )

        phase = classify_phase(inputs)
        return PositionPhaseProjection(
            trade_id=analytics.trade_id,
            position_id=analytics.position_id,
            phase=phase,
            quality_status=PositionAnalyticsStatus.AVAILABLE,
            reason=f"POSITION_PHASE_{phase.value}",
            policy_version=PHASE_POLICY_VERSION,
            analysis_run_id=analytics.analysis_run_id,
            sessions_since_entry=analytics.sessions_since_entry,
        )

    @staticmethod
    def _parse_inputs(
        analytics: PositionAnalytics,
        metrics: dict[str, str | None],
    ) -> PhaseInputs | None:
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
        return PhaseInputs(
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
    ) -> PositionPhaseProjection:
        return PositionPhaseProjection(
            trade_id=analytics.trade_id,
            position_id=analytics.position_id,
            phase=None,
            quality_status=status,
            reason=reason,
            policy_version=PHASE_POLICY_VERSION,
            analysis_run_id=analytics.analysis_run_id,
            sessions_since_entry=analytics.sessions_since_entry,
        )
