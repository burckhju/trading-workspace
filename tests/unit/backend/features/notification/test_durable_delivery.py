from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.features.notification.domain.models import (
    DeliveryAttempt,
    DeliveryPreparation,
    DeliveryResult,
    DeliveryStatus,
    Notification,
    NotificationChannel,
)
from app.features.notification.service.durable_delivery import DurableNotificationDeliveryService


class Store:
    def __init__(self, notification: Notification) -> None:
        self.notification = notification
        self.prepared = False
        self.completed: list[DeliveryResult] = []

    async def prepare(
        self,
        *,
        notification_id: UUID,
        attempt_id: UUID,
        now: datetime,
        stale_before: datetime,
        max_attempts: int,
    ) -> DeliveryPreparation:
        assert notification_id == self.notification.id
        assert stale_before == now - timedelta(minutes=5)
        assert max_attempts == 3
        self.prepared = True
        return DeliveryPreparation(
            notification=self.notification,
            attempt=DeliveryAttempt(
                id=attempt_id,
                notification_id=notification_id,
                attempt_number=1,
                status=DeliveryStatus.IN_PROGRESS,
                attempted_at=now,
                completed_at=None,
                retryable=True,
            ),
        )

    async def complete(
        self,
        *,
        notification_id: UUID,
        attempt_id: UUID,
        result: DeliveryResult,
        completed_at: datetime,
        max_attempts: int,
    ) -> None:
        assert notification_id == self.notification.id
        assert attempt_id
        assert completed_at.tzinfo is UTC
        assert max_attempts == 3
        self.completed.append(result)


class Adapter:
    def __init__(self, store: Store, *, raise_error: bool = False) -> None:
        self.store = store
        self.raise_error = raise_error
        self.calls = 0

    async def deliver(self, *, body: str) -> DeliveryResult:
        assert self.store.prepared is True
        assert body == "Position Alert"
        self.calls += 1
        if self.raise_error:
            raise RuntimeError("connection lost")
        return DeliveryResult(
            status=DeliveryStatus.DELIVERED,
            retryable=False,
            provider_message_id="42",
        )


def notification() -> Notification:
    return Notification(
        id=uuid4(),
        alert_id=uuid4(),
        channel=NotificationChannel.TELEGRAM,
        destination_key="telegram_default",
        body="Position Alert",
        created_at=datetime(2026, 9, 3, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_attempt_is_prepared_before_external_delivery() -> None:
    item = notification()
    store = Store(item)
    adapter = Adapter(store)
    service = DurableNotificationDeliveryService(
        store=store,
        adapter=adapter,
        new_id=uuid4,
        now=lambda: datetime(2026, 9, 3, 10, tzinfo=UTC),
    )

    result = await service.deliver(item.id)

    assert result.status is DeliveryStatus.DELIVERED
    assert adapter.calls == 1
    assert store.completed == [result]


@pytest.mark.asyncio
async def test_unexpected_adapter_error_is_persisted_as_retryable_failure() -> None:
    item = notification()
    store = Store(item)
    adapter = Adapter(store, raise_error=True)
    service = DurableNotificationDeliveryService(
        store=store,
        adapter=adapter,
        new_id=uuid4,
        now=lambda: datetime(2026, 9, 3, 10, tzinfo=UTC),
    )

    result = await service.deliver(item.id)

    assert result.status is DeliveryStatus.FAILED
    assert result.retryable is True
    assert result.error_code == "DELIVERY_EXCEPTION"
    assert store.completed == [result]
