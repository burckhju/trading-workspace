"""Central scope, passive operations read and separate external delivery permission."""

from contextlib import asynccontextmanager
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session
from tests.unit.backend.features.market_data.test_retained_quotes import SqlDatabase
from tests.unit.backend.features.notification.test_hebeltrader_b04 import NOW, executions
from tests.unit.backend.features.notification.test_position_review_alerts import (
    REVIEW_TYPES,
    delivery_fixture,
)
from tests.unit.backend.features.position_monitoring.test_runner import Runtime

from app.core.config import Settings
from app.features.alert.persistence.models import AlertModel
from app.features.notification.domain.models import DeliveryResult, DeliveryStatus
from app.features.notification.persistence.durable_delivery import (
    SqlAlchemyDurableNotificationDeliveryStore,
)
from app.features.notification.persistence.models import NotificationModel
from app.features.position_monitoring.api.router import get_monitoring_runtime_status
from app.features.position_monitoring.service import runtime as runtime_module
from app.features.position_monitoring.service.indicative_entry_runtime import IndicativeEntryRuntime
from app.features.trade_position.persistence.repositories import SqlAlchemyExecutionRecordRepository


@pytest.mark.parametrize("scope", ["INDICATIVE_ENTRY_V1", "INDICATIVE_ENTRY_V2"])
def test_review_activation_is_central_and_does_not_activate_confirmed_baseline(scope):
    defaults = Settings(environment="test")
    assert defaults.position_monitoring.review_scope == "DISABLED"
    assert not defaults.position_monitoring.review_notifications_enabled
    configured = Settings(
        environment="test",
        position_monitoring={"enabled": True, "review_scope": scope},
    )
    assert configured.position_monitoring.hebeltrader_scope == "DISABLED"
    assert not configured.position_monitoring.review_notifications_enabled
    with pytest.raises(ValidationError):
        Settings(position_monitoring={"review_scope": "HEBELTRADER_CONFIRMED_BASELINE"})


