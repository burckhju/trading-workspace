"""Create the FT-001 basis asset management schema.

Revision ID: 20260803_0001
Revises:
Create Date: 2026-08-03 20:10:36 UTC
"""

from collections.abc import Sequence
from datetime import datetime, timezone
from uuid import UUID

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260803_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
WORKSPACE_NAME = "Trading Workspace V1"
XETRA_ID = UUID("00000000-0000-4000-8001-000000000001")
REFERENCE_VERSION = "FT-001-V1"
SEED_TIMESTAMP = datetime(2026, 8, 3, 20, 10, 36, tzinfo=timezone.utc)


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workspaces")),
    )

    op.create_table(
        "trading_venues",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("mic", sa.String(length=4), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("reference_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(trim(name)) > 0", name=op.f("ck_trading_venues_name_not_blank")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trading_venues")),
        sa.UniqueConstraint("mic", name="uq_trading_venues_mic"),
    )

    op.create_table(
        "currencies",
        sa.Column("code", sa.String(length=3), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("minor_unit", sa.SmallInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("reference_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("minor_unit BETWEEN 0 AND 6", name=op.f("ck_currencies_minor_unit_range")),
        sa.CheckConstraint("length(trim(name)) > 0", name=op.f("ck_currencies_name_not_blank")),
        sa.PrimaryKeyConstraint("code", name=op.f("pk_currencies")),
    )

    op.create_table(
        "underlyings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("isin", sa.String(length=12), nullable=True),
        sa.Column("wkn", sa.String(length=6), nullable=True),
        sa.Column("lifecycle_status", sa.String(length=20), nullable=False),
        sa.Column("quality_status", sa.String(length=20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_origin", sa.String(length=20), nullable=False),
        sa.CheckConstraint("version >= 1", name=op.f("ck_underlyings_version_positive")),
        sa.CheckConstraint("length(trim(name)) > 0", name=op.f("ck_underlyings_name_not_blank")),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"],
            name=op.f("fk_underlyings_workspace_id_workspaces"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_underlyings")),
    )
    op.create_index(
        "ix_underlyings_workspace_lifecycle_name",
        "underlyings",
        ["workspace_id", "lifecycle_status", "name"],
        unique=False,
    )
    op.create_index(
        "uq_underlyings_workspace_isin",
        "underlyings",
        ["workspace_id", "isin"],
        unique=True,
        postgresql_where=sa.text("isin IS NOT NULL"),
    )
    op.create_index(
        "uq_underlyings_workspace_wkn",
        "underlyings",
        ["workspace_id", "wkn"],
        unique=True,
        postgresql_where=sa.text("wkn IS NOT NULL"),
    )

    op.create_table(
        "listings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("underlying_id", sa.Uuid(), nullable=False),
        sa.Column("trading_venue_id", sa.Uuid(), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("currency_code", sa.String(length=3), nullable=False),
        sa.Column("lifecycle_status", sa.String(length=20), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_origin", sa.String(length=20), nullable=False),
        sa.CheckConstraint("version >= 1", name=op.f("ck_listings_version_positive")),
        sa.CheckConstraint("length(trim(ticker)) > 0", name=op.f("ck_listings_ticker_not_blank")),
        sa.ForeignKeyConstraint(
            ["currency_code"], ["currencies.code"],
            name=op.f("fk_listings_currency_code_currencies"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["trading_venue_id"], ["trading_venues.id"],
            name=op.f("fk_listings_trading_venue_id_trading_venues"), ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["underlying_id"], ["underlyings.id"],
            name=op.f("fk_listings_underlying_id_underlyings"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"],
            name=op.f("fk_listings_workspace_id_workspaces"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_listings")),
        sa.UniqueConstraint(
            "workspace_id", "trading_venue_id", "ticker",
            name="uq_listings_workspace_venue_ticker"
        ),
    )
    op.create_index(
        "ix_listings_underlying_lifecycle",
        "listings",
        ["underlying_id", "lifecycle_status"],
        unique=False,
    )
    op.create_index(
        "ix_listings_workspace_ticker",
        "listings",
        ["workspace_id", "ticker"],
        unique=False,
    )
    op.create_index(
        "uq_listings_active_primary_underlying",
        "listings",
        ["underlying_id"],
        unique=True,
        postgresql_where=sa.text("is_primary = true AND lifecycle_status = 'ACTIVE'"),
    )

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("aggregate_type", sa.String(length=30), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_type", sa.String(length=20), nullable=False),
        sa.Column("actor_id", sa.String(length=100), nullable=True),
        sa.Column("actor_display_name", sa.String(length=200), nullable=False),
        sa.Column("data_origin", sa.String(length=20), nullable=False),
        sa.Column("change_type", sa.String(length=30), nullable=False),
        sa.Column("version_before", sa.Integer(), nullable=True),
        sa.Column("version_after", sa.Integer(), nullable=True),
        sa.Column("field_changes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"],
            name=op.f("fk_audit_events_workspace_id_workspaces"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index(
        "ix_audit_events_aggregate_chronology",
        "audit_events",
        ["workspace_id", "aggregate_type", "aggregate_id", sa.text("occurred_at DESC")],
        unique=False,
    )
    op.create_index(
        "ix_audit_events_workspace_chronology",
        "audit_events",
        ["workspace_id", sa.text("occurred_at DESC")],
        unique=False,
    )

    workspace_table = sa.table(
        "workspaces",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    trading_venue_table = sa.table(
        "trading_venues",
        sa.column("id", sa.Uuid()),
        sa.column("mic", sa.String()),
        sa.column("name", sa.String()),
        sa.column("country_code", sa.String()),
        sa.column("timezone", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("reference_version", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    currency_table = sa.table(
        "currencies",
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("minor_unit", sa.SmallInteger()),
        sa.column("is_active", sa.Boolean()),
        sa.column("reference_version", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )

    op.bulk_insert(
        workspace_table,
        [{"id": WORKSPACE_ID, "name": WORKSPACE_NAME, "created_at": SEED_TIMESTAMP}],
    )
    op.bulk_insert(
        trading_venue_table,
        [{
            "id": XETRA_ID,
            "mic": "XETR",
            "name": "Xetra",
            "country_code": "DE",
            "timezone": "Europe/Berlin",
            "is_active": True,
            "reference_version": REFERENCE_VERSION,
            "created_at": SEED_TIMESTAMP,
            "updated_at": SEED_TIMESTAMP,
        }],
    )
    op.bulk_insert(
        currency_table,
        [{
            "code": "EUR",
            "name": "Euro",
            "minor_unit": 2,
            "is_active": True,
            "reference_version": REFERENCE_VERSION,
            "created_at": SEED_TIMESTAMP,
            "updated_at": SEED_TIMESTAMP,
        }],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_events_workspace_chronology", table_name="audit_events")
    op.drop_index("ix_audit_events_aggregate_chronology", table_name="audit_events")
    op.drop_table("audit_events")

    op.drop_index("uq_listings_active_primary_underlying", table_name="listings")
    op.drop_index("ix_listings_workspace_ticker", table_name="listings")
    op.drop_index("ix_listings_underlying_lifecycle", table_name="listings")
    op.drop_table("listings")

    op.drop_index("uq_underlyings_workspace_wkn", table_name="underlyings")
    op.drop_index("uq_underlyings_workspace_isin", table_name="underlyings")
    op.drop_index("ix_underlyings_workspace_lifecycle_name", table_name="underlyings")
    op.drop_table("underlyings")

    op.drop_table("currencies")
    op.drop_table("trading_venues")
    op.drop_table("workspaces")
