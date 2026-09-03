from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update

from app.database import DatabaseManager
from app.features.notification.domain.models import (
    DeliveryAttempt,
    DeliveryPreparation,
    DeliveryResult,
    DeliveryStatus,
    Notification,
    NotificationChannel,
    NotificationStatus,
)
from app.features.notification.persistence.models import (
    NotificationDeliveryAttemptModel,
    NotificationModel,
)


class SqlAlchemyDurableNotificationDeliveryStore:
    """Persist preparation and completion in separate database transactions."""

    def __init__(self, database: DatabaseManager) -> None:
        self._database = database

    async def prepare(
        self,
        *,
        notification_id: UUID,
        attempt_id: UUID,
        now: datetime,
        stale_before: datetime,
        max_attempts: int,
    ) -> DeliveryPreparation:
        async with self._database.session_context() as session:
            model = await session.scalar(
                select(NotificationModel)
                .where(NotificationModel.id == notification_id)
                .with_for_update()
            )
            if model is None:
                raise LookupError("notification not found")
            notification = self._notification(model)
            if notification.status is NotificationStatus.DELIVERED:
                return DeliveryPreparation(
                    notification=notification,
                    terminal_result=DeliveryResult(
                        status=DeliveryStatus.DELIVERED,
                        retryable=False,
                    ),
                )

            await session.execute(
                update(NotificationDeliveryAttemptModel)
                .where(
                    NotificationDeliveryAttemptModel.notification_id == notification_id,
                    NotificationDeliveryAttemptModel.status == DeliveryStatus.IN_PROGRESS.value,
                    NotificationDeliveryAttemptModel.attempted_at <= stale_before,
                )
                .values(
                    status=DeliveryStatus.FAILED.value,
                    completed_at=now,
                    retryable=True,
                    error_code="PROCESS_INTERRUPTED",
                    error_message="Previous delivery attempt did not complete before recovery timeout",
                )
            )
            current = await session.scalar(
                select(func.max(NotificationDeliveryAttemptModel.attempt_number)).where(
                    NotificationDeliveryAttemptModel.notification_id == notification_id
                )
            )
            attempt_number = int(current or 0) + 1
            if attempt_number > max_attempts:
                model.status = NotificationStatus.FAILED.value
                await session.commit()
                return DeliveryPreparation(
                    notification=self._notification(model),
                    terminal_result=DeliveryResult(
                        status=DeliveryStatus.FAILED,
                        retryable=False,
                        error_code="MAX_ATTEMPTS_EXCEEDED",
                        error_message="notification delivery attempt limit exceeded",
                    ),
                )

            attempt = DeliveryAttempt(
                id=attempt_id,
                notification_id=notification_id,
                attempt_number=attempt_number,
                status=DeliveryStatus.IN_PROGRESS,
                attempted_at=now,
                completed_at=None,
                retryable=True,
            )
            session.add(
                NotificationDeliveryAttemptModel(
                    id=attempt.id,
                    notification_id=attempt.notification_id,
                    attempt_number=attempt.attempt_number,
                    status=attempt.status.value,
                    attempted_at=attempt.attempted_at,
                    completed_at=None,
                    retryable=True,
                    provider_message_id=None,
                    error_code=None,
                    error_message=None,
                )
            )
            model.status = NotificationStatus.PENDING.value
            await session.commit()
            return DeliveryPreparation(notification=notification, attempt=attempt)

    async def complete(
        self,
        *,
        notification_id: UUID,
        attempt_id: UUID,
        result: DeliveryResult,
        completed_at: datetime,
        max_attempts: int,
    ) -> None:
        if result.status is DeliveryStatus.IN_PROGRESS:
            raise ValueError("delivery result cannot remain in progress")
        async with self._database.session_context() as session:
            attempt = await session.scalar(
                select(NotificationDeliveryAttemptModel)
                .where(NotificationDeliveryAttemptModel.id == attempt_id)
                .with_for_update()
            )
            notification = await session.scalar(
                select(NotificationModel)
                .where(NotificationModel.id == notification_id)
                .with_for_update()
            )
            if attempt is None or attempt.notification_id != notification_id:
                raise LookupError("delivery attempt not found")
            if notification is None:
                raise LookupError("notification not found")
            if attempt.status != DeliveryStatus.IN_PROGRESS.value:
                return

            attempt.status = result.status.value
            attempt.completed_at = completed_at
            attempt.retryable = result.retryable
            attempt.provider_message_id = result.provider_message_id
            attempt.error_code = result.error_code
            attempt.error_message = result.error_message
            if result.status is DeliveryStatus.DELIVERED:
                notification.status = NotificationStatus.DELIVERED.value
            elif not result.retryable or attempt.attempt_number >= max_attempts:
                notification.status = NotificationStatus.FAILED.value
            else:
                notification.status = NotificationStatus.PENDING.value
            await session.commit()

    @staticmethod
    def _notification(model: NotificationModel) -> Notification:
        return Notification(
            id=model.id,
            alert_id=model.alert_id,
            channel=NotificationChannel(model.channel),
            destination_key=model.destination_key,
            body=model.body,
            created_at=model.created_at,
            status=NotificationStatus(model.status),
        )
