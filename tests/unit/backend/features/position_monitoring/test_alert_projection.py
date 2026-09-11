from decimal import Decimal
from uuid import uuid4

from app.features.position_monitoring.service.alert_projection import (
    POSITION_ALERT_POLICY_VERSION,
    PositionAlertLevel,
    project_position_alert,
)
from app.features.position_monitoring.service.dynamic_stop import (
    DYNAMIC_STOP_POLICY_VERSION,
    DynamicStopProjection,
)
from app.features.position_monitoring.service.phase_engine import PositionPhase
from app.features.position_monitoring.service.position_analytics import PositionAnalyticsStatus


def _stop(*, phase: PositionPhase, breached: bool) -> DynamicStopProjection:
    return DynamicStopProjection(
        trade_id=uuid4(),
        position_id=uuid4(),
        candidate_stop=Decimal("98"),
        atr_multiple=Decimal("1.5"),
        latest_price=Decimal("100"),
        atr_14=Decimal("2"),
        highest_high_since_entry=Decimal("101"),
        breached=breached,
        distance_to_stop=Decimal("2"),
        phase=phase,
        trend_score=80,
        peak_score=75,
        quality_status=PositionAnalyticsStatus.AVAILABLE,
        reason="DYNAMIC_STOP_AVAILABLE",
        policy_version=DYNAMIC_STOP_POLICY_VERSION,
        phase_policy_version="POSITION_PHASE_V1",
        score_policy_version="POSITION_SCORE_V1",
        analysis_run_id=uuid4(),
    )


def test_breached_dynamic_stop_is_critical() -> None:
    projection = project_position_alert(
        _stop(phase=PositionPhase.PEAK_PROTECTION, breached=True)
    )

    assert projection.alert_level is PositionAlertLevel.CRITICAL
    assert projection.attention_required is True
    assert projection.reason == "DYNAMIC_STOP_BREACHED"
    assert projection.policy_version == POSITION_ALERT_POLICY_VERSION


def test_peak_protection_requires_attention_without_stop_breach() -> None:
    projection = project_position_alert(
        _stop(phase=PositionPhase.PEAK_PROTECTION, breached=False)
    )

    assert projection.alert_level is PositionAlertLevel.ATTENTION
    assert projection.attention_required is True
    assert projection.reason == "PEAK_PROTECTION_ACTIVE"


def test_regular_phase_is_normal_without_attention() -> None:
    projection = project_position_alert(
        _stop(phase=PositionPhase.TREND, breached=False)
    )

    assert projection.alert_level is PositionAlertLevel.NORMAL
    assert projection.attention_required is False
    assert projection.reason == "NO_POSITION_ATTENTION_REQUIRED"


def test_unavailable_dynamic_stop_fails_closed() -> None:
    stop = _stop(phase=PositionPhase.TREND, breached=False)
    stop = DynamicStopProjection(
        trade_id=stop.trade_id,
        position_id=stop.position_id,
        candidate_stop=None,
        atr_multiple=None,
        latest_price=None,
        atr_14=None,
        highest_high_since_entry=None,
        breached=None,
        distance_to_stop=None,
        phase=None,
        trend_score=None,
        peak_score=None,
        quality_status=PositionAnalyticsStatus.STALE,
        reason="COMPLETED_DAILY_PRICE_STALE",
        policy_version=DYNAMIC_STOP_POLICY_VERSION,
        phase_policy_version="POSITION_PHASE_V1",
        score_policy_version="POSITION_SCORE_V1",
        analysis_run_id=uuid4(),
    )

    projection = project_position_alert(stop)

    assert projection.alert_level is None
    assert projection.attention_required is False
    assert projection.quality_status is PositionAnalyticsStatus.STALE
    assert projection.reason == "COMPLETED_DAILY_PRICE_STALE"
