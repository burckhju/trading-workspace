"""Create FT-007 TradePlan persistence.

Revision ID: 20260811_0008
Revises: 20260810_0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260811_0008"
down_revision: str | None = "20260810_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trade_plans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("underlying_id", sa.Uuid(), nullable=False),
        sa.Column("origin_type", sa.String(40), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=True),
        sa.Column("candidate_evaluation_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.CheckConstraint(
            "(origin_type = 'MANUAL' AND candidate_id IS NULL AND candidate_evaluation_id IS NULL) "
            "OR (origin_type = 'CANDIDATE_EVALUATION' AND candidate_id IS NOT NULL "
            "AND candidate_evaluation_id IS NOT NULL)",
            name="ck_trade_plans_trade_plan_origin_provenance",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["underlying_id"], ["underlyings.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["candidate_id"], ["candidates.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["candidate_evaluation_id"], ["candidate_evaluations.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_trade_plans_workspace_underlying", "trade_plans", ["workspace_id", "underlying_id"]
    )

    op.create_table(
        "trade_plan_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trade_plan_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("thesis", sa.Text(), nullable=False),
        sa.Column("entry_type", sa.String(20), nullable=False),
        sa.Column("entry_currency", sa.String(3), nullable=False),
        sa.Column("entry_price", sa.Numeric(24, 10), nullable=True),
        sa.Column("entry_price_from", sa.Numeric(24, 10), nullable=True),
        sa.Column("entry_price_to", sa.Numeric(24, 10), nullable=True),
        sa.Column("entry_trigger", sa.Text(), nullable=True),
        sa.Column("entry_reference_price", sa.Numeric(24, 10), nullable=True),
        sa.Column("entry_valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("entry_rationale", sa.Text(), nullable=True),
        sa.Column("stop_price", sa.Numeric(24, 10), nullable=True),
        sa.Column("invalidation_rule", sa.Text(), nullable=True),
        sa.Column("invalidation_rationale", sa.Text(), nullable=True),
        sa.Column("risk_thesis", sa.Text(), nullable=False),
        sa.Column("risk_max_loss_assumption", sa.Text(), nullable=True),
        sa.Column("risk_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("previous_version_id", sa.Uuid(), nullable=True),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "version > 0", name="ck_trade_plan_versions_trade_plan_version_positive"
        ),
        sa.CheckConstraint(
            "direction = 'LONG'", name="ck_trade_plan_versions_trade_plan_version_long_only"
        ),
        sa.ForeignKeyConstraint(["trade_plan_id"], ["trade_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["previous_version_id"], ["trade_plan_versions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trade_plan_id", "version", name="uq_trade_plan_versions_plan_version"),
    )
    op.create_index(
        "ix_trade_plan_versions_plan_status", "trade_plan_versions", ["trade_plan_id", "status"]
    )
    op.create_index(
        "ix_trade_plan_versions_plan_created",
        "trade_plan_versions",
        ["trade_plan_id", "created_at"],
    )

    op.create_table(
        "trade_plan_targets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trade_plan_version_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(24, 10), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "sequence > 0", name="ck_trade_plan_targets_trade_plan_target_sequence_positive"
        ),
        sa.CheckConstraint(
            "price > 0", name="ck_trade_plan_targets_trade_plan_target_price_positive"
        ),
        sa.ForeignKeyConstraint(
            ["trade_plan_version_id"], ["trade_plan_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trade_plan_version_id", "sequence", name="uq_trade_plan_targets_version_sequence"
        ),
    )

    op.create_table(
        "trade_plan_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trade_plan_id", sa.Uuid(), nullable=False),
        sa.Column("trade_plan_version_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("from_status", sa.String(40), nullable=True),
        sa.Column("to_status", sa.String(40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor", sa.String(200), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["trade_plan_id"], ["trade_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["trade_plan_version_id"], ["trade_plan_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_trade_plan_events_plan_occurred", "trade_plan_events", ["trade_plan_id", "occurred_at"]
    )
    op.create_index(
        "ix_trade_plan_events_version_occurred",
        "trade_plan_events",
        ["trade_plan_version_id", "occurred_at"],
    )

    op.create_table(
        "trade_plan_approvals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trade_plan_id", sa.Uuid(), nullable=False),
        sa.Column("trade_plan_version_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("actor", sa.String(200), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=True),
        sa.ForeignKeyConstraint(["trade_plan_id"], ["trade_plans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["trade_plan_version_id"], ["trade_plan_versions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trade_plan_version_id", name="uq_trade_plan_approvals_version"),
    )
    op.create_index(
        "ix_trade_plan_approvals_plan_time",
        "trade_plan_approvals",
        ["trade_plan_id", "approved_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_trade_plan_approvals_plan_time", table_name="trade_plan_approvals")
    op.drop_table("trade_plan_approvals")
    op.drop_index("ix_trade_plan_events_version_occurred", table_name="trade_plan_events")
    op.drop_index("ix_trade_plan_events_plan_occurred", table_name="trade_plan_events")
    op.drop_table("trade_plan_events")
    op.drop_table("trade_plan_targets")
    op.drop_index("ix_trade_plan_versions_plan_created", table_name="trade_plan_versions")
    op.drop_index("ix_trade_plan_versions_plan_status", table_name="trade_plan_versions")
    op.drop_table("trade_plan_versions")
    op.drop_index("ix_trade_plans_workspace_underlying", table_name="trade_plans")
    op.drop_table("trade_plans")
