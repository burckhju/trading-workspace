"""Add semantic top-down source-resolution mappings.

Revision ID: 20260810_0007
Revises: 20260808_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260810_0007"
down_revision: str | None = "20260808_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "underlying_benchmark_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("underlying_id", sa.Uuid(), nullable=False),
        sa.Column("market_reference_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(40), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["market_reference_id"], ["market_references.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_underlying_benchmark_assignments_underlying_role_valid",
        "underlying_benchmark_assignments",
        ["underlying_id", "role", "valid_from"],
    )
    op.create_table(
        "market_reference_listing_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("market_reference_id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
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
            ["market_reference_id"], ["market_references.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_market_reference_listing_assignments_reference_valid",
        "market_reference_listing_assignments",
        ["market_reference_id", "valid_from"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_market_reference_listing_assignments_reference_valid",
        table_name="market_reference_listing_assignments",
    )
    op.drop_table("market_reference_listing_assignments")
    op.drop_index(
        "ix_underlying_benchmark_assignments_underlying_role_valid",
        table_name="underlying_benchmark_assignments",
    )
    op.drop_table("underlying_benchmark_assignments")
