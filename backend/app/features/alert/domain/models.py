from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class AlertType(StrEnum):
    STOP_REACHED = "STOP_REACHED"
    TARGET_REACHED = "TARGET_REACHED"
    RISK_TREND_CHANGED = "RISK_TREND_CHANGED"
    RISK_VOLATILITY_HIGH = "RISK_VOLATILITY_HIGH"


class AlertSeverity(StrEnum):
    WARNING = "WARNING"
    INFO = "INFO"


class AlertStatus(StrEnum):
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    INVALIDATED = "INVALIDATED"


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
    market_data_observed_at: datetime | None
    detected_at: datetime
    status: AlertStatus = AlertStatus.OPEN
    resolved_at: datetime | None = None
    price_context: dict[str, str | None] | None = None
    invalidated_at: datetime | None = None
    invalidation_reason: str | None = None
