"""Add provider-neutral market-data instrument identities.

Revision ID: 20260825_0022
Revises: 20260824_0021
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0022"
down_revision: str | None = "20260824_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_data_instruments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=True),
        sa.Column("market_reference_id", sa.Uuid(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(kind = 'LISTING' AND listing_id IS NOT NULL AND market_reference_id IS NULL) OR "
            "(kind = 'MARKET_REFERENCE' AND listing_id IS NULL AND market_reference_id IS NOT NULL)",
            name="ck_market_data_instruments_owner_matches_kind",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["listing_id"], ["listings.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["market_reference_id"], ["market_references.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "listing_id",
            name="uq_market_data_instruments_workspace_listing",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "market_reference_id",
            name="uq_market_data_instruments_workspace_reference",
        ),
    )
    op.create_index(
        "ix_market_data_instruments_workspace_kind_active",
        "market_data_instruments",
        ["workspace_id", "kind", "active"],
    )

    bind = op.get_bind()
    now = datetime.now(UTC)

    listings = bind.execute(sa.text("SELECT id, workspace_id FROM listings")).mappings()
    for row in listings:
        bind.execute(
            sa.text(
                "INSERT INTO market_data_instruments "
                "(id, workspace_id, kind, listing_id, market_reference_id, active, created_at) "
                "VALUES (:id, :workspace_id, 'LISTING', :listing_id, NULL, true, :created_at)"
            ),
            {
                "id": uuid4(),
                "workspace_id": row["workspace_id"],
                "listing_id": row["id"],
                "created_at": now,
            },
        )

    references = bind.execute(
        sa.text("SELECT id, workspace_id, active FROM market_references")
    ).mappings()
    for row in references:
        bind.execute(
            sa.text(
                "INSERT INTO market_data_instruments "
                "(id, workspace_id, kind, listing_id, market_reference_id, active, created_at) "
                "VALUES (:id, :workspace_id, 'MARKET_REFERENCE', NULL, :reference_id, :active, :created_at)"
            ),
            {
                "id": uuid4(),
                "workspace_id": row["workspace_id"],
                "reference_id": row["id"],
                "active": row["active"],
                "created_at": now,
            },
        )

    op.alter_column("market_data_instruments", "active", server_default=None)


def downgrade() -> None:
    op.drop_index(
        "ix_market_data_instruments_workspace_kind_active",
        table_name="market_data_instruments",
    )
    op.drop_table("market_data_instruments")
