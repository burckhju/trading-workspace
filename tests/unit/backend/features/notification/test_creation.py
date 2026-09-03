from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.features.alert.domain.models import Alert, AlertSeverity, AlertType
from app.features.notification.domain.models import Notification, NotificationChannel
from app.features.notification.service.creation import AlertNotificationService


class Repo:
    def __init__(self) -> None:
        self.values: list[Notification] = []

    async def get_for_alert(
        self, *, alert_id: UUID, channel: NotificationChannel, destination_key: str
    ) -> Notification | None:
        return next(
            (
                item
                for item in self.values
                if item.alert_id == alert_id
                and item.channel is channel
                and item.destination_key == destination_key
            ),
            None,
        )

    async def add(self, notification: Notification) -> None:
        self.values.append(notification)


@pytest.mark.asyncio
async def test_alert_creates_exactly_one_telegram_notification() -> None:
    repo = Repo()
    service = AlertNotificationService(
        notifications=repo,
        new_id=uuid4,
        now=lambda: datetime(2026, 9, 3, 10, tzinfo=UTC),
    )
    alert = Alert(
        id=uuid4(),
        position_id=uuid4(),
        trade_id=uuid4(),
        alert_type=AlertType.TARGET_REACHED,
        severity=AlertSeverity.INFO,
        rule_key="target:120",
        reason="threshold reached",
        observed_value=Decimal("121"),
        threshold_value=Decimal("120"),
        market_data_observed_at=datetime(2026, 9, 3, tzinfo=UTC),
        detected_at=datetime(2026, 9, 3, tzinfo=UTC),
    )

    first = await service.create_telegram(alert=alert, symbol="SAP")
    second = await service.create_telegram(alert=alert, symbol="SAP")

    assert first.id == second.id
    assert len(repo.values) == 1
    assert "Target erreicht" in first.body
