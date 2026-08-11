"""REST contracts for top-down candidates."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.features.candidate.domain.enums import CandidateStatus


class CreateCandidateRequest(BaseModel):
    underlying_id: UUID


class CandidateResponse(BaseModel):
    id: UUID
    underlying_id: UUID
    status: str
    created_at: datetime
    created_by: str


class StoredAnalysisReferenceRequest(BaseModel):
    analysis_id: UUID
    version: int = Field(gt=0)


class AutoEvaluateCandidateRequest(BaseModel):
    as_of: datetime | None = None


class EvaluateCandidateRequest(BaseModel):
    market_source: StoredAnalysisReferenceRequest
    sector_source: StoredAnalysisReferenceRequest
    underlying_source: StoredAnalysisReferenceRequest


class CandidateEvaluationResponse(BaseModel):
    id: UUID
    version: int
    direction: str
    model_id: str
    model_version: str
    qualification: str
    quality_status: str
    warnings: list[str]
    evaluated_at: datetime


class CandidateCriterionResponse(BaseModel):
    criterion_id: str
    group: str
    severity: str
    evaluation: str
    source: str
    actual_value: str | None
    expected_value: str | None
    numeric_value: str | None
    explanation: str


class CandidateEvaluationDetailResponse(CandidateEvaluationResponse):
    criteria: list[CandidateCriterionResponse]


class ChangeCandidateStatusRequest(BaseModel):
    status: CandidateStatus
    reason: str | None = Field(default=None, max_length=1000)


class CandidateLiveWorkflowStepResponse(BaseModel):
    code: str
    label: str
    status: str
    detail: str
    action: str | None
    resource_id: UUID | None
    action_params: dict[str, str] | None = None


class CandidateLiveWorkflowResponse(BaseModel):
    candidate_id: UUID
    underlying_id: UUID
    as_of: datetime
    ready: bool
    can_evaluate: bool
    next_action: str | None
    steps: list[CandidateLiveWorkflowStepResponse]
