from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class NotificationChannel(StrEnum):
    TELEGRAM = "TELEGRAM"


class NotificationStatus(StrEnum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class DeliveryStatus(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class Notification:
    id: UUID
    alert_id: UUID
    channel: NotificationChannel
    destination_key: str
    body: str
    created_at: datetime
    status: NotificationStatus = NotificationStatus.PENDING


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    status: DeliveryStatus
    retryable: bool
    provider_message_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class DeliveryAttempt:
    id: UUID
    notification_id: UUID
    attempt_number: int
    status: DeliveryStatus
    attempted_at: datetime
    completed_at: datetime | None
    retryable: bool
    provider_message_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class DeliveryPreparation:
    notification: Notification
    attempt: DeliveryAttempt | None = None
    terminal_result: DeliveryResult | None = None
