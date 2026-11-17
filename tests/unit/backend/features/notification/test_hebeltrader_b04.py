"""B04 messages and terminal outbox decisions; no database or external send."""

from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from tests.unit.backend.features.notification.test_warrant_name import (
    ISIN,
    NAME,
    WKN,
    alert,
)

from app.features.alert.domain.models import AlertType
from app.features.alert.persistence.models import AlertModel
from app.features.notification.domain.models import DeliveryResult, DeliveryStatus
from app.features.notification.persistence.durable_delivery import (
    SqlAlchemyDurableNotificationDeliveryStore,
)
from app.features.notification.persistence.models import (
    NotificationDeliveryAttemptModel,
    NotificationModel,
)
from app.features.notification.service.durable_delivery import (
    DurableNotificationDeliveryService,
)
from app.features.notification.service.formatter import format_position_alert
from app.features.notification.service.hebeltrader_lifecycle import (
    suppress_pending_b04_notifications,
)
from app.features.trade_position.domain.enums import ExecutionSide
from app.features.trade_position.domain.models import ExecutionRecord
from app.features.trade_position.persistence.models import TradeModel
from app.features.trade_position.persistence.repositories import (
    SqlAlchemyExecutionRecordRepository,
)

NOW = datetime(2026, 11, 17, 12, tzinfo=UTC)


def test_b04_formatter_preserves_qualified_scope_quantity_and_reason():
    item = replace(
        alert(AlertType.HEBELTRADER_B04_LOSS),
        observed_value=Decimal("0.48"),
        threshold_value=Decimal("0.55"),
        reason="Original-Geldkurs liegt unter dem persönlichen Bruttoeinstand.",
        price_context={
            "basis": "WARRANT",
            "currency": "EUR",
            "provider": "SYNTHETIC",
            "observed_at": NOW.isoformat(),
            "rule_version": "hebeltrader-b04-b57-v1",
            "remaining_quantity": "2300",
            "completed_sessions_at_bid": "20",
        },
    )
    body = format_position_alert(
        item, symbol=ISIN, warrant_name=NAME, warrant_isin=ISIN, warrant_wkn=WKN
    )
    for expected in (
        NAME,
        WKN,
        ISIN,
        "Hebeltrader · Verlust nach 20 Basiswertsitzungen",
        "Original-Geldkurs: 0.48 EUR",
        "Persönlicher Bruttoeinstand je Stück: 0.55 EUR",
        "Restmenge bei Auslösung: 2300",
        "Abgeschlossene Basiswertsitzungen zur Geldkurszeit: 20",
        "B04/B57 · hebeltrader-b04-b57-v1",
        f"Original-Geldkurszeit: {NOW.isoformat()}",
        f"Grund: {item.reason}",
        "keine Orderfreigabe",
    ):
        assert expected in body
    assert "TARGET_REACHED" not in body
    assert "None" not in body


def test_b04_formatter_does_not_invent_missing_version_or_quantity():
    item = replace(alert(AlertType.HEBELTRADER_B04_LOSS), price_context=None)
    body = format_position_alert(item, symbol=ISIN)
    assert "Regel: B04/B57 · —" in body
    assert "Restmenge bei Auslösung: —" in body
    assert "Name nicht verfügbar" in body
    assert "None" not in body


def store_fixture(*, alert_status="OPEN", notification_status="PENDING", cancelled=False):
    trade = TradeModel(
        id=uuid4(),
        workspace_id=uuid4(),
        product_id=uuid4(),
        origin="EXTERNAL",
        created_at=NOW - timedelta(days=40),
        created_by=uuid4(),
        cancelled_at=NOW if cancelled else None,
    )
    item = AlertModel(
        id=uuid4(),
        trade_id=trade.id,
        position_id=uuid4(),
        alert_type=AlertType.HEBELTRADER_B04_LOSS.value,
        status=alert_status,
    )
    notification = NotificationModel(
        id=uuid4(),
        alert_id=item.id,
        channel="TELEGRAM",
        destination_key="synthetic-no-delivery",
        body="Synthetic B04 notification",
        created_at=NOW,
        status=notification_status,
    )
    session = SimpleNamespace(
        scalar=AsyncMock(),
        scalars=AsyncMock(),
        execute=AsyncMock(),
        commit=AsyncMock(),
        flush=AsyncMock(),
        add=Mock(),
    )

    @asynccontextmanager
    async def session_context():
        yield session

    store = SqlAlchemyDurableNotificationDeliveryStore(
        SimpleNamespace(session_context=session_context)
    )
    adapter = SimpleNamespace(deliver=AsyncMock())
    delivery = DurableNotificationDeliveryService(
        store=store, adapter=adapter, new_id=uuid4, now=lambda: NOW
    )
    return SimpleNamespace(
        trade=trade,
        alert=item,
        notification=notification,
        session=session,
        store=store,
        adapter=adapter,
        delivery=delivery,
    )


def executions(trade, *, sold=10):
    common = dict(
        trade_id=trade.id,
        product_id=trade.product_id,
        price_per_unit=Decimal("0.55"),
        recorded_at=NOW,
        recorded_by=trade.created_by,
    )
    return [
        ExecutionRecord(id=uuid4(), quantity=10, executed_at=NOW - timedelta(days=40), **common),
        ExecutionRecord(
            id=uuid4(),
            quantity=sold,
            side=ExecutionSide.SELL,
            executed_at=NOW - timedelta(days=1),
            **common,
        ),
    ]


