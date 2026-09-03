from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class AlertType(StrEnum):
    STOP_REACHED = "STOP_REACHED"
    TARGET_REACHED = "TARGET_REACHED"


class AlertSeverity(StrEnum):
    WARNING = "WARNING"
    INFO = "INFO"


class AlertStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


@dataclass(frozen=True, slots=True)
class Alert:
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
    status: AlertStatus = AlertStatus.OPEN
    resolved_at: datetime | None = None
