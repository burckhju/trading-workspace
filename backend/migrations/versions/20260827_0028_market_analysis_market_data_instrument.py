"""D01-D expand MarketAnalysis to MarketDataInstrument.

Revision ID: 20260827_0028
Revises: 20260826_0027
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "20260827_0028"
down_revision: str | None = "20260826_0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ANALYSIS_INSTRUMENT_GUARD = """
CREATE FUNCTION enforce_market_analysis_instrument_consistency()
RETURNS trigger AS $$
DECLARE
    instrument_workspace uuid;
    instrument_kind varchar(30);
    instrument_listing_id uuid;
BEGIN
    IF NEW.market_data_instrument_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT workspace_id, kind, listing_id
      INTO instrument_workspace, instrument_kind, instrument_listing_id
      FROM market_data_instruments
     WHERE id = NEW.market_data_instrument_id;

    IF NOT FOUND OR instrument_workspace <> NEW.workspace_id THEN
        RAISE EXCEPTION 'market analysis/market-data instrument workspace mismatch'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.listing_id IS NOT NULL THEN
        IF instrument_kind <> 'LISTING' OR instrument_listing_id <> NEW.listing_id THEN
            RAISE EXCEPTION 'market analysis listing/instrument owner mismatch'
                USING ERRCODE = '23514';
        END IF;
    ELSIF instrument_kind <> 'MARKET_REFERENCE' THEN
        RAISE EXCEPTION 'instrument-only market analysis requires MARKET_REFERENCE owner'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def _ensure_listing_identities() -> None:
    bind = op.get_bind()
    missing = bind.execute(
        sa.text(
            "SELECT listing.id, listing.workspace_id, listing.created_at "
            "FROM listings AS listing "
            "LEFT JOIN market_data_instruments AS instrument "
            "ON instrument.listing_id = listing.id "
            "WHERE instrument.id IS NULL"
        )
    ).mappings()
    for row in missing:
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


def upgrade() -> None:
    op.add_column(
        "market_analyses",
        sa.Column("market_data_instrument_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_market_analyses_market_data_instrument",
        "market_analyses",
        "market_data_instruments",
        ["market_data_instrument_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    _ensure_listing_identities()
    op.execute(
        sa.text(
            "UPDATE market_analyses AS analysis "
            "SET market_data_instrument_id = instrument.id "
            "FROM market_data_instruments AS instrument "
            "WHERE analysis.listing_id IS NOT NULL "
            "AND instrument.kind = 'LISTING' "
            "AND instrument.listing_id = analysis.listing_id "
            "AND instrument.workspace_id = analysis.workspace_id"
        )
    )

    op.alter_column("market_analyses", "underlying_id", nullable=True)
    op.alter_column("market_analyses", "listing_id", nullable=True)
    op.create_check_constraint(
        "ck_market_analyses_owner_shape",
        "market_analyses",
        "((listing_id IS NOT NULL AND underlying_id IS NOT NULL) OR "
        "(listing_id IS NULL AND underlying_id IS NULL AND "
        "market_data_instrument_id IS NOT NULL))",
    )
    op.create_index(
        "ix_market_analyses_workspace_instrument_created",
        "market_analyses",
        ["workspace_id", "market_data_instrument_id", "created_at"],
    )

    op.execute(_ANALYSIS_INSTRUMENT_GUARD)
    op.execute(
        "CREATE TRIGGER trg_market_analysis_instrument_consistency "
        "BEFORE INSERT OR UPDATE OF workspace_id, listing_id, market_data_instrument_id "
        "ON market_analyses FOR EACH ROW "
        "EXECUTE FUNCTION enforce_market_analysis_instrument_consistency()"
    )


def downgrade() -> None:
    bind = op.get_bind()
    instrument_only_count = bind.execute(
        sa.text(
            "SELECT count(*) FROM market_analyses "
            "WHERE listing_id IS NULL AND market_data_instrument_id IS NOT NULL"
        )
    ).scalar_one()
    if instrument_only_count:
        raise RuntimeError(
            "D01-D downgrade refused: instrument-only market analyses cannot be "
            "represented by revision 20260826_0027"
        )

    op.execute(
        "DROP TRIGGER IF EXISTS trg_market_analysis_instrument_consistency ON market_analyses"
    )
    op.execute("DROP FUNCTION IF EXISTS enforce_market_analysis_instrument_consistency()")
    op.drop_index(
        "ix_market_analyses_workspace_instrument_created",
        table_name="market_analyses",
    )
    op.drop_constraint("ck_market_analyses_owner_shape", "market_analyses", type_="check")
    op.alter_column("market_analyses", "listing_id", nullable=False)
    op.alter_column("market_analyses", "underlying_id", nullable=False)
    op.drop_constraint(
        "fk_market_analyses_market_data_instrument",
        "market_analyses",
        type_="foreignkey",
    )
    op.drop_column("market_analyses", "market_data_instrument_id")
