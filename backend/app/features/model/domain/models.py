"""Immutable domain snapshots for FT-013 controlled model governance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.features.model.domain.enums import (
    HypothesisStatus,
    ModelVersionStatus,
    ProposalStatus,
    ValidationConclusion,
    ValidationMethod,
)


def _required(value: str, field: str) -> None:
    if not value.strip():
        raise ValueError(f"{field} is required")


@dataclass(frozen=True, slots=True)
class GovernedModel:
    id: UUID
    workspace_id: UUID
    model_key: str
    name: str
    purpose: str
    created_at: datetime
    created_by: UUID

    def __post_init__(self) -> None:
        _required(self.model_key, "model_key")
        _required(self.name, "name")
        _required(self.purpose, "purpose")


@dataclass(frozen=True, slots=True)
class ModelVersion:
    id: UUID
    model_id: UUID
    version: int
    status: ModelVersionStatus
    definition: dict[str, object]
    change_summary: str
    created_at: datetime
    created_by: UUID
    previous_version_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("model version must be positive")
        if not self.definition:
            raise ValueError("model definition is required")
        _required(self.change_summary, "change_summary")
        if self.version == 1 and self.previous_version_id is not None:
            raise ValueError("initial model version must not have a predecessor")
        if self.version > 1 and self.previous_version_id is None:
            raise ValueError("later model version requires predecessor")
        if self.previous_version_id == self.id:
            raise ValueError("model version cannot reference itself")


@dataclass(frozen=True, slots=True)
class Hypothesis:
    id: UUID
    workspace_id: UUID
    title: str
    statement: str
    status: HypothesisStatus
    created_at: datetime
    created_by: UUID
    source_lesson_version_id: UUID | None = None

    def __post_init__(self) -> None:
        _required(self.title, "title")
        _required(self.statement, "statement")


@dataclass(frozen=True, slots=True)
class ModelChangeProposal:
    id: UUID
    workspace_id: UUID
    model_id: UUID
    base_model_version_id: UUID
    hypothesis_id: UUID
    status: ProposalStatus
    proposed_definition: dict[str, object]
    rationale: str
    created_at: datetime
    created_by: UUID

    def __post_init__(self) -> None:
        if not self.proposed_definition:
            raise ValueError("proposed_definition is required")
        _required(self.rationale, "rationale")


@dataclass(frozen=True, slots=True)
class ModelValidation:
    id: UUID
    proposal_id: UUID
    method: ValidationMethod
    evidence_cutoff_at: datetime
    conclusion: ValidationConclusion
    metrics: dict[str, object]
    notes: str | None
    created_at: datetime
    created_by: UUID

    def __post_init__(self) -> None:
        if self.method is not ValidationMethod.RETROSPECTIVE:
            raise ValueError("FT-013 V1 only supports retrospective validation")
        if self.evidence_cutoff_at > self.created_at:
            raise ValueError("evidence cutoff must not be in the future relative to validation")


@dataclass(frozen=True, slots=True)
class ModelApproval:
    id: UUID
    proposal_id: UUID | None
    model_version_id: UUID
    approved_at: datetime
    approved_by: UUID
    correlation_id: str | None = None
