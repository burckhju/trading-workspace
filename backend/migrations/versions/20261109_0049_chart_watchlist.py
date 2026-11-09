"""Persist explicitly activated chart membership and setup attempt facts.

Revision ID: 20261109_0049
Revises: 20261028_0048
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261109_0049"
down_revision: str | None = "20261028_0048"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chart_watchlists",
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("catalog_version", sa.String(80), nullable=False),
        sa.Column("catalog_checksum", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_by", sa.String(200)),
        sa.Column("activated_by_name", sa.String(200), nullable=False),
        sa.CheckConstraint("length(catalog_checksum) = 64", name="catalog_checksum_shape"),
    )
    op.create_table(
        "chart_watchlist_members",
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("chart_watchlists.workspace_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("code", sa.String(80), primary_key=True),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("definition", sa.JSON(), nullable=False),
        sa.Column("listing_id", sa.Uuid(), sa.ForeignKey("listings.id", ondelete="RESTRICT")),
        sa.Column(
            "market_reference_id",
            sa.Uuid(),
            sa.ForeignKey("market_references.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "created_mapping_id",
            sa.Uuid(),
            sa.ForeignKey(
                "provider_instrument_mappings.id",
                ondelete="RESTRICT",
                deferrable=True,
                initially="DEFERRED",
            ),
        ),
        sa.Column("created_mapping_version", sa.Integer()),
        sa.Column(
            "verified_mapping_id",
            sa.Uuid(),
            sa.ForeignKey("provider_instrument_mappings.id", ondelete="RESTRICT"),
        ),
        sa.Column("verified_mapping_version", sa.Integer()),
        sa.Column("verified_provider_symbol", sa.String(64)),
        sa.Column("verified_provider_exchange_code", sa.String(32)),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("last_attempt_reason", sa.String(120)),
        sa.Column("setup_completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("workspace_id", "ordinal", name="uq_chart_watchlist_member_order"),
        sa.CheckConstraint("ordinal >= 0 AND ordinal < 100", name="member_order"),
        sa.CheckConstraint("kind IN ('INDEX', 'ETF')", name="member_kind"),
        sa.CheckConstraint(
            "(kind = 'INDEX' AND listing_id IS NULL) OR "
            "(kind = 'ETF' AND market_reference_id IS NULL)",
            name="member_owner_kind",
        ),
        sa.CheckConstraint(
            "(created_mapping_id IS NULL AND created_mapping_version IS NULL) OR "
            "(created_mapping_id IS NOT NULL AND created_mapping_version >= 1)",
            name="created_mapping_evidence",
        ),
        sa.CheckConstraint(
            "(verified_mapping_id IS NULL AND verified_mapping_version IS NULL "
            "AND verified_provider_symbol IS NULL AND verified_provider_exchange_code IS NULL "
            "AND setup_completed_at IS NULL) OR "
            "(verified_mapping_id IS NOT NULL AND verified_mapping_version >= 1 "
            "AND verified_provider_symbol IS NOT NULL "
            "AND verified_provider_exchange_code IS NOT NULL AND setup_completed_at IS NOT NULL)",
            name="verified_mapping_evidence",
        ),
    )
    op.execute("""
    CREATE FUNCTION guard_chart_watchlist_member_scope() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP='UPDATE' AND (
        NEW.workspace_id IS DISTINCT FROM OLD.workspace_id
        OR NEW.code IS DISTINCT FROM OLD.code OR NEW.kind IS DISTINCT FROM OLD.kind
        OR NEW.ordinal IS DISTINCT FROM OLD.ordinal
        OR NEW.definition::jsonb IS DISTINCT FROM OLD.definition::jsonb
      ) THEN
        RAISE EXCEPTION 'Activated chart member identity and source snapshot are immutable'
          USING ERRCODE='23514', CONSTRAINT='chart_watchlist_definition_immutable';
      END IF;
      IF NEW.listing_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM listings WHERE id=NEW.listing_id AND workspace_id=NEW.workspace_id
      ) THEN
        RAISE EXCEPTION 'Chart watchlist listing belongs to another workspace'
          USING ERRCODE='23503', CONSTRAINT='chart_watchlist_listing_scope';
      END IF;
      IF NEW.market_reference_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM market_references
        WHERE id=NEW.market_reference_id AND workspace_id=NEW.workspace_id
      ) THEN
        RAISE EXCEPTION 'Chart watchlist reference belongs to another workspace'
          USING ERRCODE='23503', CONSTRAINT='chart_watchlist_reference_scope';
      END IF;
      RETURN NEW;
    END $$;
    """)
    op.execute("""
    CREATE TRIGGER trg_chart_watchlist_member_scope
      BEFORE INSERT OR UPDATE ON chart_watchlist_members
      FOR EACH ROW EXECUTE FUNCTION guard_chart_watchlist_member_scope();
    """)
    op.execute("""
    CREATE FUNCTION guard_chart_watchlist_mapping_scope() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE bound_mapping_id uuid;
    BEGIN
      FOREACH bound_mapping_id IN ARRAY ARRAY[NEW.created_mapping_id,NEW.verified_mapping_id]
      LOOP
        IF bound_mapping_id IS NOT NULL AND NOT EXISTS (
          SELECT 1 FROM provider_instrument_mappings AS mapping
          JOIN market_data_instruments AS instrument
            ON instrument.id=mapping.market_data_instrument_id
          WHERE mapping.id=bound_mapping_id AND mapping.workspace_id=NEW.workspace_id
            AND instrument.workspace_id=NEW.workspace_id
            AND (
              (NEW.kind='ETF' AND mapping.listing_id=NEW.listing_id
                AND instrument.listing_id=NEW.listing_id
                AND instrument.market_reference_id IS NULL)
              OR (NEW.kind='INDEX' AND mapping.listing_id IS NULL
                AND instrument.listing_id IS NULL
                AND instrument.market_reference_id=NEW.market_reference_id)
            )
        ) THEN
          RAISE EXCEPTION 'Chart watchlist mapping owner does not match its workspace and member'
            USING ERRCODE='23503', CONSTRAINT='chart_watchlist_mapping_scope';
        END IF;
      END LOOP;
      RETURN NEW;
    END $$;
    """)
    op.execute("""
    CREATE CONSTRAINT TRIGGER trg_chart_watchlist_mapping_scope
      AFTER INSERT OR UPDATE ON chart_watchlist_members DEFERRABLE INITIALLY DEFERRED
      FOR EACH ROW EXECUTE FUNCTION guard_chart_watchlist_mapping_scope();
    """)


def downgrade() -> None:
    op.execute("""
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM chart_watchlists) THEN
        RAISE EXCEPTION 'Refusing downgrade: activated chart membership would be lost';
      END IF;
    END $$;
    """)
    op.drop_table("chart_watchlist_members")
    op.execute("DROP FUNCTION guard_chart_watchlist_mapping_scope()")
    op.execute("DROP FUNCTION guard_chart_watchlist_member_scope()")
    op.drop_table("chart_watchlists")
