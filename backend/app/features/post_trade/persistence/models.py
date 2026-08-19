"""SQLAlchemy persistence models for FT-011 Post Trade."""

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
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PostTradeObservationModel(Base):
    __tablename__ = "post_trade_observations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'COMPLETED')",
            name="status_valid",
        ),
        CheckConstraint(
            "target_observation_count = 20",
            name="target_observation_count_v1",
        ),
        CheckConstraint(
            """
            (
                status = 'ACTIVE'
                AND completed_at IS NULL
            )
            OR
            (
                status = 'COMPLETED'
                AND completed_at IS NOT NULL
                AND completed_at >= started_at
            )
            """,
            name="lifecycle_consistent",
        ),
        CheckConstraint(
            "created_at >= started_at",
            name="created_not_before_started",
        ),
        CheckConstraint(
            "updated_at >= created_at",
            name="updated_not_before_created",
        ),
        ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_post_trade_observations_workspace",
        ),
        ForeignKeyConstraint(
            ["trade_id"],
            ["trades.id"],
            ondelete="RESTRICT",
            name="fk_post_trade_observations_trade",
        ),
        ForeignKeyConstraint(
            ["underlying_listing_id"],
            ["listings.id"],
            ondelete="RESTRICT",
            name="fk_post_trade_observations_underlying_listing",
        ),
        UniqueConstraint(
            "trade_id",
            name="uq_post_trade_observations_trade",
        ),
        Index(
            "ix_post_trade_observations_workspace_status",
            "workspace_id",
            "status",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    trade_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    underlying_listing_id: Mapped[UUID] = mapped_column(
        Uuid(),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(String(16), nullable=False)
    target_observation_count: Mapped[int] = mapped_column(
        Integer(),
        nullable=False,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    started_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )


class ExitReviewModel(Base):
    __tablename__ = "exit_reviews"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_exit_reviews_workspace",
        ),
        ForeignKeyConstraint(
            ["post_trade_observation_id"],
            ["post_trade_observations.id"],
            ondelete="RESTRICT",
            name="fk_exit_reviews_observation",
        ),
        UniqueConstraint(
            "post_trade_observation_id",
            name="uq_exit_reviews_observation",
        ),
        Index(
            "ix_exit_reviews_workspace_created",
            "workspace_id",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)
    post_trade_observation_id: Mapped[UUID] = mapped_column(
        Uuid(),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)


class ExitReviewVersionModel(Base):
    __tablename__ = "exit_review_versions"
    __table_args__ = (
        CheckConstraint(
            "version >= 1",
            name="version_positive",
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'FINALIZED')",
            name="status_valid",
        ),
        CheckConstraint(
            "currentness IN ('CURRENT', 'STALE')",
            name="currentness_valid",
        ),
        CheckConstraint(
            """
            timing IS NULL
            OR timing IN (
                'GOOD',
                'ACCEPTABLE',
                'IMPROVABLE',
                'NOT_ASSESSABLE'
            )
            """,
            name="timing_valid",
        ),
        CheckConstraint(
            """
            process_adherence IS NULL
            OR process_adherence IN (
                'GOOD',
                'ACCEPTABLE',
                'IMPROVABLE',
                'NOT_ASSESSABLE'
            )
            """,
            name="process_adherence_valid",
        ),
        CheckConstraint(
            """
            risk_decision IS NULL
            OR risk_decision IN (
                'GOOD',
                'ACCEPTABLE',
                'IMPROVABLE',
                'NOT_ASSESSABLE'
            )
            """,
            name="risk_decision_valid",
        ),
        CheckConstraint(
            """
            overall_exit_decision IS NULL
            OR overall_exit_decision IN (
                'GOOD',
                'ACCEPTABLE',
                'IMPROVABLE',
                'NOT_ASSESSABLE'
            )
            """,
            name="overall_exit_decision_valid",
        ),
        CheckConstraint(
            """
            (
                status = 'DRAFT'
                AND currentness = 'CURRENT'
                AND input_fingerprint IS NULL
                AND finalized_at IS NULL
                AND finalized_by IS NULL
                AND stale_at IS NULL
                AND stale_reason IS NULL
            )
            OR
            (
                status = 'FINALIZED'
                AND timing IS NOT NULL
                AND process_adherence IS NOT NULL
                AND risk_decision IS NOT NULL
                AND overall_exit_decision IS NOT NULL
                AND rationale IS NOT NULL
                AND length(trim(rationale)) > 0
                AND input_fingerprint IS NOT NULL
                AND length(trim(input_fingerprint)) > 0
                AND finalized_at IS NOT NULL
                AND finalized_by IS NOT NULL
                AND finalized_at >= created_at
            )
            """,
            name="lifecycle_consistent",
        ),
        CheckConstraint(
            """
            (
                currentness = 'CURRENT'
                AND stale_at IS NULL
                AND stale_reason IS NULL
            )
            OR
            (
                currentness = 'STALE'
                AND status = 'FINALIZED'
                AND stale_at IS NOT NULL
                AND stale_reason IS NOT NULL
                AND length(trim(stale_reason)) > 0
                AND stale_at >= finalized_at
            )
            """,
            name="currentness_consistent",
        ),
        CheckConstraint(
            "supersedes_version_id IS NULL OR supersedes_version_id <> id",
            name="not_self_superseding",
        ),
        ForeignKeyConstraint(
            ["exit_review_id"],
            ["exit_reviews.id"],
            ondelete="RESTRICT",
            name="fk_exit_review_versions_review",
        ),
        ForeignKeyConstraint(
            ["supersedes_version_id"],
            ["exit_review_versions.id"],
            ondelete="RESTRICT",
            name="fk_exit_review_versions_supersedes",
        ),
        UniqueConstraint(
            "exit_review_id",
            "version",
            name="uq_exit_review_versions_review_version",
        ),
        UniqueConstraint(
            "supersedes_version_id",
            name="uq_exit_review_versions_supersedes",
        ),
        Index(
            "ix_exit_review_versions_review_version",
            "exit_review_id",
            "version",
        ),
        Index(
            "uq_exit_review_versions_open_draft",
            "exit_review_id",
            unique=True,
            postgresql_where=text("status = 'DRAFT'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    exit_review_id: Mapped[UUID] = mapped_column(Uuid(), nullable=False)

    version: Mapped[int] = mapped_column(Integer(), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    currentness: Mapped[str] = mapped_column(String(16), nullable=False)

    timing: Mapped[str | None] = mapped_column(String(24), nullable=True)
    process_adherence: Mapped[str | None] = mapped_column(
        String(24),
        nullable=True,
    )
    risk_decision: Mapped[str | None] = mapped_column(
        String(24),
        nullable=True,
    )
    overall_exit_decision: Mapped[str | None] = mapped_column(
        String(24),
        nullable=True,
    )

    rationale: Mapped[str | None] = mapped_column(Text(), nullable=True)

    input_fingerprint: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    created_by: Mapped[UUID] = mapped_column(Uuid(), nullable=False)

    finalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finalized_by: Mapped[UUID | None] = mapped_column(
        Uuid(),
        nullable=True,
    )

    supersedes_version_id: Mapped[UUID | None] = mapped_column(
        Uuid(),
        nullable=True,
    )

    stale_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    stale_reason: Mapped[str | None] = mapped_column(
        Text(),
        nullable=True,
    )
