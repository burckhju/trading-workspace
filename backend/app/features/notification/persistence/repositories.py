from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.notification.domain.models import (
    DeliveryAttempt,
    Notification,
    NotificationChannel,
    NotificationStatus,
)
from app.features.notification.persistence.models import (
    NotificationDeliveryAttemptModel,
    NotificationModel,
)


class NotificationRepository(Protocol):
    async def add(self, notification: Notification) -> None: ...

    async def get(self, notification_id: UUID) -> Notification | None: ...

    async def get_for_alert(
        self, *, alert_id: UUID, channel: NotificationChannel, destination_key: str
    ) -> Notification | None: ...

    async def set_status(self, notification_id: UUID, status: NotificationStatus) -> None: ...

    async def next_attempt_number(self, notification_id: UUID) -> int: ...

    async def add_attempt(self, attempt: DeliveryAttempt) -> None: ...


class SqlAlchemyNotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, notification: Notification) -> None:
        self._session.add(
            NotificationModel(
                id=notification.id,
                alert_id=notification.alert_id,
                channel=notification.channel.value,
                destination_key=notification.destination_key,
                body=notification.body,
                created_at=notification.created_at,
                status=notification.status.value,
            )
        )

    async def get(self, notification_id: UUID) -> Notification | None:
        model = await self._session.scalar(
            select(NotificationModel).where(NotificationModel.id == notification_id)
        )
        return None if model is None else self._to_domain(model)

    async def get_for_alert(
        self, *, alert_id: UUID, channel: NotificationChannel, destination_key: str
    ) -> Notification | None:
        model = await self._session.scalar(
            select(NotificationModel).where(
                NotificationModel.alert_id == alert_id,
                NotificationModel.channel == channel.value,
                NotificationModel.destination_key == destination_key,
            )
        )
        return None if model is None else self._to_domain(model)

    async def set_status(self, notification_id: UUID, status: NotificationStatus) -> None:
        model = await self._session.scalar(
            select(NotificationModel).where(NotificationModel.id == notification_id)
        )
        if model is None:
            raise LookupError("notification not found")
        model.status = status.value

    async def next_attempt_number(self, notification_id: UUID) -> int:
        current = await self._session.scalar(
            select(func.max(NotificationDeliveryAttemptModel.attempt_number)).where(
                NotificationDeliveryAttemptModel.notification_id == notification_id
            )
        )
        return int(current or 0) + 1

    async def add_attempt(self, attempt: DeliveryAttempt) -> None:
        self._session.add(
            NotificationDeliveryAttemptModel(
                id=attempt.id,
                notification_id=attempt.notification_id,
                attempt_number=attempt.attempt_number,
                status=attempt.status.value,
                attempted_at=attempt.attempted_at,
                completed_at=attempt.completed_at,
                retryable=attempt.retryable,
                provider_message_id=attempt.provider_message_id,
                error_code=attempt.error_code,
                error_message=attempt.error_message,
            )
        )

    @staticmethod
    def _to_domain(model: NotificationModel) -> Notification:
        return Notification(
            id=model.id,
            alert_id=model.alert_id,
            channel=NotificationChannel(model.channel),
            destination_key=model.destination_key,
            body=model.body,
            created_at=model.created_at,
            status=NotificationStatus(model.status),
        )
