"""Add append-only FT-006 lifecycle events.

Revision ID: 20260806_0005
Revises: 20260806_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260806_0005"
down_revision: str | None = "20260806_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_analysis_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("from_status", sa.String(40), nullable=True),
        sa.Column("to_status", sa.String(40), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=True),
        sa.Column("replacement_version", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("correlation_id", sa.String(100), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["market_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["market_analysis_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_id",
            "version",
            "event_type",
            name="uq_market_analysis_events_version_type",
        ),
    )
    op.create_index(
        "ix_market_analysis_events_analysis_occurred",
        "market_analysis_events",
        ["analysis_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_market_analysis_events_analysis_occurred",
        table_name="market_analysis_events",
    )
    op.drop_table("market_analysis_events")
