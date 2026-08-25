"""Migrate provider mappings, daily prices and analyses to market-data instruments.

Revision ID: 20260825_0023
Revises: 20260825_0022
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0023"
down_revision: str | None = "20260825_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _backfill(table: str) -> None:
    op.execute(
        sa.text(
            f"UPDATE {table} AS target "
            "SET market_data_instrument_id = mdi.id "
            "FROM market_data_instruments AS mdi "
            "WHERE mdi.kind = 'LISTING' "
            "AND mdi.listing_id = target.listing_id "
            "AND mdi.workspace_id = target.workspace_id"
        )
    )


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
        ondelete="CASCADE",
    )
    _backfill("provider_instrument_mappings")
    op.alter_column("provider_instrument_mappings", "market_data_instrument_id", nullable=False)
    op.alter_column("provider_instrument_mappings", "listing_id", nullable=True)
    op.drop_constraint(
        "uq_provider_instrument_mappings_provider_listing",
        "provider_instrument_mappings",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_provider_instrument_mappings_provider_instrument",
        "provider_instrument_mappings",
        ["provider", "market_data_instrument_id"],
    )

    op.add_column("daily_prices", sa.Column("market_data_instrument_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_daily_prices_market_data_instrument",
        "daily_prices",
        "market_data_instruments",
        ["market_data_instrument_id"],
        ["id"],
        ondelete="CASCADE",
    )
    _backfill("daily_prices")
    op.alter_column("daily_prices", "market_data_instrument_id", nullable=False)
    op.alter_column("daily_prices", "listing_id", nullable=True)
    op.drop_constraint("uq_daily_prices_listing_date_type", "daily_prices", type_="unique")
    op.create_unique_constraint(
        "uq_daily_prices_instrument_date_type",
        "daily_prices",
        ["market_data_instrument_id", "trading_date", "price_type"],
    )
    op.create_index(
        "ix_daily_prices_instrument_date",
        "daily_prices",
        ["market_data_instrument_id", "trading_date"],
    )

    op.add_column("market_analyses", sa.Column("market_data_instrument_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_market_analyses_market_data_instrument",
        "market_analyses",
        "market_data_instruments",
        ["market_data_instrument_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    _backfill("market_analyses")
    op.alter_column("market_analyses", "market_data_instrument_id", nullable=False)
    op.alter_column("market_analyses", "underlying_id", nullable=True)
    op.alter_column("market_analyses", "listing_id", nullable=True)
    op.create_index(
        "ix_market_analyses_workspace_instrument_created",
        "market_analyses",
        ["workspace_id", "market_data_instrument_id", "created_at"],
    )


def downgrade() -> None:
    # Downgrade is only safe while all rows still have legacy listing ownership.
    op.execute(
        sa.text(
            "DELETE FROM market_analyses WHERE listing_id IS NULL OR underlying_id IS NULL"
        )
    )
    op.execute(sa.text("DELETE FROM daily_prices WHERE listing_id IS NULL"))
    op.execute(sa.text("DELETE FROM provider_instrument_mappings WHERE listing_id IS NULL"))

    op.drop_index("ix_market_analyses_workspace_instrument_created", table_name="market_analyses")
    op.alter_column("market_analyses", "listing_id", nullable=False)
    op.alter_column("market_analyses", "underlying_id", nullable=False)
    op.drop_constraint(
        "fk_market_analyses_market_data_instrument", "market_analyses", type_="foreignkey"
    )
    op.drop_column("market_analyses", "market_data_instrument_id")

    op.drop_index("ix_daily_prices_instrument_date", table_name="daily_prices")
    op.drop_constraint("uq_daily_prices_instrument_date_type", "daily_prices", type_="unique")
    op.create_unique_constraint(
        "uq_daily_prices_listing_date_type",
        "daily_prices",
        ["listing_id", "trading_date", "price_type"],
    )
    op.alter_column("daily_prices", "listing_id", nullable=False)
    op.drop_constraint(
        "fk_daily_prices_market_data_instrument", "daily_prices", type_="foreignkey"
    )
    op.drop_column("daily_prices", "market_data_instrument_id")

    op.drop_constraint(
        "uq_provider_instrument_mappings_provider_instrument",
        "provider_instrument_mappings",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_provider_instrument_mappings_provider_listing",
        "provider_instrument_mappings",
        ["provider", "listing_id"],
    )
    op.alter_column("provider_instrument_mappings", "listing_id", nullable=False)
    op.drop_constraint(
        "fk_provider_instrument_mappings_market_data_instrument",
        "provider_instrument_mappings",
        type_="foreignkey",
    )
    op.drop_column("provider_instrument_mappings", "market_data_instrument_id")
