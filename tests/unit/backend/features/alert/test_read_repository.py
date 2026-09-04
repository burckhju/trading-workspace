from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.features.alert.persistence.models import AlertModel
from app.features.alert.persistence.read_repository import SqlAlchemyAlertReadRepository
from app.features.notification.persistence.models import (
    NotificationDeliveryAttemptModel,
    NotificationModel,
)


class ScalarRows:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows


class Session:
    def __init__(self, responses: list[list[object]]) -> None:
        self.responses = responses
        self.calls = 0

    async def scalars(self, _statement: object) -> ScalarRows:
        response = self.responses[self.calls]
        self.calls += 1
        return ScalarRows(response)


@pytest.mark.asyncio
async def test_read_repository_projects_alert_notification_and_latest_delivery() -> None:
    trade_id = uuid4()
    alert_id = uuid4()
    notification_id = uuid4()
    now = datetime(2026, 9, 3, 10, tzinfo=UTC)
    alert = AlertModel(
        id=alert_id,
        position_id=uuid4(),
        trade_id=trade_id,
        alert_type="TARGET_REACHED",
        severity="INFO",
        rule_key="target-1",
        reason="target reached",
        observed_value=Decimal("125"),
        threshold_value=Decimal("120"),
        market_data_observed_at=now,
        detected_at=now,
        status="OPEN",
        resolved_at=None,
    )
    notification = NotificationModel(
        id=notification_id,
        alert_id=alert_id,
        channel="TELEGRAM",
        destination_key="telegram_default",
        body="body",
        created_at=now,
        status="DELIVERED",
    )
    latest = NotificationDeliveryAttemptModel(
        id=uuid4(),
        notification_id=notification_id,
        attempt_number=2,
        status="DELIVERED",
        attempted_at=now,
        completed_at=now,
        retryable=False,
        provider_message_id="42",
        error_code=None,
        error_message=None,
    )
    older = NotificationDeliveryAttemptModel(
        id=uuid4(),
        notification_id=notification_id,
        attempt_number=1,
        status="FAILED",
        attempted_at=now,
        completed_at=now,
        retryable=True,
        provider_message_id=None,
        error_code="TIMEOUT",
        error_message="timeout",
    )
    session = Session([[alert], [notification], [latest, older]])

    values = await SqlAlchemyAlertReadRepository(session).list_for_trade(trade_id)  # type: ignore[arg-type]

    assert len(values) == 1
    view = values[0]
    assert view.id == alert_id
    assert view.alert_type.value == "TARGET_REACHED"
    assert len(view.notifications) == 1
    delivery = view.notifications[0].last_delivery
    assert delivery is not None
    assert delivery.status.value == "DELIVERED"
    assert delivery.error_code is None
    assert session.calls == 3


@pytest.mark.asyncio
async def test_read_repository_returns_empty_without_notification_queries() -> None:
    session = Session([[]])

    values = await SqlAlchemyAlertReadRepository(session).list_for_trade(uuid4())  # type: ignore[arg-type]

    assert values == ()
    assert session.calls == 1
