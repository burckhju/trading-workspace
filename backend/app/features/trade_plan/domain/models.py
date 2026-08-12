"""Immutable FT-007 TradePlan domain snapshots and value objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.features.trade_plan.domain.enums import (
    EntryType,
    TradeDirection,
    TradePlanOriginType,
    TradePlanStatus,
)


def _positive(value: Decimal | None, name: str) -> None:
    if value is not None and value <= 0:
        raise ValueError(f"{name} must be positive")


@dataclass(frozen=True, slots=True)
class TradePlan:
    id: UUID
    workspace_id: UUID
    underlying_id: UUID
    origin_type: TradePlanOriginType
    created_at: datetime
    created_by: UUID
    candidate_id: UUID | None = None
    candidate_evaluation_id: UUID | None = None

    def __post_init__(self) -> None:
        has_candidate = (
            self.candidate_id is not None or self.candidate_evaluation_id is not None
        )
        if self.origin_type is TradePlanOriginType.MANUAL and has_candidate:
            raise ValueError("manual trade plan cannot reference candidate provenance")
        if self.origin_type is TradePlanOriginType.CANDIDATE_EVALUATION and (
            self.candidate_id is None or self.candidate_evaluation_id is None
        ):
            raise ValueError(
                "candidate-originated trade plan requires candidate and candidate evaluation"
            )


@dataclass(frozen=True, slots=True)
class EntryPlan:
    type: EntryType
    currency: str
    price: Decimal | None = None
    price_from: Decimal | None = None
    price_to: Decimal | None = None
    trigger: str | None = None
    reference_price: Decimal | None = None
    valid_until: datetime | None = None
    rationale: str | None = None

    def __post_init__(self) -> None:
        if not self.currency.strip():
            raise ValueError("entry currency is required")
        for value, name in (
            (self.price, "entry price"),
            (self.price_from, "entry range start"),
            (self.price_to, "entry range end"),
            (self.reference_price, "entry reference price"),
        ):
            _positive(value, name)
        if self.type is EntryType.PRICE:
            if self.price is None or any(
                v is not None for v in (self.price_from, self.price_to, self.trigger)
            ):
                raise ValueError("PRICE entry requires only price")
        elif self.type is EntryType.PRICE_RANGE:
            if (
                self.price_from is None
                or self.price_to is None
                or self.price is not None
                or self.trigger is not None
            ):
                raise ValueError(
                    "PRICE_RANGE entry requires only price_from and price_to"
                )
            if self.price_from > self.price_to:
                raise ValueError("entry range start must not exceed end")
        elif self.type is EntryType.TRIGGER and (
            not self.trigger
            or not self.trigger.strip()
            or any(v is not None for v in (self.price, self.price_from, self.price_to))
        ):
            raise ValueError("TRIGGER entry requires trigger and no direct price/range")

    @property
    def validation_price(self) -> Decimal | None:
        if self.type is EntryType.PRICE:
            return self.price
        if self.type is EntryType.PRICE_RANGE:
            return self.price_from
        return self.reference_price


@dataclass(frozen=True, slots=True)
class InvalidationPlan:
    stop_price: Decimal | None = None
    invalidation_rule: str | None = None
    rationale: str | None = None

    def __post_init__(self) -> None:
        _positive(self.stop_price, "stop price")
        rule = bool(self.invalidation_rule and self.invalidation_rule.strip())
        if self.stop_price is None and not rule:
            raise ValueError("stop price or invalidation rule is required")
        if self.stop_price is None and not (self.rationale and self.rationale.strip()):
            raise ValueError("rule-only invalidation requires rationale")


@dataclass(frozen=True, slots=True)
class Target:
    sequence: int
    price: Decimal
    rationale: str | None = None

    def __post_init__(self) -> None:
        if self.sequence <= 0:
            raise ValueError("target sequence must be positive")
        _positive(self.price, "target price")


@dataclass(frozen=True, slots=True)
class RiskAssumptions:
    """User-authored plan-risk notes; never position sizing or order quantity."""

    thesis_risk: str
    max_loss_assumption: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.thesis_risk.strip():
            raise ValueError("risk thesis is required")


@dataclass(frozen=True, slots=True)
class TradePlanVersion:
    id: UUID
    trade_plan_id: UUID
    version: int
    direction: TradeDirection
    thesis: str
    entry: EntryPlan
    invalidation: InvalidationPlan
    targets: tuple[Target, ...]
    risk_assumptions: RiskAssumptions
    status: TradePlanStatus
    created_at: datetime
    created_by: UUID
    previous_version_id: UUID | None = None
    change_reason: str | None = None

    def __post_init__(self) -> None:
        if self.version <= 0:
            raise ValueError("trade plan version must be positive")
        if self.direction is not TradeDirection.LONG:
            raise ValueError("TradePlan V1 is LONG-only")
        if not self.thesis.strip():
            raise ValueError("trade thesis is required")
        if not self.targets:
            raise ValueError("at least one target is required")
        expected = tuple(range(1, len(self.targets) + 1))
        actual = tuple(t.sequence for t in self.targets)
        if actual != expected:
            raise ValueError("target sequence must start at 1 and contain no gaps")
        if any(
            a.price >= b.price
            for a, b in zip(self.targets, self.targets[1:], strict=False)
        ):
            raise ValueError("LONG targets must be strictly increasing")
        anchor = self.entry.validation_price
        if anchor is not None:
            if (
                self.invalidation.stop_price is not None
                and self.invalidation.stop_price >= anchor
            ):
                raise ValueError("LONG stop price must be below entry validation price")
            if any(t.price <= anchor for t in self.targets):
                raise ValueError("LONG targets must be above entry validation price")
        if self.version == 1:
            if self.previous_version_id is not None or self.change_reason is not None:
                raise ValueError(
                    "initial trade plan version cannot reference a previous version"
                )
        else:
            if self.previous_version_id is None:
                raise ValueError("amendment version requires a previous version")
            if self.previous_version_id == self.id:
                raise ValueError(
                    "trade plan version cannot reference itself as previous version"
                )
            if not self.change_reason or not self.change_reason.strip():
                raise ValueError("amendment version requires a change reason")

    def ensure_ready_for_review(self) -> None:
        if self.status is not TradePlanStatus.DRAFT:
            raise ValueError("only DRAFT can be submitted for review")

    def ensure_approvable(self) -> None:
        if self.status is not TradePlanStatus.READY_FOR_REVIEW:
            raise ValueError("only READY_FOR_REVIEW can be approved")
