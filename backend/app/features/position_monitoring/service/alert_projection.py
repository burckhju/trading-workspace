"""Read-only operational attention projection over the dynamic stop contract."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from app.features.position_monitoring.service.dynamic_stop import (
    DYNAMIC_STOP_POLICY_VERSION,
    DynamicStopProjection,
    DynamicStopService,
)
from app.features.position_monitoring.service.phase_engine import PositionPhase
from app.features.position_monitoring.service.position_analytics import PositionAnalyticsStatus

POSITION_ALERT_POLICY_VERSION = "POSITION_ALERT_V1"


class PositionAlertLevel(StrEnum):
    NORMAL = "NORMAL"
    ATTENTION = "ATTENTION"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class PositionAlertProjection:
    trade_id: UUID
    position_id: UUID
    alert_level: PositionAlertLevel | None
    attention_required: bool
    quality_status: PositionAnalyticsStatus
    reason: str
    candidate_stop: Decimal | None
    latest_price: Decimal | None
    phase: PositionPhase | None
    policy_version: str
    dynamic_stop_policy_version: str
    analysis_run_id: UUID | None


def project_position_alert(stop: DynamicStopProjection) -> PositionAlertProjection:
    """Translate the stable dynamic-stop output into an operational attention state."""
    if stop.quality_status is not PositionAnalyticsStatus.AVAILABLE:
        return PositionAlertProjection(
            trade_id=stop.trade_id,
            position_id=stop.position_id,
            alert_level=None,
            attention_required=False,
            quality_status=stop.quality_status,
            reason=stop.reason,
            candidate_stop=stop.candidate_stop,
            latest_price=stop.latest_price,
            phase=stop.phase,
            policy_version=POSITION_ALERT_POLICY_VERSION,
            dynamic_stop_policy_version=DYNAMIC_STOP_POLICY_VERSION,
            analysis_run_id=stop.analysis_run_id,
        )
    if stop.breached is None or stop.phase is None:
        return PositionAlertProjection(
            trade_id=stop.trade_id,
            position_id=stop.position_id,
            alert_level=None,
            attention_required=False,
            quality_status=PositionAnalyticsStatus.ERROR,
            reason="POSITION_ALERT_DEPENDENCY_INCOMPLETE",
            candidate_stop=stop.candidate_stop,
            latest_price=stop.latest_price,
            phase=stop.phase,
            policy_version=POSITION_ALERT_POLICY_VERSION,
            dynamic_stop_policy_version=DYNAMIC_STOP_POLICY_VERSION,
            analysis_run_id=stop.analysis_run_id,
        )
    if stop.breached:
        level = PositionAlertLevel.CRITICAL
        attention_required = True
        reason = "DYNAMIC_STOP_BREACHED"
    elif stop.phase is PositionPhase.PEAK_PROTECTION:
        level = PositionAlertLevel.ATTENTION
        attention_required = True
        reason = "PEAK_PROTECTION_ACTIVE"
    else:
        level = PositionAlertLevel.NORMAL
        attention_required = False
        reason = "NO_POSITION_ATTENTION_REQUIRED"
    return PositionAlertProjection(
        trade_id=stop.trade_id,
        position_id=stop.position_id,
        alert_level=level,
        attention_required=attention_required,
        quality_status=PositionAnalyticsStatus.AVAILABLE,
        reason=reason,
        candidate_stop=stop.candidate_stop,
        latest_price=stop.latest_price,
        phase=stop.phase,
        policy_version=POSITION_ALERT_POLICY_VERSION,
        dynamic_stop_policy_version=DYNAMIC_STOP_POLICY_VERSION,
        analysis_run_id=stop.analysis_run_id,
    )


class PositionAlertProjectionService:
    """Expose operational attention without creating persisted Alert truth."""

    def __init__(self, *, dynamic_stop: DynamicStopService) -> None:
        self._dynamic_stop = dynamic_stop

    async def for_trade(self, trade_id: UUID) -> PositionAlertProjection | None:
        stop = await self._dynamic_stop.for_trade(trade_id)
        if stop is None:
            return None
        return project_position_alert(stop)
