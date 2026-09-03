from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from app.features.alert.domain.models import Alert
from app.features.notification.domain.models import Notification, NotificationChannel
from app.features.notification.persistence.repositories import NotificationRepository
from app.features.notification.service.formatter import format_position_alert


class AlertNotificationService:
    """Create at most one channel notification for a persisted alert."""

    def __init__(
        self,
        *,
        notifications: NotificationRepository,
        new_id: Callable[[], UUID],
        now: Callable[[], datetime],
    ) -> None:
        self._notifications = notifications
        self._new_id = new_id
        self._now = now

    async def create_telegram(
        self,
        *,
        alert: Alert,
        symbol: str,
        destination_key: str = "telegram_default",
    ) -> Notification:
        existing = await self._notifications.get_for_alert(
            alert_id=alert.id,
            channel=NotificationChannel.TELEGRAM,
            destination_key=destination_key,
        )
        if existing is not None:
            return existing
        notification = Notification(
            id=self._new_id(),
            alert_id=alert.id,
            channel=NotificationChannel.TELEGRAM,
            destination_key=destination_key,
            body=format_position_alert(alert, symbol=symbol),
            created_at=self._now(),
        )
        await self._notifications.add(notification)
        return notification
