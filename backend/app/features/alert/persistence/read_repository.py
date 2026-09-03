from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.alert.domain.models import AlertSeverity, AlertStatus, AlertType
from app.features.alert.persistence.models import AlertModel
from app.features.alert.service.read_models import (
    AlertView,
    DeliveryAttemptView,
    NotificationView,
)
from app.features.notification.domain.models import (
    DeliveryStatus,
    NotificationChannel,
    NotificationStatus,
)
from app.features.notification.persistence.models import (
    NotificationDeliveryAttemptModel,
    NotificationModel,
)


class SqlAlchemyAlertReadRepository:
    """Read-optimized projection for trade-management alert visibility."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_trade(self, trade_id: UUID) -> tuple[AlertView, ...]:
        alert_models = tuple(
            (
                await self._session.scalars(
                    select(AlertModel)
                    .where(AlertModel.trade_id == trade_id)
                    .order_by(AlertModel.detected_at.desc())
                )
            ).all()
        )
        if not alert_models:
            return ()

        alert_ids = [item.id for item in alert_models]
        notification_models = tuple(
            (
                await self._session.scalars(
                    select(NotificationModel)
                    .where(NotificationModel.alert_id.in_(alert_ids))
                    .order_by(NotificationModel.created_at.asc())
                )
            ).all()
        )
        notification_ids = [item.id for item in notification_models]
        attempts_by_notification: dict[UUID, NotificationDeliveryAttemptModel] = {}
        if notification_ids:
            attempt_models = tuple(
                (
                    await self._session.scalars(
                        select(NotificationDeliveryAttemptModel)
                        .where(
                            NotificationDeliveryAttemptModel.notification_id.in_(notification_ids)
                        )
                        .order_by(
                            NotificationDeliveryAttemptModel.notification_id.asc(),
                            NotificationDeliveryAttemptModel.attempt_number.desc(),
                        )
                    )
                ).all()
            )
            for attempt in attempt_models:
                attempts_by_notification.setdefault(attempt.notification_id, attempt)

        notifications_by_alert: dict[UUID, list[NotificationView]] = defaultdict(list)
        for notification in notification_models:
            attempt = attempts_by_notification.get(notification.id)
            last_delivery = None
            if attempt is not None:
                last_delivery = DeliveryAttemptView(
                    status=DeliveryStatus(attempt.status),
                    attempted_at=attempt.attempted_at,
                    completed_at=attempt.completed_at,
                    retryable=attempt.retryable,
                    error_code=attempt.error_code,
                    error_message=attempt.error_message,
                )
            notifications_by_alert[notification.alert_id].append(
                NotificationView(
                    id=notification.id,
                    channel=NotificationChannel(notification.channel),
                    destination_key=notification.destination_key,
                    status=NotificationStatus(notification.status),
                    created_at=notification.created_at,
                    last_delivery=last_delivery,
                )
            )

        return tuple(
            AlertView(
                id=alert.id,
                position_id=alert.position_id,
                trade_id=alert.trade_id,
                alert_type=AlertType(alert.alert_type),
                severity=AlertSeverity(alert.severity),
                rule_key=alert.rule_key,
                reason=alert.reason,
                observed_value=alert.observed_value,
                threshold_value=alert.threshold_value,
                market_data_observed_at=alert.market_data_observed_at,
                detected_at=alert.detected_at,
                status=AlertStatus(alert.status),
                resolved_at=alert.resolved_at,
                notifications=tuple(notifications_by_alert.get(alert.id, ())),
            )
            for alert in alert_models
        )
