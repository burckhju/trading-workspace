"""SQLAlchemy persistence models for immutable FT-008 selection snapshots."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ProductSelectionRunModel(Base):
    __tablename__ = "product_selection_runs"
    __table_args__ = (
        CheckConstraint(
            "trade_plan_version_status = 'APPROVED'", name="approved_trade_plan_version"
        ),
        Index(
            "ix_product_selection_runs_workspace_plan_version",
            "workspace_id",
            "trade_plan_version_id",
        ),
        Index("ix_product_selection_runs_underlying_evaluated", "underlying_id", "evaluated_at"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    trade_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("trade_plans.id", ondelete="RESTRICT"), nullable=False
    )
    trade_plan_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("trade_plan_versions.id", ondelete="RESTRICT"), nullable=False
    )
    trade_plan_version_status: Mapped[str] = mapped_column(String(32), nullable=False)
    underlying_id: Mapped[UUID] = mapped_column(
        ForeignKey("underlyings.id", ondelete="RESTRICT"), nullable=False
    )
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    universe_model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    universe_model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    eligibility_model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    eligibility_model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    evaluation_model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    evaluation_model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[UUID] = mapped_column(nullable=False)


class ProductEvaluationModel(Base):
    __tablename__ = "product_evaluations"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "warrant_terms_version_id",
            "warrant_listing_id",
            name="uq_product_evaluations_run_terms_listing",
        ),
        UniqueConstraint("id", "run_id", name="uq_product_evaluations_id_run"),
        Index("ix_product_evaluations_run_status", "run_id", "eligibility_status"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_selection_runs.id", ondelete="RESTRICT"), nullable=False
    )
    warrant_id: Mapped[UUID] = mapped_column(
        ForeignKey("warrants.id", ondelete="RESTRICT"), nullable=False
    )
    warrant_terms_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("warrant_terms_versions.id", ondelete="RESTRICT"), nullable=False
    )
    warrant_listing_id: Mapped[UUID] = mapped_column(
        ForeignKey("warrant_listings.id", ondelete="RESTRICT"), nullable=False
    )
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    eligibility_model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    eligibility_model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    evaluation_model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    evaluation_model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    eligibility_status: Mapped[str] = mapped_column(String(32), nullable=False)


class ProductEvaluationInputModel(Base):
    __tablename__ = "product_evaluation_inputs"
    __table_args__ = (
        UniqueConstraint(
            "product_evaluation_id",
            "sequence",
            name="uq_product_evaluation_inputs_evaluation_sequence",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    product_evaluation_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_evaluations.id", ondelete="RESTRICT"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str | None] = mapped_column(Text)
    availability: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    observed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    quality: Mapped[str | None] = mapped_column(String(100))


class ProductEvaluationCriterionModel(Base):
    __tablename__ = "product_evaluation_criteria"
    __table_args__ = (
        UniqueConstraint(
            "product_evaluation_id",
            "sequence",
            name="uq_product_evaluation_criteria_evaluation_sequence",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    product_evaluation_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_evaluations.id", ondelete="RESTRICT"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    criterion_id: Mapped[str] = mapped_column(String(120), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    actual_value: Mapped[str | None] = mapped_column(Text)
    expected_value: Mapped[str | None] = mapped_column(Text)
    data_availability: Mapped[str] = mapped_column(String(32), nullable=False)


class ProductEvaluationMetricModel(Base):
    __tablename__ = "product_evaluation_metrics"
    __table_args__ = (
        UniqueConstraint(
            "product_evaluation_id",
            "sequence",
            name="uq_product_evaluation_metrics_evaluation_sequence",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    product_evaluation_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_evaluations.id", ondelete="RESTRICT"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    metric_id: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(30, 12))
    unit: Mapped[str | None] = mapped_column(String(40))
    origin: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    formula_or_rule: Mapped[str | None] = mapped_column(Text)
    data_availability: Mapped[str] = mapped_column(String(32), nullable=False)


class ProductEvaluationReasonModel(Base):
    __tablename__ = "product_evaluation_reasons"
    __table_args__ = (
        UniqueConstraint(
            "product_evaluation_id",
            "sequence",
            name="uq_product_evaluation_reasons_evaluation_sequence",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    product_evaluation_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_evaluations.id", ondelete="RESTRICT"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class ProductUniverseOmissionModel(Base):
    __tablename__ = "product_universe_omissions"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "warrant_id",
            "reason",
            name="uq_product_universe_omissions_run_warrant_reason",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_selection_runs.id", ondelete="RESTRICT"), nullable=False
    )
    warrant_id: Mapped[UUID] = mapped_column(
        ForeignKey("warrants.id", ondelete="RESTRICT"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)


class ProductSelectionModel(Base):
    __tablename__ = "product_selections"
    __table_args__ = (
        UniqueConstraint("run_id", name="uq_product_selections_run"),
        ForeignKeyConstraint(
            ["product_evaluation_id", "run_id"],
            ["product_evaluations.id", "product_evaluations.run_id"],
            ondelete="RESTRICT",
            name="fk_product_selections_evaluation_same_run",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_selection_runs.id", ondelete="RESTRICT"), nullable=False
    )
    product_evaluation_id: Mapped[UUID] = mapped_column(nullable=False)
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    selected_by: Mapped[UUID] = mapped_column(nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)
