"""Add provider mappings and completed daily prices.

Revision ID: 20260805_0002
Revises: 20260803_0001
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260805_0002"
down_revision: str | None = "20260803_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "provider_instrument_mappings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("provider_symbol", sa.String(length=64), nullable=False),
        sa.Column("provider_exchange_code", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validation_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "version >= 1", name=op.f("ck_provider_instrument_mappings_version_positive")
        ),
        sa.CheckConstraint(
            "length(trim(provider_symbol)) > 0",
            name=op.f("ck_provider_instrument_mappings_provider_symbol_not_blank"),
        ),
        sa.CheckConstraint(
            "length(trim(provider_exchange_code)) > 0",
            name=op.f("ck_provider_instrument_mappings_provider_exchange_code_not_blank"),
        ),
        sa.ForeignKeyConstraint(
            ["listing_id"],
            ["listings.id"],
            name=op.f("fk_provider_instrument_mappings_listing_id_listings"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_provider_instrument_mappings_workspace_id_workspaces"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_provider_instrument_mappings")),
        sa.UniqueConstraint(
            "provider", "listing_id", name="uq_provider_instrument_mappings_provider_listing"
        ),
        sa.UniqueConstraint(
            "provider",
            "provider_exchange_code",
            "provider_symbol",
            name="uq_provider_instrument_mappings_provider_symbol",
        ),
    )
    op.create_index(
        "ix_provider_instrument_mappings_workspace_status",
        "provider_instrument_mappings",
        ["workspace_id", "status"],
        unique=False,
    )
    op.create_table(
        "daily_prices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), nullable=False),
        sa.Column("trading_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(precision=24, scale=10), nullable=False),
        sa.Column("high", sa.Numeric(precision=24, scale=10), nullable=False),
        sa.Column("low", sa.Numeric(precision=24, scale=10), nullable=False),
        sa.Column("close", sa.Numeric(precision=24, scale=10), nullable=False),
        sa.Column("adjusted_close", sa.Numeric(precision=24, scale=10), nullable=True),
        sa.Column("volume", sa.Numeric(precision=30, scale=6), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("provider_symbol", sa.String(length=64), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("quality_status", sa.String(length=20), nullable=False),
        sa.Column("warnings", sa.String(length=2000), nullable=False),
        sa.Column("price_type", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("open > 0", name=op.f("ck_daily_prices_open_positive")),
        sa.CheckConstraint("high > 0", name=op.f("ck_daily_prices_high_positive")),
        sa.CheckConstraint("low > 0", name=op.f("ck_daily_prices_low_positive")),
        sa.CheckConstraint("close > 0", name=op.f("ck_daily_prices_close_positive")),
        sa.CheckConstraint(
            "adjusted_close IS NULL OR adjusted_close > 0",
            name=op.f("ck_daily_prices_adjusted_close_positive"),
        ),
        sa.CheckConstraint(
            "volume IS NULL OR volume >= 0", name=op.f("ck_daily_prices_volume_non_negative")
        ),
        sa.CheckConstraint("low <= high", name=op.f("ck_daily_prices_low_not_above_high")),
        sa.CheckConstraint("open BETWEEN low AND high", name=op.f("ck_daily_prices_open_in_range")),
        sa.CheckConstraint(
            "close BETWEEN low AND high", name=op.f("ck_daily_prices_close_in_range")
        ),
        sa.ForeignKeyConstraint(
            ["currency"],
            ["currencies.code"],
            name=op.f("fk_daily_prices_currency_currencies"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["listing_id"],
            ["listings.id"],
            name=op.f("fk_daily_prices_listing_id_listings"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name=op.f("fk_daily_prices_workspace_id_workspaces"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_daily_prices")),
        sa.UniqueConstraint(
            "listing_id", "trading_date", "price_type", name="uq_daily_prices_listing_date_type"
        ),
    )
    op.create_index(
        "ix_daily_prices_listing_date", "daily_prices", ["listing_id", "trading_date"], unique=False
    )
    op.create_index(
        "ix_daily_prices_workspace_date",
        "daily_prices",
        ["workspace_id", "trading_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_daily_prices_workspace_date", table_name="daily_prices")
    op.drop_index("ix_daily_prices_listing_date", table_name="daily_prices")
    op.drop_table("daily_prices")
    op.drop_index(
        "ix_provider_instrument_mappings_workspace_status",
        table_name="provider_instrument_mappings",
    )
    op.drop_table("provider_instrument_mappings")
