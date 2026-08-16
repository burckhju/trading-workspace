"""Immutable FT-008 Product Selection domain snapshots and value objects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.features.product_selection.domain.enums import (
    CriterionOutcome,
    DataAvailability,
    EligibilityStatus,
    MetricOrigin,
)
from app.features.trade_plan.domain.enums import TradePlanStatus


def _required_text(value: str, name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{name} is required")
    return normalized


@dataclass(frozen=True, slots=True)
class ModelReference:
    model_id: str
    model_version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_id", _required_text(self.model_id, "model_id"))
        object.__setattr__(
            self,
            "model_version",
            _required_text(self.model_version, "model_version"),
        )


@dataclass(frozen=True, slots=True)
class ProductSelectionRun:
    """Historical evaluation context for one exact approved TradePlanVersion."""

    id: UUID
    workspace_id: UUID
    trade_plan_id: UUID
    trade_plan_version_id: UUID
    trade_plan_version_status: TradePlanStatus
    underlying_id: UUID
    evaluated_at: datetime
    universe_model: ModelReference
    eligibility_model: ModelReference
    evaluation_model: ModelReference
    created_at: datetime
    created_by: UUID

    def __post_init__(self) -> None:
        if self.trade_plan_version_status is not TradePlanStatus.APPROVED:
            raise ValueError("ProductSelectionRun requires an APPROVED TradePlanVersion")


@dataclass(frozen=True, slots=True)
class EvaluationInput:
    name: str
    value: str | None
    availability: DataAvailability
    source: str
    observed_at: datetime | None = None
    quality: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required_text(self.name, "input name"))
        object.__setattr__(self, "source", _required_text(self.source, "input source"))
        if self.availability is DataAvailability.AVAILABLE and self.value is None:
            raise ValueError("AVAILABLE input requires a value")
        if (
            self.availability in {DataAvailability.MISSING, DataAvailability.NOT_APPLICABLE}
            and self.value is not None
        ):
            raise ValueError(f"{self.availability.value} input must not carry a value")


@dataclass(frozen=True, slots=True)
class CriterionResult:
    criterion_id: str
    outcome: CriterionOutcome
    explanation: str
    actual_value: str | None = None
    expected_value: str | None = None
    data_availability: DataAvailability = DataAvailability.AVAILABLE

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "criterion_id",
            _required_text(self.criterion_id, "criterion_id"),
        )
        object.__setattr__(
            self,
            "explanation",
            _required_text(self.explanation, "criterion explanation"),
        )
        if self.outcome is CriterionOutcome.NOT_EVALUABLE and self.data_availability not in {
            DataAvailability.MISSING,
            DataAvailability.INSUFFICIENT,
        }:
            raise ValueError("NOT_EVALUABLE criterion requires MISSING or INSUFFICIENT data")
        if self.outcome is CriterionOutcome.NOT_APPLICABLE and (
            self.data_availability is not DataAvailability.NOT_APPLICABLE
        ):
            raise ValueError("NOT_APPLICABLE criterion requires NOT_APPLICABLE data status")


@dataclass(frozen=True, slots=True)
class EvaluationMetric:
    metric_id: str
    value: Decimal | None
    unit: str | None
    origin: MetricOrigin
    source: str
    formula_or_rule: str | None = None
    data_availability: DataAvailability = DataAvailability.AVAILABLE

    def __post_init__(self) -> None:
        object.__setattr__(self, "metric_id", _required_text(self.metric_id, "metric_id"))
        object.__setattr__(self, "source", _required_text(self.source, "metric source"))
        if self.data_availability is DataAvailability.AVAILABLE and self.value is None:
            raise ValueError("AVAILABLE metric requires a value")
        if (
            self.data_availability in {DataAvailability.MISSING, DataAvailability.NOT_APPLICABLE}
            and self.value is not None
        ):
            raise ValueError(f"{self.data_availability.value} metric must not carry a value")
        if (
            self.origin is MetricOrigin.CALCULATED
            and self.data_availability is DataAvailability.AVAILABLE
            and (not self.formula_or_rule or not self.formula_or_rule.strip())
        ):
            raise ValueError("calculated metric requires formula_or_rule")


@dataclass(frozen=True, slots=True)
class ProductEvaluation:
    """System result for one historical Warrant + Terms + Listing context."""

    id: UUID
    run_id: UUID
    warrant_id: UUID
    warrant_terms_version_id: UUID
    warrant_listing_id: UUID
    evaluated_at: datetime
    eligibility_model: ModelReference
    evaluation_model: ModelReference
    inputs: tuple[EvaluationInput, ...]
    criteria: tuple[CriterionResult, ...]
    metrics: tuple[EvaluationMetric, ...]
    eligibility_status: EligibilityStatus
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.criteria:
            raise ValueError("ProductEvaluation requires at least one criterion result")
        if self.eligibility_status is EligibilityStatus.INELIGIBLE and not any(
            criterion.outcome is CriterionOutcome.NOT_FULFILLED for criterion in self.criteria
        ):
            raise ValueError("INELIGIBLE evaluation requires a failed criterion")
        if self.eligibility_status is EligibilityStatus.NOT_EVALUABLE and not any(
            criterion.outcome is CriterionOutcome.NOT_EVALUABLE for criterion in self.criteria
        ):
            raise ValueError("NOT_EVALUABLE evaluation requires a non-evaluable criterion")
        normalized_reasons = tuple(reason.strip() for reason in self.reasons if reason.strip())
        if self.eligibility_status is not EligibilityStatus.ELIGIBLE and not normalized_reasons:
            raise ValueError("non-eligible evaluation requires at least one reason")
        object.__setattr__(self, "reasons", normalized_reasons)


@dataclass(frozen=True, slots=True)
class ProductSelection:
    """Explicit user decision selecting one ProductEvaluation from the same run."""

    id: UUID
    run_id: UUID
    product_evaluation_id: UUID
    selected_at: datetime
    selected_by: UUID
    rationale: str | None = None

    def __post_init__(self) -> None:
        if self.rationale is not None:
            normalized = self.rationale.strip()
            object.__setattr__(self, "rationale", normalized or None)

    @classmethod
    def from_user_decision(
        cls,
        *,
        id: UUID,
        run: ProductSelectionRun,
        evaluation: ProductEvaluation,
        selected_at: datetime,
        selected_by: UUID,
        rationale: str | None = None,
    ) -> ProductSelection:
        if evaluation.run_id != run.id:
            raise ValueError("selected ProductEvaluation must belong to ProductSelectionRun")
        if evaluation.eligibility_status is not EligibilityStatus.ELIGIBLE:
            raise ValueError("V1 ProductSelection requires an ELIGIBLE ProductEvaluation")
        return cls(
            id=id,
            run_id=run.id,
            product_evaluation_id=evaluation.id,
            selected_at=selected_at,
            selected_by=selected_by,
            rationale=rationale,
        )
