"""SQLAlchemy models for FT-013 controlled model governance."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class GovernedModelRecord(Base):
    __tablename__ = "governed_models"
    __table_args__ = (
        CheckConstraint("length(trim(model_key)) > 0", name="ck_governed_models_key_nonblank"),
        CheckConstraint("length(trim(name)) > 0", name="ck_governed_models_name_nonblank"),
        CheckConstraint("length(trim(purpose)) > 0", name="ck_governed_models_purpose_nonblank"),
        ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="RESTRICT",
            name="fk_governed_models_workspace",
        ),
        UniqueConstraint("workspace_id", "model_key", name="uq_governed_models_workspace_key"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    model_key: Mapped[str] = mapped_column(String(96), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    purpose: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)


class ModelVersionRecord(Base):
    __tablename__ = "governed_model_versions"
    __table_args__ = (
        CheckConstraint("version >= 1", name="ck_governed_model_versions_positive"),
        CheckConstraint(
            "status IN ('DRAFT','APPROVED')",
            name="ck_governed_model_versions_status_valid",
        ),
        CheckConstraint(
            "previous_version_id IS NULL OR previous_version_id <> id",
            name="ck_governed_model_versions_not_self_previous",
        ),
        ForeignKeyConstraint(
            ["model_id"], ["governed_models.id"], ondelete="RESTRICT",
            name="fk_governed_model_versions_model",
        ),
        ForeignKeyConstraint(
            ["previous_version_id"], ["governed_model_versions.id"], ondelete="RESTRICT",
            name="fk_governed_model_versions_previous",
        ),
        UniqueConstraint("model_id", "version", name="uq_governed_model_versions_model_version"),
        UniqueConstraint("previous_version_id", name="uq_governed_model_versions_previous"),
        Index("ix_governed_model_versions_model_status", "model_id", "status"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    model_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    version: Mapped[int] = mapped_column(Integer(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    definition: Mapped[dict[str, object]] = mapped_column(JSONB(), nullable=False)
    change_summary: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    previous_version_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)


class HypothesisRecord(Base):
    __tablename__ = "model_hypotheses"
    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="ck_model_hypotheses_title_nonblank"),
        CheckConstraint(
            "length(trim(statement)) > 0", name="ck_model_hypotheses_statement_nonblank"
        ),
        CheckConstraint(
            "status IN ('OPEN','PROPOSED','CLOSED')",
            name="ck_model_hypotheses_status_valid",
        ),
        ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="RESTRICT",
            name="fk_model_hypotheses_workspace",
        ),
        ForeignKeyConstraint(
            ["source_lesson_version_id"], ["lesson_versions.id"], ondelete="RESTRICT",
            name="fk_model_hypotheses_lesson_version",
        ),
        Index("ix_model_hypotheses_workspace_status", "workspace_id", "status"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    statement: Mapped[str] = mapped_column(Text(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    source_lesson_version_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)


class HypothesisEvidenceRecord(Base):
    __tablename__ = "model_hypothesis_evidence"
    __table_args__ = (
        ForeignKeyConstraint(
            ["hypothesis_id"], ["model_hypotheses.id"], ondelete="RESTRICT",
            name="fk_model_hypothesis_evidence_hypothesis",
        ),
        ForeignKeyConstraint(
            ["learning_evidence_id"], ["learning_evidence.id"], ondelete="RESTRICT",
            name="fk_model_hypothesis_evidence_evidence",
        ),
    )
    hypothesis_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    learning_evidence_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)


class ModelChangeProposalRecord(Base):
    __tablename__ = "model_change_proposals"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT','VALIDATED','APPROVED')",
            name="ck_model_change_proposals_status_valid",
        ),
        CheckConstraint(
            "length(trim(rationale)) > 0", name="ck_model_change_proposals_rationale_nonblank"
        ),
        ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="RESTRICT",
            name="fk_model_change_proposals_workspace",
        ),
        ForeignKeyConstraint(
            ["model_id"], ["governed_models.id"], ondelete="RESTRICT",
            name="fk_model_change_proposals_model",
        ),
        ForeignKeyConstraint(
            ["base_model_version_id"], ["governed_model_versions.id"], ondelete="RESTRICT",
            name="fk_model_change_proposals_base_version",
        ),
        ForeignKeyConstraint(
            ["hypothesis_id"], ["model_hypotheses.id"], ondelete="RESTRICT",
            name="fk_model_change_proposals_hypothesis",
        ),
        Index("ix_model_change_proposals_workspace_status", "workspace_id", "status"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    model_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    base_model_version_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    hypothesis_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    proposed_definition: Mapped[dict[str, object]] = mapped_column(JSONB(), nullable=False)
    rationale: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)


class ModelValidationRecord(Base):
    __tablename__ = "model_validations"
    __table_args__ = (
        CheckConstraint(
            "method = 'RETROSPECTIVE'",
            name="ck_model_validations_method_v1",
        ),
        CheckConstraint(
            "conclusion IN ('SUPPORTS','INCONCLUSIVE','CONTRADICTS')",
            name="ck_model_validations_conclusion_valid",
        ),
        CheckConstraint(
            "evidence_cutoff_at <= created_at",
            name="ck_model_validations_cutoff_not_after_created",
        ),
        ForeignKeyConstraint(
            ["proposal_id"], ["model_change_proposals.id"], ondelete="RESTRICT",
            name="fk_model_validations_proposal",
        ),
        Index("ix_model_validations_proposal_created", "proposal_id", "created_at"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    proposal_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    method: Mapped[str] = mapped_column(String(24), nullable=False)
    evidence_cutoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    conclusion: Mapped[str] = mapped_column(String(24), nullable=False)
    metrics: Mapped[dict[str, object]] = mapped_column(JSONB(), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)


class ModelValidationEvidenceRecord(Base):
    __tablename__ = "model_validation_evidence"
    __table_args__ = (
        ForeignKeyConstraint(
            ["validation_id"], ["model_validations.id"], ondelete="RESTRICT",
            name="fk_model_validation_evidence_validation",
        ),
        ForeignKeyConstraint(
            ["learning_evidence_id"], ["learning_evidence.id"], ondelete="RESTRICT",
            name="fk_model_validation_evidence_evidence",
        ),
    )
    validation_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    learning_evidence_id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)


class ModelApprovalRecord(Base):
    __tablename__ = "model_approvals"
    __table_args__ = (
        ForeignKeyConstraint(
            ["proposal_id"], ["model_change_proposals.id"], ondelete="RESTRICT",
            name="fk_model_approvals_proposal",
        ),
        ForeignKeyConstraint(
            ["model_version_id"], ["governed_model_versions.id"], ondelete="RESTRICT",
            name="fk_model_approvals_version",
        ),
        UniqueConstraint("proposal_id", name="uq_model_approvals_proposal"),
        UniqueConstraint("model_version_id", name="uq_model_approvals_version"),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    proposal_id: Mapped[UUID | None] = mapped_column(Uuid(), nullable=True)
    model_version_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
