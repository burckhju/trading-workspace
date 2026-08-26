"""D01-A provider-neutral market-data instrument identity.

Revision ID: 20260826_0025
Revises: 20260825_0024
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "20260826_0025"
down_revision: str | None = "20260825_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_WORKSPACE_GUARD_FUNCTION = """
CREATE FUNCTION enforce_market_data_instrument_workspace()
RETURNS trigger AS $$
BEGIN
    IF NEW.kind = 'LISTING' THEN
        PERFORM 1
        FROM listings
        WHERE id = NEW.listing_id AND workspace_id = NEW.workspace_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'market-data instrument/listing workspace mismatch'
                USING ERRCODE = '23514';
        END IF;
    ELSIF NEW.kind = 'MARKET_REFERENCE' THEN
        PERFORM 1
        FROM market_references
        WHERE id = NEW.market_reference_id AND workspace_id = NEW.workspace_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'market-data instrument/market-reference workspace mismatch'
                USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    op.create_table(
        "market_data_instruments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=True),
        sa.Column("market_reference_id", sa.Uuid(), nullable=True),
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
        sa.UniqueConstraint("listing_id", name="uq_market_data_instruments_listing"),
        sa.UniqueConstraint(
            "market_reference_id",
            name="uq_market_data_instruments_market_reference",
        ),
    )
    op.create_index(
        "ix_market_data_instruments_workspace_kind",
        "market_data_instruments",
        ["workspace_id", "kind"],
    )

    op.execute(_WORKSPACE_GUARD_FUNCTION)
    op.execute(
        "CREATE TRIGGER trg_market_data_instruments_workspace "
        "BEFORE INSERT OR UPDATE OF workspace_id, kind, listing_id, market_reference_id "
        "ON market_data_instruments FOR EACH ROW "
        "EXECUTE FUNCTION enforce_market_data_instrument_workspace()"
    )

    bind = op.get_bind()
    listings = bind.execute(
        sa.text("SELECT id, workspace_id, created_at FROM listings")
    ).mappings()
    for row in listings:
        bind.execute(
            sa.text(
                "INSERT INTO market_data_instruments "
                "(id, workspace_id, kind, listing_id, market_reference_id, created_at) "
                "VALUES (:id, :workspace_id, 'LISTING', :listing_id, NULL, :created_at)"
            ),
            {
                "id": uuid4(),
                "workspace_id": row["workspace_id"],
                "listing_id": row["id"],
                "created_at": row["created_at"],
            },
        )

    references = bind.execute(
        sa.text("SELECT id, workspace_id, created_at FROM market_references")
    ).mappings()
    for row in references:
        bind.execute(
            sa.text(
                "INSERT INTO market_data_instruments "
                "(id, workspace_id, kind, listing_id, market_reference_id, created_at) "
                "VALUES (:id, :workspace_id, 'MARKET_REFERENCE', NULL, :reference_id, :created_at)"
            ),
            {
                "id": uuid4(),
                "workspace_id": row["workspace_id"],
                "reference_id": row["id"],
                "created_at": row["created_at"],
            },
        )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_market_data_instruments_workspace "
        "ON market_data_instruments"
    )
    op.execute("DROP FUNCTION IF EXISTS enforce_market_data_instrument_workspace()")
    op.drop_index(
        "ix_market_data_instruments_workspace_kind",
        table_name="market_data_instruments",
    )
    op.drop_table("market_data_instruments")
