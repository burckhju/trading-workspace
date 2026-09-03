from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.features.notification.domain.models import (
    DeliveryAttempt,
    DeliveryResult,
    DeliveryStatus,
    NotificationStatus,
)
from app.features.notification.persistence.repositories import NotificationRepository


class NotificationDeliveryAdapter(Protocol):
    async def deliver(self, *, body: str) -> DeliveryResult: ...


class NotificationDeliveryService:
    """Provider-neutral delivery orchestration; retries never recreate alerts."""

    def __init__(
        self,
        *,
        notifications: NotificationRepository,
        adapter: NotificationDeliveryAdapter,
        new_id: Callable[[], UUID],
        now: Callable[[], datetime],
        max_attempts: int = 3,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self._notifications = notifications
        self._adapter = adapter
        self._new_id = new_id
        self._now = now
        self._max_attempts = max_attempts

    async def deliver(self, notification_id: UUID) -> DeliveryResult:
        notification = await self._notifications.get(notification_id)
        if notification is None:
            raise LookupError("notification not found")
        if notification.status is NotificationStatus.DELIVERED:
            return DeliveryResult(status=DeliveryStatus.DELIVERED, retryable=False)

        attempt_number = await self._notifications.next_attempt_number(notification_id)
        if attempt_number > self._max_attempts:
            result = DeliveryResult(
                status=DeliveryStatus.FAILED,
                retryable=False,
                error_code="MAX_ATTEMPTS_EXCEEDED",
                error_message="notification delivery attempt limit exceeded",
            )
            await self._notifications.set_status(notification_id, NotificationStatus.FAILED)
            return result

        attempted_at = self._now()
        result = await self._adapter.deliver(body=notification.body)
        completed_at = self._now()
        await self._notifications.add_attempt(
            DeliveryAttempt(
                id=self._new_id(),
                notification_id=notification_id,
                attempt_number=attempt_number,
                status=result.status,
                attempted_at=attempted_at,
                completed_at=completed_at,
                retryable=result.retryable,
                provider_message_id=result.provider_message_id,
                error_code=result.error_code,
                error_message=result.error_message,
            )
        )
        if result.status is DeliveryStatus.DELIVERED:
            await self._notifications.set_status(notification_id, NotificationStatus.DELIVERED)
        elif not result.retryable or attempt_number >= self._max_attempts:
            await self._notifications.set_status(notification_id, NotificationStatus.FAILED)
        return result
