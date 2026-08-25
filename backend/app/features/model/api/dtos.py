"""Pydantic contracts for FT-013 controlled model governance."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.features.model.domain.enums import (
    HypothesisStatus,
    ModelVersionStatus,
    ProposalStatus,
    ValidationConclusion,
    ValidationMethod,
)


class CreateModelRequest(BaseModel):
    model_key: str = Field(min_length=1, max_length=96)
    name: str = Field(min_length=1, max_length=240)
    purpose: str = Field(min_length=1)
    initial_definition: dict[str, object]


class ModelResponse(BaseModel):
    id: UUID
    model_key: str
    name: str
    purpose: str
    created_at: datetime
    created_by: UUID


class ModelVersionResponse(BaseModel):
    id: UUID
    model_id: UUID
    version: int
    status: ModelVersionStatus
    definition: dict[str, object]
    change_summary: str
    created_at: datetime
    created_by: UUID
    previous_version_id: UUID | None = None


class ModelDetailResponse(BaseModel):
    model: ModelResponse
    initial_version: ModelVersionResponse


class CreateHypothesisRequest(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    statement: str = Field(min_length=1)
    evidence_ids: list[UUID] = Field(default_factory=list)
    source_lesson_version_id: UUID | None = None


class HypothesisResponse(BaseModel):
    id: UUID
    title: str
    statement: str
    status: HypothesisStatus
    source_lesson_version_id: UUID | None = None
    created_at: datetime
    created_by: UUID


class CreateProposalRequest(BaseModel):
    model_id: UUID
    base_model_version_id: UUID
    hypothesis_id: UUID
    proposed_definition: dict[str, object]
    rationale: str = Field(min_length=1)


class ProposalResponse(BaseModel):
    id: UUID
    model_id: UUID
    base_model_version_id: UUID
    hypothesis_id: UUID
    status: ProposalStatus
    proposed_definition: dict[str, object]
    rationale: str
    created_at: datetime
    created_by: UUID


class ValidateProposalRequest(BaseModel):
    evidence_ids: list[UUID] = Field(min_length=1)
    evidence_cutoff_at: datetime
    conclusion: ValidationConclusion
    metrics: dict[str, object] = Field(default_factory=dict)
    notes: str | None = None


class ValidationResponse(BaseModel):
    id: UUID
    proposal_id: UUID
    method: ValidationMethod
    evidence_cutoff_at: datetime
    conclusion: ValidationConclusion
    metrics: dict[str, object]
    notes: str | None = None
    created_at: datetime
    created_by: UUID


class ApprovalResponse(BaseModel):
    id: UUID
    proposal_id: UUID | None
    model_version_id: UUID
    approved_at: datetime
    approved_by: UUID
    correlation_id: str | None = None


class ProposalApprovalResponse(BaseModel):
    model_version: ModelVersionResponse
    approval: ApprovalResponse
