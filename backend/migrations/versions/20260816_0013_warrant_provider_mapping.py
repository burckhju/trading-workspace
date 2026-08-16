"""FT-008 warrant provider mapping boundary.

Revision ID: 20260816_0013
Revises: 20260816_0012
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "20260816_0013"
down_revision: str | None = "20260816_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "warrant_provider_mappings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("warrant_listing_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("provider_symbol", sa.String(length=64), nullable=False),
        sa.Column("provider_exchange_code", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validation_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint("version >= 1", name="ck_warrant_provider_mappings_version_positive"),
        sa.CheckConstraint("length(trim(provider_symbol)) > 0", name="ck_warrant_provider_mappings_provider_symbol_not_blank"),
        sa.CheckConstraint("length(trim(provider_exchange_code)) > 0", name="ck_warrant_provider_mappings_provider_exchange_code_not_blank"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warrant_listing_id"], ["warrant_listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "warrant_listing_id", name="uq_warrant_provider_mappings_provider_listing"),
        sa.UniqueConstraint("provider", "provider_exchange_code", "provider_symbol", name="uq_warrant_provider_mappings_provider_symbol"),
    )
    op.create_index("ix_warrant_provider_mappings_workspace_status", "warrant_provider_mappings", ["workspace_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_warrant_provider_mappings_workspace_status", table_name="warrant_provider_mappings")
    op.drop_table("warrant_provider_mappings")
