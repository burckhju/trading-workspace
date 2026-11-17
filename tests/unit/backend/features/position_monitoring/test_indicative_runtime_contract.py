"""Central scope, passive operations read and separate external delivery permission."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError
from tests.unit.backend.features.notification.test_hebeltrader_b04 import executions
from tests.unit.backend.features.notification.test_position_review_alerts import (
    REVIEW_TYPES,
    delivery_fixture,
)

from app.core.config import Settings
from app.features.notification.domain.models import DeliveryStatus
from app.features.position_monitoring.api.router import get_monitoring_runtime_status
from app.features.trade_position.persistence.repositories import SqlAlchemyExecutionRecordRepository


def test_review_activation_is_central_and_does_not_activate_confirmed_baseline():
    defaults = Settings(environment="test")
    assert defaults.position_monitoring.review_scope == "DISABLED"
    assert not defaults.position_monitoring.review_notifications_enabled
    configured = Settings(
        environment="test",
        position_monitoring={"enabled": True, "review_scope": "INDICATIVE_ENTRY_V1"},
    )
    assert configured.position_monitoring.hebeltrader_scope == "DISABLED"
    assert not configured.position_monitoring.review_notifications_enabled
    with pytest.raises(ValidationError):
        Settings(position_monitoring={"review_scope": "HEBELTRADER_CONFIRMED_BASELINE"})


async def test_status_read_reports_configuration_without_inventing_a_completed_cycle():
    settings = Settings(
        environment="test",
        position_monitoring={"enabled": True, "review_scope": "INDICATIVE_ENTRY_V1"},
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    # No database, evaluator or acquisition port exists in this read container.
    result = await get_monitoring_runtime_status(request, SimpleNamespace(settings=settings))
    assert result.review_scope == "INDICATIVE_ENTRY_V1"
    assert result.review_rule_version == "indicative-entry-review-v1"
    assert result.hebeltrader_scope == "DISABLED"
    assert result.enabled and not result.running
    assert result.last_cycle_completed_at is None and result.last_result is None
    assert not result.review_notifications_enabled


@pytest.mark.parametrize("kind", REVIEW_TYPES)
async def test_external_review_pause_preserves_pending_notice_without_delivery(monkeypatch, kind):
    fixture = delivery_fixture(kind)
    fixture.store._review_delivery_enabled = False
    fixture.session.scalar.side_effect = [
        fixture.trade.id,
        fixture.trade,
        fixture.notification,
        fixture.alert,
    ]
    monkeypatch.setattr(
        SqlAlchemyExecutionRecordRepository,
        "list_effective_for_trade",
        AsyncMock(return_value=executions(fixture.trade, sold=5)),
    )
    result = await fixture.delivery.deliver(fixture.notification.id)
    assert result.status is DeliveryStatus.FAILED
    assert result.error_code == "REVIEW_DELIVERY_DISABLED"
    assert fixture.notification.status == "PENDING"
    fixture.adapter.deliver.assert_not_awaited()
    fixture.session.add.assert_not_called()


@pytest.mark.parametrize("kind", REVIEW_TYPES)
async def test_full_sale_still_terminates_notice_when_external_review_delivery_paused(
    monkeypatch, kind
):
    fixture = delivery_fixture(kind)
    fixture.store._review_delivery_enabled = False
    fixture.session.scalar.side_effect = [
        fixture.trade.id,
        fixture.trade,
        fixture.notification,
        fixture.alert,
        None,
    ]
    monkeypatch.setattr(
        SqlAlchemyExecutionRecordRepository,
        "list_effective_for_trade",
        AsyncMock(return_value=executions(fixture.trade)),
    )
    result = await fixture.delivery.deliver(fixture.notification.id)
    assert result.error_code == "REVIEW_POSITION_CLOSED" and not result.retryable
    assert fixture.notification.status == "FAILED"
    fixture.adapter.deliver.assert_not_awaited()
