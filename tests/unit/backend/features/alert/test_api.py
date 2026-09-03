from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.features.alert.api.router import list_trade_alerts
from app.features.alert.domain.models import AlertSeverity, AlertStatus, AlertType
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


class Repository:
    def __init__(self, value: AlertView) -> None:
        self.value = value
        self.trade_id: UUID | None = None

    async def list_for_trade(self, trade_id: UUID) -> tuple[AlertView, ...]:
        self.trade_id = trade_id
        return (self.value,)


@pytest.mark.asyncio
async def test_list_trade_alerts_exposes_channel_neutral_delivery_status() -> None:
    now = datetime(2026, 9, 3, 10, tzinfo=UTC)
    trade_id = uuid4()
    view = AlertView(
        id=uuid4(),
        position_id=uuid4(),
        trade_id=trade_id,
        alert_type=AlertType.STOP_REACHED,
        severity=AlertSeverity.WARNING,
        rule_key="stop",
        reason="stop reached",
        observed_value=Decimal("95"),
        threshold_value=Decimal("100"),
        market_data_observed_at=now,
        detected_at=now,
        status=AlertStatus.OPEN,
        resolved_at=None,
        notifications=(
            NotificationView(
                id=uuid4(),
                channel=NotificationChannel.TELEGRAM,
                destination_key="telegram_default",
                status=NotificationStatus.FAILED,
                created_at=now,
                last_delivery=DeliveryAttemptView(
                    status=DeliveryStatus.FAILED,
                    attempted_at=now,
                    completed_at=now,
                    retryable=True,
                    error_code="TELEGRAM_TIMEOUT",
                    error_message="timeout",
                ),
            ),
        ),
    )
    repository = Repository(view)

    response = await list_trade_alerts(trade_id, repository)  # type: ignore[arg-type]

    assert repository.trade_id == trade_id
    assert response[0].status is AlertStatus.OPEN
    assert response[0].notifications[0].status is NotificationStatus.FAILED
    assert response[0].notifications[0].last_delivery is not None
    assert response[0].notifications[0].last_delivery.error_code == "TELEGRAM_TIMEOUT"
