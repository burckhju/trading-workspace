"""REST DTOs for FT-011 Post Trade."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.features.post_trade.domain import (
    ExitReviewAssessment,
    ExitReviewCurrentness,
    ExitReviewStatus,
    PostTradeObservationStatus,
)


class ObservationResponse(BaseModel):
    id: UUID
    trade_id: UUID
    status: PostTradeObservationStatus
    underlying_listing_id: UUID
    target_observation_count: int
    available_observation_count: int
    missing_observation_count: int
    is_complete: bool
    started_at: datetime
    completed_at: datetime | None
    created_at: datetime


class ExitExecutionResponse(BaseModel):
    execution_id: UUID
    quantity: Decimal
    price_per_unit: Decimal
    executed_at: datetime


class ActualExitResponse(BaseModel):
    full_exit_at: datetime
    realized_gross_pnl: Decimal
    executions: list[ExitExecutionResponse]


class ObservationPointResponse(BaseModel):
    trading_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adjusted_close: Decimal | None
    quality_status: str | None


class ObservedExtremeResponse(BaseModel):
    trading_date: date
    value: Decimal


class LevelCrossingResponse(BaseModel):
    level: Decimal
    crossed: bool
    first_crossed_on: date | None


class CounterfactualEvidenceResponse(BaseModel):
    available_observation_count: int
    target_observation_count: int
    horizon_complete: bool
    points: list[ObservationPointResponse]
    highest_high: ObservedExtremeResponse | None
    lowest_low: ObservedExtremeResponse | None
    final_close: ObservedExtremeResponse | None
    target_crossings: list[LevelCrossingResponse]
    stop_crossing: LevelCrossingResponse | None


class ProductContextResponse(BaseModel):
    warrant_id: UUID
    underlying_id: UUID
    historical_warrant_terms_version_id: UUID | None
    maturity_date: date | None
    historical_underlying_listing_id: UUID | None


class PlanningContextResponse(BaseModel):
    trade_plan_id: UUID | None
    trade_plan_version_id: UUID | None
    original_stop: Decimal | None
    original_targets: list[Decimal]


class ManagementLevelResponse(BaseModel):
    event_id: UUID
    kind: str
    effective_at: datetime
    numeric_value: Decimal | None


class ObservationEvidenceResponse(BaseModel):
    observation_id: UUID
    trade_id: UUID
    product_context: ProductContextResponse | None
    planning_context: PlanningContextResponse
    management_levels: list[ManagementLevelResponse]
    actual_exit: ActualExitResponse
    counterfactual: CounterfactualEvidenceResponse


class ExitReviewDraftRequest(BaseModel):
    timing: ExitReviewAssessment
    process_adherence: ExitReviewAssessment
    risk_decision: ExitReviewAssessment
    overall_exit_decision: ExitReviewAssessment
    rationale: str = Field(min_length=1, max_length=8000)


class ExitReviewResponse(BaseModel):
    exit_review_id: UUID
    current_version_id: UUID
    version: int
    status: ExitReviewStatus
    currentness: ExitReviewCurrentness
    timing: ExitReviewAssessment | None
    process_adherence: ExitReviewAssessment | None
    risk_decision: ExitReviewAssessment | None
    overall_exit_decision: ExitReviewAssessment | None
    rationale: str | None
    created_at: datetime
    created_by: UUID
    finalized_at: datetime | None
    finalized_by: UUID | None
    supersedes_version_id: UUID | None
    stale_at: datetime | None
    stale_reason: str | None


class HandoffResponse(BaseModel):
    ready: bool
    reason: str
    post_trade_observation_id: UUID | None
    exit_review_id: UUID | None
    exit_review_version_id: UUID | None
