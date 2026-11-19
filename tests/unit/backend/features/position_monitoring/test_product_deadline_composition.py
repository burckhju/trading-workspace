"""Central V2 composition and independent price-free deadline runner results."""

from contextlib import asynccontextmanager
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from tests.unit.backend.features.position_monitoring.test_runner import Runtime

from app.core.config import Settings
from app.features.notification.domain.models import DeliveryResult, DeliveryStatus
from app.features.position_monitoring import bootstrap
from app.features.position_monitoring.service import runtime as runtime_module
from app.features.position_monitoring.service.hebeltrader_loss_runtime import LossRunResult
from app.features.position_monitoring.service.indicative_entry_runtime import IndicativeRunResult
from app.features.position_monitoring.service.product_deadline_review_runtime import (
    ProductDeadlineRunResult,
)
from app.features.position_monitoring.service.runner import PositionMonitoringRunner


@pytest.fixture(autouse=True)
def no_external_http(monkeypatch):
    asynchronous = AsyncMock(side_effect=AssertionError("Synthetic composition cannot call HTTP"))
    synchronous = Mock(side_effect=AssertionError("Synthetic composition cannot call HTTP"))
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", asynchronous)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", synchronous)
    yield
    asynchronous.assert_not_awaited()
    synchronous.assert_not_called()


@pytest.mark.parametrize("scope", ["DISABLED", "INDICATIVE_ENTRY_V1", "INDICATIVE_ENTRY_V2"])
@pytest.mark.parametrize("authorized", [False, True])
@pytest.mark.parametrize("adapter_configured", [False, True])
def test_bootstrap_enables_deadline_creation_and_delivery_only_through_central_v2_scope(
    scope, authorized, adapter_configured
):
    settings = Settings(
        environment="test",
        position_monitoring={
            "review_scope": scope,
            "review_notifications_enabled": authorized,
        },
        notification={
            "telegram": {
                "enabled": adapter_configured,
                "bot_token": "synthetic-not-a-token",
                "chat_id": "synthetic-no-external-delivery",
                "base_url": "https://example.invalid",
            }
        },
    )
    database = SimpleNamespace(
        session_context=Mock(side_effect=AssertionError("No application run"))
    )
    runtime = bootstrap.build_position_monitoring_runtime(
        settings=settings, database=database, market_data=None, products=None
    )
    assert runtime._product_deadline._scope == scope
    assert runtime._deadline_notifications_enabled is (
        authorized and scope == "INDICATIVE_ENTRY_V2"
    )
    assert runtime._product_deadline._notifications_enabled is (
        authorized and scope == "INDICATIVE_ENTRY_V2" and adapter_configured
    )
    assert runtime._review_notifications_enabled is (authorized and scope != "DISABLED")
    assert (runtime._delivery_adapter is not None) is adapter_configured
    assert runtime._hebeltrader_loss._scope == "DISABLED"
    database.session_context.assert_not_called()


def composed_fixture(monkeypatch, *, delivery):
    @asynccontextmanager
    async def session_context():
        yield SimpleNamespace()

    database = SimpleNamespace(session_context=session_context)
    cleanup = AsyncMock(return_value=0)
    stores = []

    def store(selected_database, *, review_delivery_enabled, deadline_delivery_enabled=False):
        assert selected_database is database
        stores.append((review_delivery_enabled, deadline_delivery_enabled))
        return SimpleNamespace(suppress_terminal_review_notifications=cleanup)

    monkeypatch.setattr(runtime_module, "SqlAlchemyDurableNotificationDeliveryStore", store)
    monkeypatch.setattr(runtime_module, "invalidate_unbound_alerts", AsyncMock(return_value=0))
    indicative = SimpleNamespace(
        run=AsyncMock(
            return_value=IndicativeRunResult(
                positions_evaluated=6,
                alerts_created=2,
                data_problems=6,
                notifications_created=2 if delivery else 0,
            )
        )
    )
    deadlines = SimpleNamespace(
        run=AsyncMock(
            return_value=ProductDeadlineRunResult(
                positions_evaluated=4,
                alerts_created=3,
                data_problems=1,
                notifications_created=3 if delivery else 0,
            )
        )
    )
    loss = SimpleNamespace(
        run=AsyncMock(
            return_value=LossRunResult(
                positions_evaluated=1,
                notifications_created=1 if delivery else 0,
            )
        )
    )
    runtime = runtime_module.PositionMonitoringRuntimeService(
        database=database,
        market_data=None,
        products=None,
        delivery_adapter=SimpleNamespace(deliver=AsyncMock()) if delivery else None,
        hebeltrader_loss=loss,
        indicative_entry=indicative,
        product_deadline=deadlines,
        review_notifications_enabled=delivery,
        deadline_notifications_enabled=delivery,
    )
    return SimpleNamespace(
        runtime=runtime,
        indicative=indicative,
        deadlines=deadlines,
        loss=loss,
        cleanup=cleanup,
        stores=stores,
    )


