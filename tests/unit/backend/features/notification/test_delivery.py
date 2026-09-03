from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.features.notification.domain.models import (
    DeliveryAttempt,
    DeliveryResult,
    DeliveryStatus,
    Notification,
    NotificationChannel,
    NotificationStatus,
)
from app.features.notification.service.delivery import NotificationDeliveryService


class Repo:
    def __init__(self, notification: Notification) -> None:
        self.notification = notification
        self.attempts: list[DeliveryAttempt] = []

    async def get(self, notification_id: UUID) -> Notification | None:
        return self.notification if self.notification.id == notification_id else None

    async def set_status(self, notification_id: UUID, status: NotificationStatus) -> None:
        self.notification = Notification(
            id=self.notification.id,
            alert_id=self.notification.alert_id,
            channel=self.notification.channel,
            destination_key=self.notification.destination_key,
            body=self.notification.body,
            created_at=self.notification.created_at,
            status=status,
        )

    async def next_attempt_number(self, notification_id: UUID) -> int:
        return len(self.attempts) + 1

    async def add_attempt(self, attempt: DeliveryAttempt) -> None:
        self.attempts.append(attempt)


class Adapter:
    def __init__(self, results: list[DeliveryResult]) -> None:
        self.results = results
        self.calls = 0

    async def deliver(self, *, body: str) -> DeliveryResult:
        result = self.results[self.calls]
        self.calls += 1
        return result


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
async def test_success_is_persisted_and_repeat_does_not_send_twice() -> None:
    item = notification()
    repo = Repo(item)
    adapter = Adapter([DeliveryResult(DeliveryStatus.DELIVERED, False, "42")])
    service = NotificationDeliveryService(
        notifications=repo,
        adapter=adapter,
        new_id=uuid4,
        now=lambda: datetime(2026, 9, 3, 10, tzinfo=UTC),
    )

    await service.deliver(item.id)
    await service.deliver(item.id)

    assert adapter.calls == 1
    assert repo.notification.status is NotificationStatus.DELIVERED
    assert len(repo.attempts) == 1


@pytest.mark.asyncio
async def test_retryable_failure_keeps_alert_independent_and_reuses_notification() -> None:
    item = notification()
    repo = Repo(item)
    adapter = Adapter(
        [
            DeliveryResult(DeliveryStatus.FAILED, True, error_code="TIMEOUT"),
            DeliveryResult(DeliveryStatus.DELIVERED, False, "43"),
        ]
    )
    service = NotificationDeliveryService(
        notifications=repo,
        adapter=adapter,
        new_id=uuid4,
        now=lambda: datetime(2026, 9, 3, 10, tzinfo=UTC),
    )

    first = await service.deliver(item.id)
    second = await service.deliver(item.id)

    assert first.retryable is True
    assert second.status is DeliveryStatus.DELIVERED
    assert adapter.calls == 2
    assert len(repo.attempts) == 2
    assert repo.notification.id == item.id
    assert repo.notification.alert_id == item.alert_id
