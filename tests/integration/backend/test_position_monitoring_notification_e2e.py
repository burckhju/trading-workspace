from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.features.alert.domain.models import Alert, AlertStatus
from app.features.notification.domain.models import (
    DeliveryAttempt,
    DeliveryResult,
    DeliveryStatus,
    Notification,
    NotificationChannel,
    NotificationStatus,
)
from app.features.notification.service.creation import AlertNotificationService
from app.features.notification.service.delivery import NotificationDeliveryService
from app.features.position_monitoring.domain.models import (
    MonitoringRule,
    MonitoringRuleState,
    MonitoringRuleType,
    PriceObservation,
)
from app.features.position_monitoring.service.application import PositionMonitoringService

NOW = datetime(2026, 9, 3, 10, 0, tzinfo=UTC)


class MemoryStates:
    def __init__(self) -> None:
        self.items: dict[tuple[UUID, str], MonitoringRuleState] = {}

    async def get(self, *, position_id: UUID, rule_key: str) -> MonitoringRuleState | None:
        return self.items.get((position_id, rule_key))

    async def put(self, state: MonitoringRuleState) -> None:
        self.items[(state.position_id, state.rule_key)] = state


class MemoryAlerts:
    def __init__(self) -> None:
        self.items: dict[UUID, Alert] = {}

    async def add(self, alert: Alert) -> None:
        self.items[alert.id] = alert

    async def get(self, alert_id: UUID) -> Alert | None:
        return self.items.get(alert_id)

    async def resolve(self, alert_id: UUID, *, resolved_at: datetime) -> None:
        alert = self.items[alert_id]
        self.items[alert_id] = replace(
            alert,
            status=AlertStatus.RESOLVED,
            resolved_at=resolved_at,
        )


class MemoryNotifications:
    def __init__(self) -> None:
        self.items: dict[UUID, Notification] = {}
        self.attempts: list[DeliveryAttempt] = []

    async def add(self, notification: Notification) -> None:
        self.items[notification.id] = notification

    async def get(self, notification_id: UUID) -> Notification | None:
        return self.items.get(notification_id)

    async def get_for_alert(
        self,
        *,
        alert_id: UUID,
        channel: NotificationChannel,
        destination_key: str,
    ) -> Notification | None:
        return next(
            (
                item
                for item in self.items.values()
                if item.alert_id == alert_id
                and item.channel is channel
                and item.destination_key == destination_key
            ),
            None,
        )

    async def set_status(self, notification_id: UUID, status: NotificationStatus) -> None:
        self.items[notification_id] = replace(self.items[notification_id], status=status)

    async def next_attempt_number(self, notification_id: UUID) -> int:
        return 1 + sum(item.notification_id == notification_id for item in self.attempts)

    async def add_attempt(self, attempt: DeliveryAttempt) -> None:
        self.attempts.append(attempt)


class DeliveryAdapter:
    def __init__(self, *, result: DeliveryResult) -> None:
        self.result = result
        self.bodies: list[str] = []

    async def deliver(self, *, body: str) -> DeliveryResult:
        self.bodies.append(body)
        return self.result


def monitoring_service(states: MemoryStates, alerts: MemoryAlerts) -> PositionMonitoringService:
    return PositionMonitoringService(states=states, alerts=alerts, new_id=uuid4, now=lambda: NOW)


def notification_service(notifications: MemoryNotifications) -> AlertNotificationService:
    return AlertNotificationService(notifications=notifications, new_id=uuid4, now=lambda: NOW)


@pytest.mark.asyncio
async def test_trigger_creates_exactly_one_alert_notification_and_delivery() -> None:
    position_id = uuid4()
    trade_id = uuid4()
    states = MemoryStates()
    alerts = MemoryAlerts()
    notifications = MemoryNotifications()
    monitor = monitoring_service(states, alerts)
    rule = MonitoringRule("target-1", MonitoringRuleType.TARGET_REACHED, Decimal("120"))
    observation = PriceObservation(Decimal("121"), NOW)

    first = await monitor.evaluate(
        position_id=position_id,
        trade_id=trade_id,
        rule=rule,
        observation=observation,
    )
    assert first.alert is not None
    assert len(alerts.items) == 1

    notification = await notification_service(notifications).create_telegram(
        alert=first.alert,
        symbol="SAP",
    )
    adapter = DeliveryAdapter(
        result=DeliveryResult(
            status=DeliveryStatus.DELIVERED,
            retryable=False,
            provider_message_id="telegram-42",
        )
    )
    delivered = await NotificationDeliveryService(
        notifications=notifications,
        adapter=adapter,
        new_id=uuid4,
        now=lambda: NOW,
    ).deliver(notification.id)

    assert delivered.status is DeliveryStatus.DELIVERED
    assert len(notifications.items) == 1
    assert len(notifications.attempts) == 1
    assert len(adapter.bodies) == 1
    assert notifications.items[notification.id].status is NotificationStatus.DELIVERED

    repeated = await monitor.evaluate(
        position_id=position_id,
        trade_id=trade_id,
        rule=rule,
        observation=observation,
    )
    assert repeated.alert is None
    assert len(alerts.items) == 1
    assert len(notifications.items) == 1
    assert len(adapter.bodies) == 1


@pytest.mark.asyncio
async def test_delivery_failure_keeps_alert_and_retry_does_not_recreate_it() -> None:
    position_id = uuid4()
    trade_id = uuid4()
    states = MemoryStates()
    alerts = MemoryAlerts()
    notifications = MemoryNotifications()
    monitor = monitoring_service(states, alerts)
    rule = MonitoringRule("stop", MonitoringRuleType.STOP_REACHED, Decimal("100"))
    observation = PriceObservation(Decimal("99"), NOW)

    first = await monitor.evaluate(
        position_id=position_id,
        trade_id=trade_id,
        rule=rule,
        observation=observation,
    )
    assert first.alert is not None
    notification_creator = notification_service(notifications)
    notification = await notification_creator.create_telegram(alert=first.alert, symbol="SAP")
    adapter = DeliveryAdapter(
        result=DeliveryResult(
            status=DeliveryStatus.FAILED,
            retryable=True,
            error_code="TELEGRAM_TIMEOUT",
            error_message="timeout",
        )
    )
    result = await NotificationDeliveryService(
        notifications=notifications,
        adapter=adapter,
        new_id=uuid4,
        now=lambda: NOW,
    ).deliver(notification.id)

    assert result.status is DeliveryStatus.FAILED
    assert result.retryable is True
    assert await alerts.get(first.alert.id) is not None
    assert len(alerts.items) == 1
    assert len(notifications.attempts) == 1

    repeated = await monitor.evaluate(
        position_id=position_id,
        trade_id=trade_id,
        rule=rule,
        observation=observation,
    )
    same_notification = await notification_creator.create_telegram(
        alert=first.alert,
        symbol="SAP",
    )
    assert repeated.alert is None
    assert same_notification.id == notification.id
    assert len(alerts.items) == 1
    assert len(notifications.items) == 1
