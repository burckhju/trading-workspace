from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.features.alert.domain.models import AlertSeverity, AlertStatus, AlertType
from app.features.notification.domain.models import DeliveryStatus, NotificationChannel, NotificationStatus


class DeliveryAttemptResponse(BaseModel):
    status: DeliveryStatus
    attempted_at: datetime
    completed_at: datetime | None
    retryable: bool
    error_code: str | None
    error_message: str | None


class NotificationResponse(BaseModel):
    id: UUID
    channel: NotificationChannel
    destination_key: str
    status: NotificationStatus
    created_at: datetime
    last_delivery: DeliveryAttemptResponse | None


class AlertResponse(BaseModel):
    id: UUID
    position_id: UUID
    trade_id: UUID
    alert_type: AlertType
    severity: AlertSeverity
    rule_key: str
    reason: str
    observed_value: Decimal
    threshold_value: Decimal
    market_data_observed_at: datetime
    detected_at: datetime
    status: AlertStatus
    resolved_at: datetime | None
    notifications: list[NotificationResponse]
