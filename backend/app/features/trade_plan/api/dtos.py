"""REST contracts for FT-007 TradePlan."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.features.trade_plan.domain.enums import (
    EntryType,
    TradePlanOriginType,
    TradePlanStatus,
)


class EntryPlanRequest(BaseModel):
    type: EntryType
    currency: str = Field(min_length=1, max_length=3)
    price: Decimal | None = None
    price_from: Decimal | None = None
    price_to: Decimal | None = None
    trigger: str | None = Field(default=None, max_length=2000)
    reference_price: Decimal | None = None
    valid_until: datetime | None = None
    rationale: str | None = Field(default=None, max_length=4000)


class InvalidationPlanRequest(BaseModel):
    stop_price: Decimal | None = None
    invalidation_rule: str | None = Field(default=None, max_length=4000)
    rationale: str | None = Field(default=None, max_length=4000)


class TargetRequest(BaseModel):
    sequence: int = Field(gt=0)
    price: Decimal = Field(gt=0)
    rationale: str | None = Field(default=None, max_length=4000)


class RiskAssumptionsRequest(BaseModel):
    thesis_risk: str = Field(min_length=1, max_length=8000)
    max_loss_assumption: str | None = Field(default=None, max_length=4000)
    notes: str | None = Field(default=None, max_length=8000)


class TradePlanContentRequest(BaseModel):
    thesis: str = Field(min_length=1, max_length=12000)
    entry: EntryPlanRequest
    invalidation: InvalidationPlanRequest
    targets: list[TargetRequest] = Field(min_length=1)
    risk_assumptions: RiskAssumptionsRequest


class CreateTradePlanRequest(TradePlanContentRequest):
    origin_type: TradePlanOriginType
    underlying_id: UUID | None = None
    candidate_id: UUID | None = None
    candidate_evaluation_id: UUID | None = None

    @model_validator(mode="after")
    def validate_origin(self) -> CreateTradePlanRequest:
        if self.origin_type is TradePlanOriginType.MANUAL:
            if self.underlying_id is None:
                raise ValueError("manual trade plan requires underlying_id")
            if (
                self.candidate_id is not None
                or self.candidate_evaluation_id is not None
            ):
                raise ValueError(
                    "manual trade plan cannot contain candidate provenance"
                )
        else:
            if self.candidate_id is None or self.candidate_evaluation_id is None:
                raise ValueError(
                    "candidate-originated trade plan requires candidate_id and "
                    "candidate_evaluation_id"
                )
            if self.underlying_id is not None:
                raise ValueError(
                    "candidate-originated trade plan resolves underlying from CandidateEvaluation"
                )
        return self


class AmendTradePlanRequest(TradePlanContentRequest):
    change_reason: str = Field(min_length=1, max_length=4000)


class LifecycleReasonRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=4000)


class EntryPlanResponse(BaseModel):
    type: EntryType
    currency: str
    price: Decimal | None
    price_from: Decimal | None
    price_to: Decimal | None
    trigger: str | None
    reference_price: Decimal | None
    valid_until: datetime | None
    rationale: str | None


class InvalidationPlanResponse(BaseModel):
    stop_price: Decimal | None
    invalidation_rule: str | None
    rationale: str | None


class TargetResponse(BaseModel):
    sequence: int
    price: Decimal
    rationale: str | None


class RiskAssumptionsResponse(BaseModel):
    thesis_risk: str
    max_loss_assumption: str | None
    notes: str | None


class TradePlanSummaryResponse(BaseModel):
    id: UUID
    underlying_id: UUID
    origin_type: TradePlanOriginType
    candidate_id: UUID | None
    candidate_evaluation_id: UUID | None
    created_at: datetime
    created_by: UUID


class CandidateEvaluationSourceResponse(BaseModel):
    role: str
    source_type: str
    source_id: UUID
    source_version: int
    model_id: str
    model_version: str


class CandidateEvaluationProvenanceResponse(BaseModel):
    candidate_id: UUID
    evaluation_id: UUID
    evaluation_version: int
    direction: str
    model_id: str
    model_version: str
    qualification: str
    quality_status: str
    evaluated_at: datetime
    sources: list[CandidateEvaluationSourceResponse]


class ApprovalResponse(BaseModel):
    approval_id: UUID
    trade_plan_version_id: UUID
    version: int
    actor: str
    approved_at: datetime
    correlation_id: str | None


class LifecycleEventResponse(BaseModel):
    id: UUID
    event_type: str
    from_status: str | None
    to_status: str
    reason: str | None
    actor: str
    correlation_id: str | None
    occurred_at: datetime


class TradePlanVersionResponse(BaseModel):
    id: UUID
    trade_plan_id: UUID
    version: int
    direction: str
    thesis: str
    entry: EntryPlanResponse
    invalidation: InvalidationPlanResponse
    targets: list[TargetResponse]
    risk_assumptions: RiskAssumptionsResponse
    status: TradePlanStatus
    created_at: datetime
    created_by: UUID
    previous_version_id: UUID | None
    change_reason: str | None
    candidate_evaluation: CandidateEvaluationProvenanceResponse | None = None
    approval: ApprovalResponse | None = None
    events: list[LifecycleEventResponse] = Field(default_factory=list)


class TradePlanDetailResponse(BaseModel):
    plan: TradePlanSummaryResponse
    latest_version: TradePlanVersionResponse
