"""SQLAlchemy persistence models for FT-007 TradePlan identity and immutable versions."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
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


class TradePlanModel(Base):
    __tablename__ = "trade_plans"
    __table_args__ = (
        CheckConstraint(
            "(origin_type = 'MANUAL' AND candidate_id IS NULL AND candidate_evaluation_id IS NULL) "
            "OR (origin_type = 'CANDIDATE_EVALUATION' AND candidate_id IS NOT NULL "
            "AND candidate_evaluation_id IS NOT NULL)",
            name="trade_plan_origin_provenance",
        ),
        Index("ix_trade_plans_workspace_underlying", "workspace_id", "underlying_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="RESTRICT"), nullable=False
    )
    underlying_id: Mapped[UUID] = mapped_column(
        ForeignKey("underlyings.id", ondelete="RESTRICT"), nullable=False
    )
    origin_type: Mapped[str] = mapped_column(String(40), nullable=False)
    candidate_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("candidates.id", ondelete="RESTRICT")
    )
    candidate_evaluation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("candidate_evaluations.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)


class TradePlanVersionModel(Base):
    """One content snapshot. Lifecycle/approval history is append-only in event tables."""

    __tablename__ = "trade_plan_versions"
    __table_args__ = (
        UniqueConstraint(
            "trade_plan_id", "version", name="uq_trade_plan_versions_plan_version"
        ),
        CheckConstraint("version > 0", name="trade_plan_version_positive"),
        CheckConstraint("direction = 'LONG'", name="trade_plan_version_long_only"),
        Index("ix_trade_plan_versions_plan_status", "trade_plan_id", "status"),
        Index("ix_trade_plan_versions_plan_created", "trade_plan_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    trade_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("trade_plans.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    thesis: Mapped[str] = mapped_column(Text, nullable=False)

    entry_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entry_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    entry_price: Mapped[Decimal | None] = mapped_column(Numeric(24, 10))
    entry_price_from: Mapped[Decimal | None] = mapped_column(Numeric(24, 10))
    entry_price_to: Mapped[Decimal | None] = mapped_column(Numeric(24, 10))
    entry_trigger: Mapped[str | None] = mapped_column(Text)
    entry_reference_price: Mapped[Decimal | None] = mapped_column(Numeric(24, 10))
    entry_valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    entry_rationale: Mapped[str | None] = mapped_column(Text)

    stop_price: Mapped[Decimal | None] = mapped_column(Numeric(24, 10))
    invalidation_rule: Mapped[str | None] = mapped_column(Text)
    invalidation_rationale: Mapped[str | None] = mapped_column(Text)

    risk_thesis: Mapped[str] = mapped_column(Text, nullable=False)
    risk_max_loss_assumption: Mapped[str | None] = mapped_column(Text)
    risk_notes: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    previous_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("trade_plan_versions.id", ondelete="RESTRICT")
    )
    change_reason: Mapped[str | None] = mapped_column(Text)


class TradePlanTargetModel(Base):
    __tablename__ = "trade_plan_targets"
    __table_args__ = (
        UniqueConstraint(
            "trade_plan_version_id",
            "sequence",
            name="uq_trade_plan_targets_version_sequence",
        ),
        CheckConstraint("sequence > 0", name="trade_plan_target_sequence_positive"),
        CheckConstraint("price > 0", name="trade_plan_target_price_positive"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    trade_plan_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("trade_plan_versions.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)


class TradePlanEventModel(Base):
    """Append-only lifecycle/audit event for a concrete TradePlanVersion."""

    __tablename__ = "trade_plan_events"
    __table_args__ = (
        Index("ix_trade_plan_events_plan_occurred", "trade_plan_id", "occurred_at"),
        Index(
            "ix_trade_plan_events_version_occurred",
            "trade_plan_version_id",
            "occurred_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    trade_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("trade_plans.id", ondelete="CASCADE"), nullable=False
    )
    trade_plan_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("trade_plan_versions.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(40))
    to_status: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String(200), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(100))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class TradePlanApprovalModel(Base):
    """Append-only proof of explicit user approval for exactly one immutable version."""

    __tablename__ = "trade_plan_approvals"
    __table_args__ = (
        UniqueConstraint(
            "trade_plan_version_id", name="uq_trade_plan_approvals_version"
        ),
        Index("ix_trade_plan_approvals_plan_time", "trade_plan_id", "approved_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    trade_plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("trade_plans.id", ondelete="CASCADE"), nullable=False
    )
    trade_plan_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("trade_plan_versions.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    actor: Mapped[str] = mapped_column(String(200), nullable=False)
    approved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    correlation_id: Mapped[str | None] = mapped_column(String(100))
