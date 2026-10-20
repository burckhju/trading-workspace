"""Retain the last verified warrant quote across refresh failures and restarts.

Revision ID: 20260914_0038
Revises: 20260914_0037
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260914_0038"
down_revision: str | None = "20260914_0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "warrant_quote_observations",
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("warrant_listing_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("identity_key", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["warrant_listing_id"], ["warrant_listings.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("workspace_id", "warrant_listing_id", "provider"),
    )


def downgrade() -> None:
    op.drop_table("warrant_quote_observations")
