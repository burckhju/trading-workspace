"""FT-004 warrant persistence.

Revision ID: 20260815_0011
Revises: 20260815_0010
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260815_0011"
down_revision: str | None = "20260815_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "warrants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("issuer_id", sa.Uuid(), nullable=False),
        sa.Column("underlying_id", sa.Uuid(), nullable=False),
        sa.Column("product_family", sa.String(length=20), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("isin", sa.String(length=12), nullable=True),
        sa.Column("wkn", sa.String(length=16), nullable=True),
        sa.Column("lifecycle_status", sa.String(length=20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version >= 1", name="ck_warrants_version_positive"),
        sa.CheckConstraint(
            "length(trim(display_name)) > 0", name="ck_warrants_display_name_not_blank"
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["issuer_id"], ["issuers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["underlying_id"], ["underlyings.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_warrants_workspace_isin",
        "warrants",
        ["workspace_id", "isin"],
        unique=True,
        postgresql_where=sa.text("isin IS NOT NULL"),
    )
    op.create_index(
        "uq_warrants_workspace_wkn",
        "warrants",
        ["workspace_id", "wkn"],
        unique=True,
        postgresql_where=sa.text("wkn IS NOT NULL"),
    )
    op.create_index(
        "ix_warrants_workspace_underlying", "warrants", ["workspace_id", "underlying_id"]
    )
    op.create_index("ix_warrants_workspace_issuer", "warrants", ["workspace_id", "issuer_id"])

    op.create_table(
        "warrant_terms_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("warrant_id", sa.Uuid(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("option_direction", sa.String(length=10), nullable=False),
        sa.Column("strike", sa.Numeric(20, 8), nullable=False),
        sa.Column("maturity_date", sa.Date(), nullable=False),
        sa.Column("ratio", sa.Numeric(20, 10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version_no >= 1", name="ck_warrant_terms_versions_version_no_positive"),
        sa.CheckConstraint("strike >= 0", name="ck_warrant_terms_versions_strike_non_negative"),
        sa.CheckConstraint("ratio > 0", name="ck_warrant_terms_versions_ratio_positive"),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="ck_warrant_terms_versions_effective_window_valid",
        ),
        sa.ForeignKeyConstraint(["warrant_id"], ["warrants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "warrant_id", "version_no", name="uq_warrant_terms_versions_warrant_version"
        ),
    )
    op.create_index(
        "uq_warrant_terms_versions_open",
        "warrant_terms_versions",
        ["warrant_id"],
        unique=True,
        postgresql_where=sa.text("effective_to IS NULL"),
    )

    op.create_table(
        "warrant_listings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("warrant_id", sa.Uuid(), nullable=False),
        sa.Column("trading_venue_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("quotation_currency_code", sa.String(length=3), nullable=False),
        sa.Column("lifecycle_status", sa.String(length=20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("version >= 1", name="ck_warrant_listings_version_positive"),
        sa.CheckConstraint("length(trim(symbol)) > 0", name="ck_warrant_listings_symbol_not_blank"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warrant_id"], ["warrants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["trading_venue_id"], ["trading_venues.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["quotation_currency_code"], ["currencies.code"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "trading_venue_id",
            "symbol",
            name="uq_warrant_listings_workspace_venue_symbol",
        ),
    )
    op.create_index(
        "ix_warrant_listings_warrant_lifecycle",
        "warrant_listings",
        ["warrant_id", "lifecycle_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_warrant_listings_warrant_lifecycle", table_name="warrant_listings")
    op.drop_table("warrant_listings")
    op.drop_index("uq_warrant_terms_versions_open", table_name="warrant_terms_versions")
    op.drop_table("warrant_terms_versions")
    op.drop_index("ix_warrants_workspace_issuer", table_name="warrants")
    op.drop_index("ix_warrants_workspace_underlying", table_name="warrants")
    op.drop_index("uq_warrants_workspace_wkn", table_name="warrants")
    op.drop_index("uq_warrants_workspace_isin", table_name="warrants")
    op.drop_table("warrants")
