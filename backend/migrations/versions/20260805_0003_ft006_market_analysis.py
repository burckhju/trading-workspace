"""Create FT-006 reproducible market-analysis schema.

Revision ID: 20260805_0003
Revises: 20260805_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260805_0003"
down_revision: str | None = "20260805_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("underlying_id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["underlying_id"], ["underlyings.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_market_analyses_workspace_created",
        "market_analyses",
        ["workspace_id", "created_at"],
    )
    op.create_table(
        "market_analysis_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("quality_status", sa.String(30), nullable=False),
        sa.Column("model_id", sa.String(100), nullable=False),
        sa.Column("model_version", sa.String(30), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("notes", sa.JSON(), nullable=False),
        sa.Column("data_sources", sa.JSON(), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("observation_count", sa.Integer(), nullable=False),
        sa.Column("analysis_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["analysis_id"], ["market_analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "analysis_id", "version", name="uq_market_analysis_runs_analysis_version"
        ),
    )
    op.create_table(
        "market_analysis_snapshot_rows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("trading_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(24, 10), nullable=False),
        sa.Column("high", sa.Numeric(24, 10), nullable=False),
        sa.Column("low", sa.Numeric(24, 10), nullable=False),
        sa.Column("close", sa.Numeric(24, 10), nullable=False),
        sa.Column("adjusted_close", sa.Numeric(24, 10), nullable=True),
        sa.Column("volume", sa.Numeric(30, 6), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("provider_symbol", sa.String(64), nullable=False),
        sa.Column("quality_status", sa.String(20), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["market_analysis_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "trading_date", name="uq_market_analysis_snapshot_run_date"),
    )
    op.create_table(
        "market_analysis_criterion_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("classification", sa.String(30), nullable=False),
        sa.Column("value", sa.Numeric(30, 12), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["market_analysis_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("market_analysis_criterion_results")
    op.drop_table("market_analysis_snapshot_rows")
    op.drop_table("market_analysis_runs")
    op.drop_index("ix_market_analyses_workspace_created", table_name="market_analyses")
    op.drop_table("market_analyses")
