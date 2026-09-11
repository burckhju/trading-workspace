"""Focused regression coverage for local backend quality-gate infrastructure."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.features.alert.domain.models import Alert, AlertSeverity, AlertStatus, AlertType
from app.features.alert.persistence.repositories import SqlAlchemyAlertRepository
from app.features.position_monitoring.domain.models import MonitoringRuleState
from app.features.position_monitoring.persistence.repositories import (
    SqlAlchemyMonitoringRuleStateRepository,
)
from app.features.position_monitoring.service.processor import (
    SqlAlchemyMonitoringRuleProcessor,
)
from app.features.user_preferences.service.application import UserPreferenceService


def _now() -> datetime:
    return datetime(2026, 9, 11, 12, 0, tzinfo=UTC)


async def test_user_preference_service_covers_list_create_and_delete() -> None:
    workspace_id = uuid4()
    preference_id = uuid4()
    listed = SimpleNamespace(id=preference_id)
    scalar_result = MagicMock()
    scalar_result.all.return_value = [listed]

    session = MagicMock()
    session.scalars = AsyncMock(return_value=scalar_result)
    session.scalar = AsyncMock(side_effect=[preference_id, None])
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    service = UserPreferenceService(session)

    assert await service.list(workspace_id, "actor", "TABLE") == (listed,)

    created = await service.create(
        workspace_id,
        "actor",
        "TABLE",
        "  compact-view  ",
        {"columns": ["symbol", "pnl"]},
    )
    assert created.workspace_id == workspace_id
    assert created.actor_id == "actor"
    assert created.kind == "TABLE"
    assert created.name == "compact-view"
    session.add.assert_called_once_with(created)
    session.refresh.assert_awaited_once_with(created)

    assert await service.delete(workspace_id, "actor", preference_id) is True
    assert await service.delete(workspace_id, "actor", uuid4()) is False
    assert session.commit.await_count == 3


async def test_alert_repository_maps_add_get_resolve_and_missing() -> None:
    now = _now()
    alert = Alert(
        id=uuid4(),
        position_id=uuid4(),
        trade_id=uuid4(),
        alert_type=AlertType.STOP_REACHED,
        severity=AlertSeverity.WARNING,
        rule_key="stop",
        reason="stop reached",
        observed_value=Decimal("9.50"),
        threshold_value=Decimal("10.00"),
        market_data_observed_at=now,
        detected_at=now,
    )
    model = SimpleNamespace(
        id=alert.id,
        position_id=alert.position_id,
        trade_id=alert.trade_id,
        alert_type=alert.alert_type.value,
        severity=alert.severity.value,
        rule_key=alert.rule_key,
        reason=alert.reason,
        observed_value=alert.observed_value,
        threshold_value=alert.threshold_value,
        market_data_observed_at=alert.market_data_observed_at,
        detected_at=alert.detected_at,
        status=AlertStatus.OPEN.value,
        resolved_at=None,
    )

    session = MagicMock()
    session.scalar = AsyncMock(side_effect=[None, model, None, model])
    repository = SqlAlchemyAlertRepository(session)

    await repository.add(alert)
    added = session.add.call_args.args[0]
    assert added.id == alert.id
    assert added.rule_key == "stop"

    assert await repository.get(uuid4()) is None
    assert await repository.get(alert.id) == alert

    with pytest.raises(LookupError, match="alert not found"):
        await repository.resolve(uuid4(), resolved_at=now)

    await repository.resolve(alert.id, resolved_at=now)
    assert model.status == AlertStatus.RESOLVED.value
    assert model.resolved_at == now


async def test_monitoring_rule_state_repository_covers_insert_update_and_read() -> None:
    now = _now()
    position_id = uuid4()
    active_alert_id = uuid4()
    state = MonitoringRuleState(
        position_id=position_id,
        rule_key="target",
        triggered=True,
        first_seen_at=now,
        last_seen_at=now,
        last_observed_value=Decimal("12.5"),
        threshold_value=Decimal("12.0"),
        active_alert_id=active_alert_id,
    )
    existing = SimpleNamespace(
        position_id=position_id,
        rule_key="target",
        triggered=False,
        first_seen_at=None,
        last_seen_at=now,
        last_observed_value=Decimal("11.0"),
        threshold_value=Decimal("12.0"),
        active_alert_id=None,
    )

    session = MagicMock()
    session.scalar = AsyncMock(side_effect=[None, None, existing, existing])
    repository = SqlAlchemyMonitoringRuleStateRepository(session)

    assert await repository.get(position_id=position_id, rule_key="target") is None

    await repository.put(state)
    inserted = session.add.call_args.args[0]
    assert inserted.position_id == position_id
    assert inserted.triggered is True

    loaded = await repository.get(position_id=position_id, rule_key="target")
    assert loaded == MonitoringRuleState(
        position_id=position_id,
        rule_key="target",
        triggered=False,
        first_seen_at=None,
        last_seen_at=now,
        last_observed_value=Decimal("11.0"),
        threshold_value=Decimal("12.0"),
        active_alert_id=None,
    )

    await repository.put(state)
    assert existing.triggered is True
    assert existing.first_seen_at == now
    assert existing.last_observed_value == Decimal("12.5")
    assert existing.active_alert_id == active_alert_id


async def test_monitoring_rule_processor_commits_success_and_rolls_back_failure() -> None:
    session = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    processor = SqlAlchemyMonitoringRuleProcessor(session)

    expected = object()
    processor._service = SimpleNamespace(evaluate=AsyncMock(return_value=expected))
    kwargs = {
        "position_id": uuid4(),
        "trade_id": uuid4(),
        "rule": MagicMock(),
        "observation": MagicMock(),
    }

    assert await processor.process(**kwargs) is expected
    session.commit.assert_awaited_once_with()
    session.rollback.assert_not_awaited()

    processor._service.evaluate = AsyncMock(side_effect=RuntimeError("boom"))
    with pytest.raises(RuntimeError, match="boom"):
        await processor.process(**kwargs)
    session.rollback.assert_awaited_once_with()
