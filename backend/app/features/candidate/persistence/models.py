"""SQLAlchemy persistence for FT-005 candidate snapshots and audit history."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class CandidateModel(Base):
    __tablename__ = "candidates"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "underlying_id", name="uq_candidates_workspace_underlying"
        ),
        Index("ix_candidates_workspace_status", "workspace_id", "status"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    underlying_id: Mapped[UUID] = mapped_column(
        ForeignKey("underlyings.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)


class CandidateEvaluationModel(Base):
    __tablename__ = "candidate_evaluations"
    __table_args__ = (
        UniqueConstraint(
            "candidate_id", "version", name="uq_candidate_evaluations_candidate_version"
        ),
        Index(
            "ix_candidate_evaluations_candidate_time", "candidate_id", "evaluated_at"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(30), nullable=False)
    qualification: Mapped[str] = mapped_column(String(30), nullable=False)
    quality_status: Mapped[str] = mapped_column(String(30), nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class CandidateEvaluationSourceModel(Base):
    __tablename__ = "candidate_evaluation_sources"
    __table_args__ = (
        UniqueConstraint(
            "evaluation_id", "role", name="uq_candidate_evaluation_sources_role"
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    evaluation_id: Mapped[UUID] = mapped_column(
        ForeignKey("candidate_evaluations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_id: Mapped[UUID] = mapped_column(nullable=False)
    source_version: Mapped[int] = mapped_column(Integer, nullable=False)
    model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[str] = mapped_column(String(30), nullable=False)


class CandidateCriterionModel(Base):
    __tablename__ = "candidate_criterion_results"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    evaluation_id: Mapped[UUID] = mapped_column(
        ForeignKey("candidate_evaluations.id", ondelete="CASCADE"), nullable=False
    )
    criterion_id: Mapped[str] = mapped_column(String(80), nullable=False)
    criterion_group: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    evaluation: Mapped[str] = mapped_column(String(30), nullable=False)
    source: Mapped[str] = mapped_column(String(150), nullable=False)
    actual_value: Mapped[str | None] = mapped_column(String(100))
    expected_value: Mapped[str | None] = mapped_column(String(100))
    numeric_value: Mapped[Decimal | None] = mapped_column(Numeric(30, 12))
    explanation: Mapped[str] = mapped_column(Text, nullable=False)


class CandidateEventModel(Base):
    __tablename__ = "candidate_events"
    __table_args__ = (
        Index("ix_candidate_events_candidate_time", "candidate_id", "occurred_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(40))
    to_status: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(200), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