@pytest.mark.parametrize("version", ["v1", "v2"])
async def test_status_read_reports_configuration_without_inventing_a_completed_cycle(version):
    scope = f"INDICATIVE_ENTRY_{version.upper()}"
    settings = Settings(
        environment="test",
        position_monitoring={"enabled": True, "review_scope": scope},
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
    # No database, evaluator or acquisition port exists in this read container.
    result = await get_monitoring_runtime_status(request, SimpleNamespace(settings=settings))
    assert result.review_scope == scope
    assert result.review_rule_version == f"indicative-entry-review-{version}"
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


async def test_cleanup_pages_past_paused_notices_with_fixed_cutoff_and_preserves_other_types(
    tmp_path, monkeypatch
):
    database = SqlDatabase(f"sqlite:///{tmp_path}/synthetic_review_cleanup_only.db")
    try:
        for model in (AlertModel, NotificationModel):
            model.__table__.create(database.engine)
        with Session(database.engine) as session:
            for index, kind in enumerate(
                (
                    "POSITION_REVIEW_DUE",
                    "POSITION_DATA_UNAVAILABLE",
                    "POSITION_REVIEW_DUE",
                    "HEBELTRADER_B04_LOSS",
                    "POSITION_REVIEW_DUE",
                    "STOP_REACHED",
                ),
                start=1,
            ):
                alert_id = uuid4()
                priced = kind in {"HEBELTRADER_B04_LOSS", "STOP_REACHED"}
                session.add(
                    AlertModel(
                        id=alert_id,
                        position_id=uuid4(),
                        trade_id=uuid4(),
                        alert_type=kind,
                        severity="WARNING",
                        rule_key="synthetic-cleanup-only",
                        reason="Synthetic terminal cleanup qualification",
                        observed_value=Decimal("1") if priced else None,
                        threshold_value=Decimal("2") if priced else None,
                        detected_at=NOW,
                        status="OPEN",
                    )
                )
                session.add(
                    NotificationModel(
                        id=UUID(int=index),
                        alert_id=alert_id,
                        channel="TELEGRAM",
                        destination_key="synthetic-no-dispatch",
                        body="Synthetic cleanup only",
                        created_at=NOW + timedelta(seconds=1) if index == 5 else NOW,
                        status="PENDING",
                    )
                )
            session.commit()
        store = SqlAlchemyDurableNotificationDeliveryStore(database, review_delivery_enabled=False)
        visited = []

        async def prepare(**kwargs):
            identifier = kwargs["notification_id"]
            visited.append(identifier)
            assert kwargs["now"] == NOW
            closed = identifier == UUID(int=3)
            if closed:
                with Session(database.engine) as session:
                    session.get(NotificationModel, identifier).status = "FAILED"
                    session.commit()
            return SimpleNamespace(
                attempt=None,
                terminal_result=DeliveryResult(
                    status=DeliveryStatus.FAILED,
                    retryable=not closed,
                    error_code="REVIEW_POSITION_CLOSED" if closed else "REVIEW_DELIVERY_DISABLED",
                ),
            )

        monkeypatch.setattr(store, "prepare", prepare)
        assert await store.suppress_terminal_review_notifications(now=NOW, page_size=1) == 1
        assert visited == [UUID(int=index) for index in (1, 2, 3)]
        visited.clear()
        assert await store.suppress_terminal_review_notifications(now=NOW, page_size=1) == 0
        assert visited == [UUID(int=index) for index in (1, 2)]
        with Session(database.engine) as session:
            for index in (1, 2, 4, 5, 6):
                assert session.get(NotificationModel, UUID(int=index)).status == "PENDING"
    finally:
        database.engine.dispose()


@pytest.mark.parametrize("fails", [False, True])
async def test_general_cycle_runs_terminal_cleanup_without_scope_or_delivery_adapter(
    monkeypatch, fails
):
    session = SimpleNamespace()

    @asynccontextmanager
    async def session_context():
        yield session

    database = SimpleNamespace(session_context=session_context)
    cleanup = AsyncMock(side_effect=RuntimeError("synthetic cleanup failure") if fails else None)

    def store(selected_database, *, review_delivery_enabled):
        assert selected_database is database and review_delivery_enabled is False
        return SimpleNamespace(suppress_terminal_review_notifications=cleanup)

    monkeypatch.setattr(runtime_module, "SqlAlchemyDurableNotificationDeliveryStore", store)
    monkeypatch.setattr(runtime_module, "invalidate_unbound_alerts", AsyncMock(return_value=0))
    runtime = runtime_module.PositionMonitoringRuntimeService(
        database=database,
        market_data=None,
        delivery_adapter=None,
        indicative_entry=IndicativeEntryRuntime(database, scope="DISABLED"),
    )
    empty_cycle = (await Runtime().run()).cycle
    cycle = AsyncMock(return_value=empty_cycle)
    monkeypatch.setattr(runtime, "_run_monitoring_cycle", cycle)
    if fails:
        with pytest.raises(RuntimeError, match="synthetic cleanup failure"):
            await runtime.run()
        cycle.assert_not_awaited()
    else:
        result = await runtime.run()
        assert result.notification_failures == result.notifications_delivered == 0
        assert result.indicative_entry.positions_evaluated == 0
        cycle.assert_awaited_once()
    cleanup.assert_awaited_once()


@pytest.mark.parametrize(
    "enabled,at,page_size",
    [(True, NOW, 1), (False, NOW, 0), (False, NOW.replace(tzinfo=None), 1)],
)
async def test_terminal_cleanup_refuses_unbounded_or_delivery_enabled_operation(
    enabled, at, page_size
):
    store = SqlAlchemyDurableNotificationDeliveryStore(
        SimpleNamespace(), review_delivery_enabled=enabled
    )
    with pytest.raises(ValueError, match="Review cleanup requires"):
        await store.suppress_terminal_review_notifications(now=at, page_size=page_size)