@pytest.mark.parametrize("delivery", [False, True])
async def test_deadline_sweep_runs_with_no_price_provider_and_indicative_data_problems(
    monkeypatch, delivery
):
    fixture = composed_fixture(monkeypatch, delivery=delivery)
    baseline = await Runtime().run()
    cycle = replace(baseline.cycle, positions_seen=6, missing_market_data=6)
    monkeypatch.setattr(fixture.runtime, "_run_monitoring_cycle", AsyncMock(return_value=cycle))
    deliver_pending = AsyncMock(
        return_value=(
            DeliveryResult(status=DeliveryStatus.DELIVERED, retryable=False),
            DeliveryResult(status=DeliveryStatus.FAILED, retryable=True),
        )
    )
    delivery_service = Mock(return_value=SimpleNamespace(deliver_pending=deliver_pending))
    monkeypatch.setattr(runtime_module, "DurableNotificationDeliveryService", delivery_service)
    result = await fixture.runtime.run()
    fixture.cleanup.assert_awaited_once()
    fixture.indicative.run.assert_awaited_once()
    fixture.deadlines.run.assert_awaited_once()
    assert result.cycle.missing_market_data == 6
    assert result.indicative_entry.positions_evaluated == 6
    assert result.indicative_entry.data_problems == 6
    assert result.product_deadline.positions_evaluated == 4
    assert result.product_deadline.alerts_created == 3
    assert result.product_deadline.data_problems == 1
    assert result.notifications_created == (6 if delivery else 0)
    assert result.notifications_delivered == result.notification_failures == int(delivery)
    assert fixture.stores[0] == (False, False)
    if delivery:
        assert fixture.stores[1:] == [(True, True)]
        deliver_pending.assert_awaited_once()
        fixture.runtime._delivery_adapter.deliver.assert_not_awaited()
    else:
        delivery_service.assert_not_called()


async def test_runner_reports_each_rule_family_without_combining_or_rewriting_counts():
    baseline = await Runtime().run()
    result = replace(
        baseline,
        cycle=replace(baseline.cycle, positions_seen=9, alerts_created=5, missing_market_data=8),
        indicative_entry=IndicativeRunResult(
            positions_evaluated=6,
            alerts_created=2,
            data_problems=6,
            position_errors=1,
        ),
        product_deadline=ProductDeadlineRunResult(
            positions_evaluated=4,
            alerts_created=3,
            data_problems=1,
            position_errors=2,
        ),
    )
    runtime = SimpleNamespace(run=AsyncMock())
    runner = PositionMonitoringRunner(runtime=runtime, interval_seconds=3600)

    async def once():
        runner.stop()
        return result

    runtime.run.side_effect = once
    assert runner.status()["last_result"] is None
    await runner.run_forever()
    snapshot = runner.status()
    expected = {
        "positions_seen": 9,
        "alerts_created": 5,
        "missing_market_data": 8,
        "review_positions_evaluated": 6,
        "review_alerts_created": 2,
        "review_data_problems": 6,
        "review_position_errors": 1,
        "deadline_positions_evaluated": 4,
        "deadline_alerts_created": 3,
        "deadline_data_problems": 1,
        "deadline_position_errors": 2,
    }
    for key, value in expected.items():
        assert snapshot["last_result"][key] == value
    assert snapshot["last_cycle_completed_at"] is not None
    assert not snapshot["running"] and not snapshot["cycle_running"]
    assert runner.status() == snapshot
    runtime.run.assert_awaited_once()
