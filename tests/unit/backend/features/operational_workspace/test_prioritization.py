from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.features.operational_workspace.service.prioritization import prioritize_position_monitoring
from app.features.operational_workspace.service.read_model import OperationalAction
from app.features.position_monitoring.service.health import (
    MonitoringHealthStatus,
    PositionMonitoringHealth,
)

NOW = datetime(2026, 9, 6, 12, 0, tzinfo=UTC)


def _action(
    *,
    action_type: str,
    resource_id=None,
    occurred_at: datetime = NOW,
) -> OperationalAction:
    resource_id = resource_id or uuid4()
    return OperationalAction(
        id=f"{action_type}:{resource_id}",
        source_feature="test",
        action_type=action_type,
        priority="ACTION",
        state="ACTIONABLE",
        title=action_type,
        detail="detail",
        resource_type="trade" if action_type == "OPEN_POSITION_MANAGEMENT" else "other",
        resource_id=resource_id,
        next_action="open",
        target="/target",
        occurred_at=occurred_at,
    )


@pytest.mark.asyncio
async def test_prioritizes_open_alert_then_unhealthy_position_then_other_actions() -> None:
    trade_id = uuid4()
    actions = (
        _action(action_type="INITIAL_PURCHASE"),
        _action(action_type="OPEN_POSITION_MANAGEMENT", resource_id=trade_id),
        _action(action_type="POSITION_ALERT"),
    )

    async def health_reader(requested_trade_id):
        assert requested_trade_id == trade_id
        return PositionMonitoringHealth(
            trade_id=trade_id,
            position_id=uuid4(),
            status=MonitoringHealthStatus.STALE,
            reason="COMPLETED_DAILY_PRICE_STALE",
            symbol="DAX.INDX",
            market_data_observed_at=NOW,
            age_days=5,
        )

    result = await prioritize_position_monitoring(actions, health_reader=health_reader)

    assert [item.action_type for item in result] == [
        "POSITION_ALERT",
        "POSITION_DATA_HEALTH",
        "INITIAL_PURCHASE",
    ]
    health_action = result[1]
    assert health_action.resource_id == trade_id
    assert health_action.title == "Monitoring-Daten veraltet"
    assert "kein Stop-/Target-Alert" in health_action.detail
    assert health_action.target == "/target"


@pytest.mark.asyncio
async def test_keeps_healthy_open_position_as_normal_management_action() -> None:
    trade_id = uuid4()
    action = _action(action_type="OPEN_POSITION_MANAGEMENT", resource_id=trade_id)

    async def health_reader(_trade_id):
        return PositionMonitoringHealth(
            trade_id=trade_id,
            position_id=uuid4(),
            status=MonitoringHealthStatus.OK,
            reason="COMPLETED_DAILY_PRICE_CURRENT",
        )

    result = await prioritize_position_monitoring((action,), health_reader=health_reader)

    assert result == (action,)


@pytest.mark.asyncio
async def test_maps_missing_and_error_health_without_creating_alert_actions() -> None:
    for status, expected_title in (
        (MonitoringHealthStatus.MISSING, "Monitoring-Daten fehlen"),
        (MonitoringHealthStatus.ERROR, "Monitoring-Daten prüfen"),
    ):
        trade_id = uuid4()
        action = _action(action_type="OPEN_POSITION_MANAGEMENT", resource_id=trade_id)

        async def health_reader(
            _trade_id,
            current_status=status,
            current_trade_id=trade_id,
        ):
            return PositionMonitoringHealth(
                trade_id=current_trade_id,
                position_id=uuid4(),
                status=current_status,
                reason="TEST",
            )

        result = await prioritize_position_monitoring((action,), health_reader=health_reader)

        assert result[0].action_type == "POSITION_DATA_HEALTH"
        assert result[0].title == expected_title
        assert result[0].source_feature == "Position Monitoring / Data Health"
