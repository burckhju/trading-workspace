from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class MonitoringRuleType(StrEnum):
    STOP_REACHED = "STOP_REACHED"
    TARGET_REACHED = "TARGET_REACHED"


@dataclass(frozen=True, slots=True)
class PriceObservation:
    value: Decimal
    observed_at: datetime


@dataclass(frozen=True, slots=True)
class MonitoringRule:
    rule_key: str
    rule_type: MonitoringRuleType
    threshold: Decimal

    def __post_init__(self) -> None:
        if not self.rule_key.strip():
            raise ValueError("rule_key must not be blank")
        if self.threshold <= 0:
            raise ValueError("threshold must be positive")


@dataclass(frozen=True, slots=True)
class MonitoringRuleState:
    position_id: UUID
    rule_key: str
    triggered: bool
    first_seen_at: datetime | None
    last_seen_at: datetime
    last_observed_value: Decimal
    threshold_value: Decimal
    active_alert_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class RuleEvaluation:
    triggered: bool
    reason: str
