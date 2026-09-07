from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.features.operational_workspace.service.prioritization import prioritize_position_monitoring
from app.features.operational_workspace.service.read_model import OperationalAction
from app.features.position_monitoring.service.health import (
    MonitoringHealthStatus,
    PositionMonitoringHealth,
)
from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuation,
    ProductValuationStatus,
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


def _health(trade_id, status: MonitoringHealthStatus) -> PositionMonitoringHealth:
    return PositionMonitoringHealth(
        trade_id=trade_id,
        position_id=uuid4(),
        status=status,
        reason="TEST",
        symbol="DAX.INDX",
        market_data_observed_at=NOW,
        age_days=5 if status is MonitoringHealthStatus.STALE else None,
    )


def _valuation(
    trade_id,
    status: ProductValuationStatus,
) -> ProductPositionValuation:
    return ProductPositionValuation(
        trade_id=trade_id,
        position_id=uuid4(),
        status=status,
        reason="TEST",
        symbol="TEST12.STU",
        quote_observed_at=NOW,
        quote_age_seconds=7200 if status is ProductValuationStatus.STALE else 60,
        max_quote_age_seconds=3600,
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
        return _health(trade_id, MonitoringHealthStatus.STALE)

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
async def test_keeps_position_normal_when_underlying_and_product_data_are_healthy() -> None:
    trade_id = uuid4()
    action = _action(action_type="OPEN_POSITION_MANAGEMENT", resource_id=trade_id)

    async def health_reader(_trade_id):
        return _health(trade_id, MonitoringHealthStatus.OK)

    async def valuation_reader(_trade_id):
        return _valuation(trade_id, ProductValuationStatus.AVAILABLE)

    result = await prioritize_position_monitoring(
        (action,),
        health_reader=health_reader,
        valuation_reader=valuation_reader,
    )

    assert result == (action,)


@pytest.mark.asyncio
async def test_surfaces_stale_product_quote_without_creating_trading_alert() -> None:
    trade_id = uuid4()
    action = _action(action_type="OPEN_POSITION_MANAGEMENT", resource_id=trade_id)

    async def health_reader(_trade_id):
        return _health(trade_id, MonitoringHealthStatus.OK)

    async def valuation_reader(_trade_id):
        return _valuation(trade_id, ProductValuationStatus.STALE)

    result = await prioritize_position_monitoring(
        (action,),
        health_reader=health_reader,
        valuation_reader=valuation_reader,
    )

    assert result[0].action_type == "POSITION_DATA_HEALTH"
    assert result[0].title == "Produktkurs veraltet"
    assert result[0].source_feature == "Position Monitoring / Product Data Health"
    assert "kein aktueller Marktwert" in result[0].detail
    assert "unrealized P&L" in result[0].detail
    assert result[0].target == "/target"


@pytest.mark.asyncio
async def test_combines_underlying_and_product_data_problems_without_mixing_semantics() -> None:
    trade_id = uuid4()
    action = _action(action_type="OPEN_POSITION_MANAGEMENT", resource_id=trade_id)

    async def health_reader(_trade_id):
        return _health(trade_id, MonitoringHealthStatus.STALE)

    async def valuation_reader(_trade_id):
        return _valuation(trade_id, ProductValuationStatus.MISSING)

    result = await prioritize_position_monitoring(
        (action,),
        health_reader=health_reader,
        valuation_reader=valuation_reader,
    )

    assert result[0].action_type == "POSITION_DATA_HEALTH"
    assert result[0].title == "Positionsdaten prüfen"
    assert "Underlying-Monitoring:" in result[0].detail
    assert "Stop-/Target-Alert" in result[0].detail
    assert "Produktbewertung:" in result[0].detail
    assert "Marktwert und unrealized P&L" in result[0].detail


@pytest.mark.asyncio
async def test_maps_product_missing_unavailable_and_error_to_data_health() -> None:
    for status, expected_title in (
        (ProductValuationStatus.MISSING, "Produktkurs fehlt"),
        (ProductValuationStatus.UNAVAILABLE, "Produktbewertung nicht verfügbar"),
        (ProductValuationStatus.ERROR, "Produktbewertung prüfen"),
    ):
        trade_id = uuid4()
        action = _action(action_type="OPEN_POSITION_MANAGEMENT", resource_id=trade_id)

        async def health_reader(_trade_id, current_trade_id=trade_id):
            return _health(current_trade_id, MonitoringHealthStatus.OK)

        async def valuation_reader(
            _trade_id,
            current_status=status,
            current_trade_id=trade_id,
        ):
            return _valuation(current_trade_id, current_status)

        result = await prioritize_position_monitoring(
            (action,),
            health_reader=health_reader,
            valuation_reader=valuation_reader,
        )

        assert result[0].action_type == "POSITION_DATA_HEALTH"
        assert result[0].title == expected_title
        assert result[0].source_feature == "Position Monitoring / Product Data Health"


@pytest.mark.asyncio
async def test_maps_missing_and_error_underlying_health_without_creating_alert_actions() -> None:
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
            return _health(current_trade_id, current_status)

        result = await prioritize_position_monitoring((action,), health_reader=health_reader)

        assert result[0].action_type == "POSITION_DATA_HEALTH"
        assert result[0].title == expected_title
        assert result[0].source_feature == "Position Monitoring / Data Health"


@pytest.mark.asyncio
async def test_existing_position_alert_is_not_reclassified_by_data_health_readers() -> None:
    alert = _action(action_type="POSITION_ALERT")
    calls = 0

    async def health_reader(_trade_id):
        nonlocal calls
        calls += 1
        return None

    async def valuation_reader(_trade_id):
        nonlocal calls
        calls += 1
        return None

    result = await prioritize_position_monitoring(
        (alert,),
        health_reader=health_reader,
        valuation_reader=valuation_reader,
    )

    assert result == (alert,)
    assert calls == 0
