"""REST contracts for FT-008 Product Selection."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.features.product_selection.domain.enums import (
    CriterionOutcome,
    DataAvailability,
    EligibilityStatus,
    MetricOrigin,
)
from app.features.trade_plan.domain.enums import TradePlanStatus


class StartProductSelectionRunRequest(BaseModel):
    trade_plan_id: UUID
    trade_plan_version_id: UUID
    evaluated_at: datetime | None = None


class SelectProductRequest(BaseModel):
    product_evaluation_id: UUID
    rationale: str | None = Field(default=None, max_length=2000)


class ModelReferenceResponse(BaseModel):
    model_id: str
    model_version: str


class EvaluationInputResponse(BaseModel):
    name: str
    value: str | None
    availability: DataAvailability
    source: str
    observed_at: datetime | None
    quality: str | None


class CriterionResultResponse(BaseModel):
    criterion_id: str
    outcome: CriterionOutcome
    explanation: str
    actual_value: str | None
    expected_value: str | None
    data_availability: DataAvailability


class EvaluationMetricResponse(BaseModel):
    metric_id: str
    value: Decimal | None
    unit: str | None
    origin: MetricOrigin
    source: str
    formula_or_rule: str | None
    data_availability: DataAvailability


class ProductEvaluationResponse(BaseModel):
    id: UUID
    run_id: UUID
    warrant_id: UUID
    warrant_terms_version_id: UUID
    warrant_listing_id: UUID
    evaluated_at: datetime
    eligibility_model: ModelReferenceResponse
    evaluation_model: ModelReferenceResponse
    inputs: list[EvaluationInputResponse]
    criteria: list[CriterionResultResponse]
    metrics: list[EvaluationMetricResponse]
    eligibility_status: EligibilityStatus
    reasons: list[str]


class UniverseOmissionResponse(BaseModel):
    warrant_id: UUID
    reason: str
    explanation: str


class ProductSelectionResponse(BaseModel):
    id: UUID
    run_id: UUID
    product_evaluation_id: UUID
    selected_at: datetime
    selected_by: UUID
    rationale: str | None


class ProductSelectionRunSummaryResponse(BaseModel):
    id: UUID
    trade_plan_id: UUID
    trade_plan_version_id: UUID
    trade_plan_version_status: TradePlanStatus
    underlying_id: UUID
    evaluated_at: datetime
    universe_model: ModelReferenceResponse
    eligibility_model: ModelReferenceResponse
    evaluation_model: ModelReferenceResponse
    created_at: datetime
    created_by: UUID


class ProductSelectionRunDetailResponse(BaseModel):
    run: ProductSelectionRunSummaryResponse
    evaluations: list[ProductEvaluationResponse] = Field(default_factory=list)
    universe_omissions: list[UniverseOmissionResponse] = Field(default_factory=list)
    selection: ProductSelectionResponse | None = None
