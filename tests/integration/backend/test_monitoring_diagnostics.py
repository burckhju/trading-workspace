from dataclasses import replace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from tests.unit.backend.features.position_monitoring.test_health import (
    LISTING_ID,
    NOW,
    UNDERLYING_ID,
    _daily_result,
)
from tests.unit.backend.features.position_monitoring.test_runner import Runtime

import app.main as main_module
from app.core.config import Settings
from app.core.di import ApplicationContainer
from app.features.position_monitoring.service.health import (
    MonitoringBasis,
    MonitoringHealthStatus,
    PositionMonitoringHealth,
)


@pytest.mark.parametrize("enabled", [False, True])
def test_runtime_status_observes_real_lifespan_without_triggering_a_cycle(monkeypatch, enabled):
    runtime = Runtime()
    monkeypatch.setattr(main_module, "build_position_monitoring_runtime", lambda **_: runtime)
    monkeypatch.setattr(ApplicationContainer, "require_eodhd_adapter", lambda _: object())
    settings = Settings(
        _env_file=None,
        environment="test",
        log_level="CRITICAL",
        position_monitoring={"enabled": enabled, "interval_seconds": 3600},
    )
    application = main_module.create_application(settings)
    with TestClient(application) as client:
        response = client.get("/api/v1/position-monitoring/runtime/status")
        assert response.status_code == 200
        value = response.json()
        assert value["enabled"] is enabled
        assert value["running"] is enabled
        assert value["scope"] == "PROCESS_LOCAL_ALL_WORKSPACES"
        assert (value["last_result"] is not None) is enabled
        before = runtime.calls
        assert client.get("/api/v1/position-monitoring/runtime/status").json() == value
        assert runtime.calls == before
        if enabled:
            assert value["last_result"]["subject_errors"] == 0
            assert value["last_cycle_completed_at"] is not None
    if enabled:
        assert application.state.position_monitoring_runner.status()["running"] is False


def test_health_contract_serializes_basis_and_exact_prices_without_mutation(monkeypatch):
    from importlib import import_module

    router_module = import_module("app.features.position_monitoring.api.router")
    trade_id = uuid4()
    price = replace(_daily_result(trading_date=NOW.date()).data, provider_symbol="APC")
    health = PositionMonitoringHealth(
        trade_id,
        uuid4(),
        MonitoringHealthStatus.OK,
        "COMPLETED_DAILY_PRICE_CURRENT",
        basis=MonitoringBasis(
            UNDERLYING_ID, "Example basis", "US0378331005", LISTING_ID, "XFRA", "EUR"
        ),
        daily_price=price,
    )
    service = AsyncMock()
    service.for_trade.return_value = health
    monkeypatch.setattr(router_module, "_health_service", lambda _: service)
    with TestClient(
        main_module.create_application(Settings(_env_file=None, environment="test"))
    ) as client:
        response = client.get(f"/api/v1/position-monitoring/trades/{trade_id}/health")
    assert response.status_code == 200
    body = response.json()
    assert body["basis"]["listing_id"] == str(LISTING_ID)
    assert body["basis"]["venue_mic"] == "XFRA"
    assert body["daily_price"]["close"] == "24100"
    assert body["daily_price"]["retrieved_at"] == "2026-09-06T12:00:00Z"
    assert body["daily_price"]["provider_symbol"] == "APC"
    service.for_trade.assert_awaited_once_with(trade_id)
