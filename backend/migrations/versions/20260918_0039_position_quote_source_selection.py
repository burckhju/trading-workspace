"""Persist one auditable quote-source decision per position.

Revision ID: 20260918_0039
Revises: 20260914_0038
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260918_0039"
down_revision: str | None = "20260914_0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "position_quote_source_selections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("position_id", sa.Uuid(), nullable=False),
        sa.Column("warrant_listing_id", sa.Uuid(), nullable=True),
        sa.Column("warrant_provider_mapping_id", sa.Uuid(), nullable=True),
        sa.Column("provider", sa.String(30), nullable=True),
        sa.Column("identity_key", sa.String(64), nullable=True),
        sa.Column("mapping_version", sa.Integer(), nullable=True),
        sa.Column("selection_status", sa.String(32), nullable=False),
        sa.Column("selection_reason", sa.String(100), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("selected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "selection_status IN "
            "('SELECTED','NO_VERIFIED_QUOTE_SOURCE','AMBIGUOUS_SOURCE')",
            name="selection_status_valid",
        ),
        sa.CheckConstraint(
            "(selection_status = 'SELECTED' "
            "AND warrant_listing_id IS NOT NULL "
            "AND warrant_provider_mapping_id IS NOT NULL "
            "AND provider IS NOT NULL "
            "AND identity_key IS NOT NULL "
            "AND mapping_version IS NOT NULL) "
            "OR "
            "(selection_status <> 'SELECTED' "
            "AND warrant_listing_id IS NULL "
            "AND warrant_provider_mapping_id IS NULL "
            "AND provider IS NULL "
            "AND identity_key IS NULL "
            "AND mapping_version IS NULL)",
            name="selected_route_consistent",
        ),
        sa.CheckConstraint(
            "(warrant_provider_mapping_id IS NULL AND mapping_version IS NULL) "
            "OR "
            "(warrant_provider_mapping_id IS NOT NULL AND mapping_version IS NOT NULL)",
            name="mapping_version_consistent",
        ),
        sa.CheckConstraint(
            "superseded_at IS NULL OR superseded_at >= selected_at",
            name="superseded_not_before_selected",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["position_id"], ["positions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["warrant_listing_id"], ["warrant_listings.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["warrant_provider_mapping_id"],
            ["warrant_provider_mappings.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_position_quote_source_selections_workspace_position",
        "position_quote_source_selections",
        ["workspace_id", "position_id"],
        unique=False,
    )
    op.create_index(
        "uq_position_quote_source_selections_active_position",
        "position_quote_source_selections",
        ["workspace_id", "position_id"],
        unique=True,
        postgresql_where=sa.text("superseded_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_position_quote_source_selections_active_position",
        table_name="position_quote_source_selections",
    )
    op.drop_index(
        "ix_position_quote_source_selections_workspace_position",
        table_name="position_quote_source_selections",
    )
    op.drop_table("position_quote_source_selections")
