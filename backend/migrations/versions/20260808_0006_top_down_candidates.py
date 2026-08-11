"""Create Sprint 5 top-down candidate persistence.

Revision ID: 20260808_0006
Revises: 20260806_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260808_0006"
down_revision: str | None = "20260806_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_references",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("reference_type", sa.String(30), nullable=False),
        sa.Column("region", sa.String(50), nullable=False),
        sa.Column("role", sa.String(40), nullable=False),
        sa.Column("reference_version", sa.String(50), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id", "code", name="uq_market_references_workspace_code"
        ),
    )
    op.create_table(
        "sectors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("classification_system", sa.String(100), nullable=False),
        sa.Column("classification_version", sa.String(50), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "code", name="uq_sectors_workspace_code"),
    )
    op.create_table(
        "underlying_sector_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("underlying_id", sa.Uuid(), nullable=False),
        sa.Column("sector_id", sa.Uuid(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("source_reference", sa.String(200), nullable=True),
        sa.Column("quality_status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["underlying_id"], ["underlyings.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["sector_id"], ["sectors.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_underlying_sector_assignments_underlying_valid",
        "underlying_sector_assignments",
        ["underlying_id", "valid_from"],
    )
    op.create_table(
        "sector_reference_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("sector_id", sa.Uuid(), nullable=False),
        sa.Column("market_reference_id", sa.Uuid(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("quality_status", sa.String(30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["sector_id"], ["sectors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["market_reference_id"], ["market_references.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sector_reference_assignments_sector_valid",
        "sector_reference_assignments",
        ["sector_id", "valid_from"],
    )
    op.create_table(
        "candidates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("underlying_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["underlying_id"], ["underlyings.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id", "underlying_id", name="uq_candidates_workspace_underlying"
        ),
    )
    op.create_index(
        "ix_candidates_workspace_status", "candidates", ["workspace_id", "status"]
    )
    op.create_table(
        "candidate_evaluations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("model_id", sa.String(100), nullable=False),
        sa.Column("model_version", sa.String(30), nullable=False),
        sa.Column("qualification", sa.String(30), nullable=False),
        sa.Column("quality_status", sa.String(30), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["candidates.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "candidate_id", "version", name="uq_candidate_evaluations_candidate_version"
        ),
    )
    op.create_index(
        "ix_candidate_evaluations_candidate_time",
        "candidate_evaluations",
        ["candidate_id", "evaluated_at"],
    )
    op.create_table(
        "candidate_evaluation_sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evaluation_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("source_type", sa.String(80), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.String(100), nullable=False),
        sa.Column("model_version", sa.String(30), nullable=False),
        sa.ForeignKeyConstraint(
            ["evaluation_id"], ["candidate_evaluations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "evaluation_id", "role", name="uq_candidate_evaluation_sources_role"
        ),
    )
    op.create_table(
        "candidate_criterion_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("evaluation_id", sa.Uuid(), nullable=False),
        sa.Column("criterion_id", sa.String(80), nullable=False),
        sa.Column("criterion_group", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(30), nullable=False),
        sa.Column("evaluation", sa.String(30), nullable=False),
        sa.Column("source", sa.String(150), nullable=False),
        sa.Column("actual_value", sa.String(100), nullable=True),
        sa.Column("expected_value", sa.String(100), nullable=True),
        sa.Column("numeric_value", sa.Numeric(30, 12), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["evaluation_id"], ["candidate_evaluations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "candidate_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("from_status", sa.String(40), nullable=True),
        sa.Column("to_status", sa.String(40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("actor", sa.String(200), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["candidates.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_candidate_events_candidate_time",
        "candidate_events",
        ["candidate_id", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_candidate_events_candidate_time", table_name="candidate_events")
    op.drop_table("candidate_events")
    op.drop_table("candidate_criterion_results")
    op.drop_table("candidate_evaluation_sources")
    op.drop_index(
        "ix_candidate_evaluations_candidate_time", table_name="candidate_evaluations"
    )
    op.drop_table("candidate_evaluations")
    op.drop_index("ix_candidates_workspace_status", table_name="candidates")
    op.drop_table("candidates")
    op.drop_index(
        "ix_sector_reference_assignments_sector_valid",
        table_name="sector_reference_assignments",
    )
    op.drop_table("sector_reference_assignments")
    op.drop_index(
        "ix_underlying_sector_assignments_underlying_valid",
        table_name="underlying_sector_assignments",
    )
    op.drop_table("underlying_sector_assignments")
    op.drop_table("sectors")
    op.drop_table("market_references")