@pytest.mark.parametrize(
    "status,cancelled,code",
    [
        ("RESOLVED", False, "B04_ALERT_RESOLVED"),
        ("INVALIDATED", False, "B04_ALERT_INVALIDATED"),
        ("OPEN", True, "B04_TRADE_CANCELLED"),
    ],
)
async def test_terminal_business_state_is_persisted_without_external_call(status, cancelled, code):
    fixture = store_fixture(alert_status=status, cancelled=cancelled)
    fixture.session.scalar.side_effect = [
        fixture.trade.id,
        fixture.trade,
        fixture.notification,
        fixture.alert,
        None,
    ]
    result = await fixture.delivery.deliver(fixture.notification.id)
    assert result.status is DeliveryStatus.FAILED and not result.retryable
    assert result.error_code == code
    fixture.adapter.deliver.assert_not_awaited()
    assert fixture.notification.status == "FAILED"
    terminal = fixture.session.add.call_args.args[0]
    assert terminal.error_code == code
    assert terminal.status == "FAILED" and terminal.completed_at == NOW
    assert terminal.provider_message_id is None and not terminal.retryable
    fixture.session.commit.assert_awaited_once()


async def test_full_sale_uses_effective_owner_executions_and_repetition_keeps_history(
    monkeypatch,
):
    fixture = store_fixture()
    owner = AsyncMock(return_value=executions(fixture.trade))
    monkeypatch.setattr(SqlAlchemyExecutionRecordRepository, "list_effective_for_trade", owner)
    fixture.session.scalar.side_effect = [
        fixture.trade.id,
        fixture.trade,
        fixture.notification,
        fixture.alert,
        2,
    ]
    result = await fixture.delivery.deliver(fixture.notification.id)
    assert result.error_code == "B04_POSITION_CLOSED"
    owner.assert_awaited_once_with(fixture.trade.id)
    terminal = fixture.session.add.call_args.args[0]
    assert terminal.attempt_number == 3
    fixture.session.scalar.side_effect = [
        fixture.trade.id,
        fixture.trade,
        fixture.notification,
        fixture.alert,
        terminal,
    ]
    repeated = await fixture.delivery.deliver(fixture.notification.id)
    assert repeated == result
    fixture.session.add.assert_called_once()
    fixture.adapter.deliver.assert_not_awaited()
    # The full effective stream is read only after locking its economic trade.
    statement = fixture.session.scalar.call_args_list[1].args[0]
    assert "FOR UPDATE" in str(statement) and "trades" in str(statement)


async def test_delivered_history_is_not_rewritten_after_full_sale():
    fixture = store_fixture(alert_status="RESOLVED", notification_status="DELIVERED")
    fixture.session.scalar.side_effect = [
        fixture.trade.id,
        fixture.trade,
        fixture.notification,
        fixture.alert,
    ]
    result = await fixture.delivery.deliver(fixture.notification.id)
    assert result.status is DeliveryStatus.DELIVERED
    assert fixture.notification.status == "DELIVERED"
    fixture.session.add.assert_not_called()
    fixture.adapter.deliver.assert_not_awaited()


async def test_lifecycle_suppresses_only_pending_and_does_not_commit_caller_transaction():
    fixture = store_fixture()
    fixture.session.scalar.side_effect = [AlertType.HEBELTRADER_B04_LOSS.value, 4]
    fixture.session.scalars.return_value = [fixture.notification]
    assert (
        await suppress_pending_b04_notifications(
            fixture.session,
            alert_id=fixture.alert.id,
            now=NOW,
            reason="B04_ALERT_RESOLVED",
        )
    ) == 1
    assert fixture.notification.status == "FAILED"
    assert fixture.session.add.call_args.args[0].attempt_number == 5
    fixture.session.commit.assert_not_awaited()


async def test_lifecycle_rejects_other_alert_types():
    fixture = store_fixture()
    fixture.session.scalar.return_value = AlertType.STOP_REACHED.value
    with pytest.raises(ValueError, match="B04 alert"):
        await suppress_pending_b04_notifications(
            fixture.session,
            alert_id=fixture.alert.id,
            now=NOW,
            reason="B04_ALERT_RESOLVED",
        )
    fixture.session.scalars.assert_not_awaited()
    fixture.session.add.assert_not_called()


async def test_late_in_flight_failure_does_not_resurrect_a_suppressed_b04_notification():
    fixture = store_fixture(notification_status="FAILED")
    attempt = NotificationDeliveryAttemptModel(
        id=uuid4(),
        notification_id=fixture.notification.id,
        attempt_number=1,
        status="IN_PROGRESS",
        attempted_at=NOW,
        retryable=True,
    )
    fixture.session.scalar.side_effect = [attempt, fixture.notification, uuid4()]
    await fixture.store.complete(
        notification_id=fixture.notification.id,
        attempt_id=attempt.id,
        result=DeliveryResult(status=DeliveryStatus.FAILED, retryable=True, error_code="TIMEOUT"),
        completed_at=NOW,
        max_attempts=3,
    )
    assert attempt.status == "FAILED" and attempt.error_code == "TIMEOUT"
    assert attempt.retryable is True  # The actual transport result is preserved.
    assert fixture.notification.status == "FAILED"  # Its later suppression remains terminal.
    fixture.session.commit.assert_awaited_once()
