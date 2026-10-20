from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from app.features.trade_position.domain.price_binding import PriceBinding


class MonitoringRuleType(StrEnum):
    STOP_REACHED = "STOP_REACHED"
    TARGET_REACHED = "TARGET_REACHED"


@dataclass(frozen=True, slots=True)
class PriceObservation:
    value: Decimal
    observed_at: datetime | None
    price_binding: PriceBinding | None = None
    context: dict[str, str | None] | None = None
    received_at: datetime | None = None

    @property
    def ordering_time_basis(self) -> str:
        return "SOURCE_TIMESTAMP" if self.observed_at is not None else "RECEIPT_TIMESTAMP"

    @property
    def ordering_at(self) -> datetime:
        # Receipt orders accepted indications; it never becomes their source timestamp.
        value = self.observed_at if self.observed_at is not None else self.received_at
        if value is None or value.utcoffset() is None:
            raise ValueError("RULE_OBSERVATION_ORDERING_TIME_UNKNOWN")
        if self.observed_at is None and (
            not self.context or self.context.get("evaluation_mode") != "INDICATIVE_ISSUER"
        ):
            raise ValueError("RULE_OBSERVATION_TIMESTAMP_UNKNOWN")
        return value


@dataclass(frozen=True, slots=True)
class MonitoringRule:
    rule_key: str
    rule_type: MonitoringRuleType
    threshold: Decimal
    price_binding: PriceBinding | None = None

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
    price_binding_key: str | None = None
    time_basis: str = "SOURCE_TIMESTAMP"


@dataclass(frozen=True, slots=True)
class RuleEvaluation:
    triggered: bool
    reason: str
