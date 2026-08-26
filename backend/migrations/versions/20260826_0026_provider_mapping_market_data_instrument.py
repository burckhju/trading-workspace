"""D01-B expand provider mappings to MarketDataInstrument.

Revision ID: 20260826_0026
Revises: 20260826_0025
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260826_0026"
down_revision: str | None = "20260826_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MAPPING_INSTRUMENT_GUARD = """
CREATE FUNCTION enforce_provider_mapping_instrument_consistency()
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
        RAISE EXCEPTION 'provider mapping/market-data instrument workspace mismatch'
            USING ERRCODE = '23514';
    END IF;

    IF NEW.listing_id IS NOT NULL
       AND (instrument_kind <> 'LISTING' OR instrument_listing_id <> NEW.listing_id) THEN
        RAISE EXCEPTION 'provider mapping listing/instrument owner mismatch'
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    op.add_column(
        "provider_instrument_mappings",
        sa.Column("market_data_instrument_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_provider_instrument_mappings_market_data_instrument",
        "provider_instrument_mappings",
        "market_data_instruments",
        ["market_data_instrument_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.execute(
        sa.text(
            "UPDATE provider_instrument_mappings AS mapping "
            "SET market_data_instrument_id = instrument.id "
            "FROM market_data_instruments AS instrument "
            "WHERE mapping.listing_id IS NOT NULL "
            "AND instrument.kind = 'LISTING' "
            "AND instrument.listing_id = mapping.listing_id "
            "AND instrument.workspace_id = mapping.workspace_id"
        )
    )

    op.alter_column("provider_instrument_mappings", "listing_id", nullable=True)
    op.create_check_constraint(
        "ck_provider_instrument_mappings_internal_owner",
        "provider_instrument_mappings",
        "listing_id IS NOT NULL OR market_data_instrument_id IS NOT NULL",
    )
    op.create_unique_constraint(
        "uq_provider_instrument_mappings_provider_instrument",
        "provider_instrument_mappings",
        ["provider", "market_data_instrument_id"],
    )
    op.create_index(
        "ix_provider_instrument_mappings_workspace_instrument",
        "provider_instrument_mappings",
        ["workspace_id", "market_data_instrument_id"],
    )

    op.execute(_MAPPING_INSTRUMENT_GUARD)
    op.execute(
        "CREATE TRIGGER trg_provider_mapping_instrument_consistency "
        "BEFORE INSERT OR UPDATE OF workspace_id, listing_id, market_data_instrument_id "
        "ON provider_instrument_mappings FOR EACH ROW "
        "EXECUTE FUNCTION enforce_provider_mapping_instrument_consistency()"
    )


def downgrade() -> None:
    # Rows owned only by MarketDataInstrument cannot be represented by the legacy schema.
    op.execute(
        sa.text(
            "DELETE FROM provider_instrument_mappings "
            "WHERE listing_id IS NULL"
        )
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_provider_mapping_instrument_consistency "
        "ON provider_instrument_mappings"
    )
    op.execute("DROP FUNCTION IF EXISTS enforce_provider_mapping_instrument_consistency()")
    op.drop_index(
        "ix_provider_instrument_mappings_workspace_instrument",
        table_name="provider_instrument_mappings",
    )
    op.drop_constraint(
        "uq_provider_instrument_mappings_provider_instrument",
        "provider_instrument_mappings",
        type_="unique",
    )
    op.drop_constraint(
        "ck_provider_instrument_mappings_internal_owner",
        "provider_instrument_mappings",
        type_="check",
    )
    op.alter_column("provider_instrument_mappings", "listing_id", nullable=False)
    op.drop_constraint(
        "fk_provider_instrument_mappings_market_data_instrument",
        "provider_instrument_mappings",
        type_="foreignkey",
    )
    op.drop_column("provider_instrument_mappings", "market_data_instrument_id")
