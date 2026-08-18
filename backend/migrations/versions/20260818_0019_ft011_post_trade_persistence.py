"""FT-011 post-trade observation and exit-review persistence.

Revision ID: 20260818_0019
Revises: 20260817_0018
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260818_0019"
down_revision: str | None = "20260817_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "post_trade_observations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("trade_id", sa.Uuid(), nullable=False),
        sa.Column("underlying_listing_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("target_observation_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_by", sa.Uuid(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'COMPLETED')",
            name="ck_post_trade_observations_status_valid",
        ),
        sa.CheckConstraint(
            "target_observation_count = 20",
            name="ck_post_trade_observations_target_observation_count_v1",
        ),
        sa.CheckConstraint(
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
            name="ck_post_trade_observations_lifecycle_consistent",
        ),
        sa.CheckConstraint(
            "created_at >= started_at",
            name="ck_post_trade_observations_created_not_before_started",
        ),
        sa.CheckConstraint(
            "updated_at >= created_at",
            name="ck_post_trade_observations_updated_not_before_created",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_post_trade_observations_workspace",
        ),
        sa.ForeignKeyConstraint(
            ["trade_id"],
            ["trades.id"],
            ondelete="RESTRICT",
            name="fk_post_trade_observations_trade",
        ),
        sa.ForeignKeyConstraint(
            ["underlying_listing_id"],
            ["listings.id"],
            ondelete="RESTRICT",
            name="fk_post_trade_observations_underlying_listing",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trade_id",
            name="uq_post_trade_observations_trade",
        ),
    )

    op.create_index(
        "ix_post_trade_observations_workspace_status",
        "post_trade_observations",
        ["workspace_id", "status"],
    )

    op.create_table(
        "exit_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column(
            "post_trade_observation_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_exit_reviews_workspace",
        ),
        sa.ForeignKeyConstraint(
            ["post_trade_observation_id"],
            ["post_trade_observations.id"],
            ondelete="RESTRICT",
            name="fk_exit_reviews_observation",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "post_trade_observation_id",
            name="uq_exit_reviews_observation",
        ),
    )

    op.create_index(
        "ix_exit_reviews_workspace_created",
        "exit_reviews",
        ["workspace_id", "created_at"],
    )

    op.create_table(
        "exit_review_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("exit_review_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("currentness", sa.String(length=16), nullable=False),
        sa.Column("timing", sa.String(length=24), nullable=True),
        sa.Column("process_adherence", sa.String(length=24), nullable=True),
        sa.Column("risk_decision", sa.String(length=24), nullable=True),
        sa.Column(
            "overall_exit_decision",
            sa.String(length=24),
            nullable=True,
        ),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("input_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finalized_by", sa.Uuid(), nullable=True),
        sa.Column("supersedes_version_id", sa.Uuid(), nullable=True),
        sa.Column("stale_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stale_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_exit_review_versions_version_positive",
        ),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'FINALIZED')",
            name="ck_exit_review_versions_status_valid",
        ),
        sa.CheckConstraint(
            "currentness IN ('CURRENT', 'STALE')",
            name="ck_exit_review_versions_currentness_valid",
        ),
        sa.CheckConstraint(
            """
            timing IS NULL
            OR timing IN (
                'GOOD',
                'ACCEPTABLE',
                'IMPROVABLE',
                'NOT_ASSESSABLE'
            )
            """,
            name="ck_exit_review_versions_timing_valid",
        ),
        sa.CheckConstraint(
            """
            process_adherence IS NULL
            OR process_adherence IN (
                'GOOD',
                'ACCEPTABLE',
                'IMPROVABLE',
                'NOT_ASSESSABLE'
            )
            """,
            name="ck_exit_review_versions_process_adherence_valid",
        ),
        sa.CheckConstraint(
            """
            risk_decision IS NULL
            OR risk_decision IN (
                'GOOD',
                'ACCEPTABLE',
                'IMPROVABLE',
                'NOT_ASSESSABLE'
            )
            """,
            name="ck_exit_review_versions_risk_decision_valid",
        ),
        sa.CheckConstraint(
            """
            overall_exit_decision IS NULL
            OR overall_exit_decision IN (
                'GOOD',
                'ACCEPTABLE',
                'IMPROVABLE',
                'NOT_ASSESSABLE'
            )
            """,
            name="ck_exit_review_versions_overall_exit_decision_valid",
        ),
        sa.CheckConstraint(
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
            name="ck_exit_review_versions_lifecycle_consistent",
        ),
        sa.CheckConstraint(
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
            name="ck_exit_review_versions_currentness_consistent",
        ),
        sa.CheckConstraint(
            """
            supersedes_version_id IS NULL
            OR supersedes_version_id <> id
            """,
            name="ck_exit_review_versions_not_self_superseding",
        ),
        sa.ForeignKeyConstraint(
            ["exit_review_id"],
            ["exit_reviews.id"],
            ondelete="RESTRICT",
            name="fk_exit_review_versions_review",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_version_id"],
            ["exit_review_versions.id"],
            ondelete="RESTRICT",
            name="fk_exit_review_versions_supersedes",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "exit_review_id",
            "version",
            name="uq_exit_review_versions_review_version",
        ),
        sa.UniqueConstraint(
            "supersedes_version_id",
            name="uq_exit_review_versions_supersedes",
        ),
    )

    op.create_index(
        "ix_exit_review_versions_review_version",
        "exit_review_versions",
        ["exit_review_id", "version"],
    )

    op.create_index(
        "uq_exit_review_versions_open_draft",
        "exit_review_versions",
        ["exit_review_id"],
        unique=True,
        postgresql_where=sa.text("status = 'DRAFT'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_exit_review_versions_open_draft",
        table_name="exit_review_versions",
    )
    op.drop_index(
        "ix_exit_review_versions_review_version",
        table_name="exit_review_versions",
    )
    op.drop_table("exit_review_versions")

    op.drop_index(
        "ix_exit_reviews_workspace_created",
        table_name="exit_reviews",
    )
    op.drop_table("exit_reviews")

    op.drop_index(
        "ix_post_trade_observations_workspace_status",
        table_name="post_trade_observations",
    )
    op.drop_table("post_trade_observations")
