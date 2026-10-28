"""Reviewed historical currency sources, without inferred data or execution writes.

Revision ID: 20261028_0048
Revises: 20261017_0047
"""

import sqlalchemy as sa
from alembic import op

revision = "20261028_0048"
down_revision = "20261017_0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "currency_source_evidence",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Uuid(),
            sa.ForeignKey("warrants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("source_reference", sa.String(1000), nullable=False),
        sa.Column("verification", sa.String(32), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), nullable=False),
        sa.Column(
            "supersedes_evidence_id",
            sa.Uuid(),
            sa.ForeignKey("currency_source_evidence.id", ondelete="RESTRICT"),
        ),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("trade_id", sa.Uuid(), sa.ForeignKey("trades.id", ondelete="RESTRICT")),
        sa.Column(
            "execution_id",
            sa.Uuid(),
            sa.ForeignKey("execution_records.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "currency_code",
            sa.String(3),
            sa.ForeignKey("currencies.code", ondelete="RESTRICT"),
        ),
        sa.Column(
            "trading_venue_id",
            sa.Uuid(),
            sa.ForeignKey("trading_venues.id", ondelete="RESTRICT"),
        ),
        sa.Column("valid_from", sa.DateTime(timezone=True)),
        sa.Column("valid_to", sa.DateTime(timezone=True)),
        sa.Column("listings", sa.JSON(), nullable=False),
        sa.Column("complete_listing_set", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("workspace_id", "request_id", name="uq_currency_evidence_request"),
        sa.UniqueConstraint("supersedes_evidence_id", name="uq_currency_evidence_successor"),
        sa.CheckConstraint(
            "kind IN ('EXECUTION_DOCUMENT','HISTORICAL_LISTINGS')",
            name="currency_evidence_kind",
        ),
        sa.CheckConstraint(
            "verification = 'USER_VERIFIED_SOURCE'",
            name="currency_evidence_verification",
        ),
        sa.CheckConstraint(
            "length(trim(source_reference)) BETWEEN 3 AND 1000",
            name="currency_evidence_reference",
        ),
        sa.CheckConstraint("id <> supersedes_evidence_id", name="currency_evidence_not_self"),
        sa.CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="currency_evidence_fingerprint",
        ),
        sa.CheckConstraint(
            "(kind = 'EXECUTION_DOCUMENT' AND trade_id IS NOT NULL AND execution_id IS NOT NULL "
            "AND (currency_code IS NOT NULL OR trading_venue_id IS NOT NULL) "
            "AND valid_from IS NULL AND valid_to IS NULL AND NOT complete_listing_set) OR "
            "(kind = 'HISTORICAL_LISTINGS' AND trade_id IS NULL AND execution_id IS NULL "
            "AND currency_code IS NULL AND trading_venue_id IS NULL AND valid_from IS NOT NULL "
            "AND valid_to IS NOT NULL AND valid_from < valid_to)",
            name="currency_evidence_shape",
        ),
    )
    op.create_index(
        "ix_currency_evidence_product_time",
        "currency_source_evidence",
        ["workspace_id", "product_id", "recorded_at"],
    )
    # Derived reference rows protect historical venue/currency identities from hard deletion.
    # The parent remains the sole source fact; its AFTER INSERT trigger populates these rows.
    op.create_table(
        "currency_source_evidence_listing_refs",
        sa.Column(
            "evidence_id",
            sa.Uuid(),
            sa.ForeignKey("currency_source_evidence.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "trading_venue_id",
            sa.Uuid(),
            sa.ForeignKey("trading_venues.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "currency_code",
            sa.String(3),
            sa.ForeignKey("currencies.code", ondelete="RESTRICT"),
        ),
    )
    op.execute("""
    CREATE FUNCTION guard_currency_source_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE previous currency_source_evidence; item jsonb; venue uuid;
      seen uuid[] := '{}'; cancelled timestamptz;
    BEGIN
      IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'currency source evidence is immutable'
          USING ERRCODE='23514', CONSTRAINT='tw_currency_evidence_immutable';
      END IF;
      PERFORM id FROM warrants WHERE id=NEW.product_id AND workspace_id=NEW.workspace_id FOR UPDATE;
      IF NOT FOUND THEN
        RAISE EXCEPTION 'currency evidence product/workspace mismatch'
          USING ERRCODE='23503', CONSTRAINT='tw_currency_evidence_product_scope';
      END IF;
      IF NEW.kind = 'EXECUTION_DOCUMENT' THEN
        SELECT cancelled_at INTO cancelled FROM trades
          WHERE id=NEW.trade_id AND workspace_id=NEW.workspace_id
            AND product_id=NEW.product_id FOR UPDATE;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'currency evidence trade scope mismatch'
            USING ERRCODE='23503', CONSTRAINT='tw_currency_evidence_execution_scope';
        END IF;
        IF cancelled IS NOT NULL THEN
          RAISE EXCEPTION 'cancelled trade cannot receive currency evidence'
            USING ERRCODE='23514', CONSTRAINT='tw_currency_evidence_cancelled';
        END IF;
        PERFORM id FROM execution_records
          WHERE id=NEW.execution_id AND trade_id=NEW.trade_id AND product_id=NEW.product_id;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'currency evidence execution scope mismatch'
            USING ERRCODE='23503', CONSTRAINT='tw_currency_evidence_execution_scope';
        END IF;
      END IF;
      IF NEW.supersedes_evidence_id IS NOT NULL THEN
        SELECT * INTO previous FROM currency_source_evidence WHERE id=NEW.supersedes_evidence_id;
        IF NOT FOUND OR previous.workspace_id <> NEW.workspace_id
           OR previous.product_id <> NEW.product_id
           OR previous.kind <> NEW.kind OR previous.trade_id IS DISTINCT FROM NEW.trade_id
           OR previous.execution_id IS DISTINCT FROM NEW.execution_id THEN
          RAISE EXCEPTION 'currency evidence predecessor scope mismatch'
            USING ERRCODE='23503', CONSTRAINT='tw_currency_evidence_predecessor_scope';
        END IF;
        IF NEW.recorded_at < previous.recorded_at THEN
          RAISE EXCEPTION 'currency evidence predecessor chronology mismatch'
            USING ERRCODE='23514', CONSTRAINT='tw_currency_evidence_chronology';
        END IF;
      ELSIF NEW.revoked THEN
        RAISE EXCEPTION 'currency evidence revocation requires predecessor'
          USING ERRCODE='23514', CONSTRAINT='tw_currency_evidence_revocation';
      END IF;
      IF jsonb_typeof(NEW.listings::jsonb) IS DISTINCT FROM 'array'
         OR (NEW.kind='EXECUTION_DOCUMENT' AND jsonb_array_length(NEW.listings::jsonb) <> 0)
         OR (NEW.kind='HISTORICAL_LISTINGS' AND
             jsonb_array_length(NEW.listings::jsonb) NOT BETWEEN 1 AND 100) THEN
        RAISE EXCEPTION 'currency evidence listing shape invalid'
          USING ERRCODE='23514', CONSTRAINT='tw_currency_evidence_listings';
      END IF;
      FOR item IN SELECT value FROM jsonb_array_elements(NEW.listings::jsonb) LOOP
        IF jsonb_typeof(item) IS DISTINCT FROM 'object'
           OR NOT item ? 'currency_code' OR NOT item ? 'trading_venue_id'
           OR (SELECT count(*) FROM jsonb_object_keys(item)) <> 2
           OR jsonb_typeof(item->'trading_venue_id') IS DISTINCT FROM 'string'
           OR (item->'currency_code' <> 'null'::jsonb AND
               (jsonb_typeof(item->'currency_code') IS DISTINCT FROM 'string' OR
                item->>'currency_code' !~ '^[A-Z]{3}$')) THEN
          RAISE EXCEPTION 'currency evidence listing value invalid'
            USING ERRCODE='23514', CONSTRAINT='tw_currency_evidence_listings';
        END IF;
        venue := (item->>'trading_venue_id')::uuid;
        IF venue = ANY(seen) THEN
          RAISE EXCEPTION 'currency evidence duplicate venue'
            USING ERRCODE='23514', CONSTRAINT='tw_currency_evidence_listings';
        END IF;
        seen := array_append(seen, venue);
      END LOOP;
      RETURN NEW;
    END $$;
    """)
    op.execute("""
    CREATE TRIGGER trg_currency_source_evidence BEFORE INSERT OR UPDATE OR DELETE
      ON currency_source_evidence FOR EACH ROW EXECUTE FUNCTION guard_currency_source_evidence();
    """)
    op.execute("""
    CREATE FUNCTION currency_source_evidence_references() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      INSERT INTO currency_source_evidence_listing_refs(evidence_id,trading_venue_id,currency_code)
        SELECT NEW.id,(item->>'trading_venue_id')::uuid,item->>'currency_code'
        FROM jsonb_array_elements(NEW.listings::jsonb) AS item;
      RETURN NEW;
    END $$;
    """)
    op.execute("""
    CREATE TRIGGER trg_currency_source_evidence_references AFTER INSERT ON currency_source_evidence
      FOR EACH ROW EXECUTE FUNCTION currency_source_evidence_references();
    """)
    op.execute("""
    CREATE FUNCTION guard_currency_source_evidence_reference()
      RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP <> 'INSERT' OR pg_trigger_depth() < 2 THEN
        RAISE EXCEPTION 'currency source evidence reference is immutable'
          USING ERRCODE='23514', CONSTRAINT='tw_currency_evidence_reference_immutable';
      END IF;
      RETURN NEW;
    END $$;
    """)
    op.execute("""
    CREATE TRIGGER trg_currency_source_evidence_reference_guard BEFORE INSERT OR UPDATE OR DELETE
      ON currency_source_evidence_listing_refs FOR EACH ROW
      EXECUTE FUNCTION guard_currency_source_evidence_reference();
    """)


def downgrade() -> None:
    op.execute("""
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM currency_source_evidence) THEN
        RAISE EXCEPTION 'Refusing downgrade: currency source evidence would be lost';
      END IF;
    END $$;
    """)
    op.drop_table("currency_source_evidence_listing_refs")
    op.drop_table("currency_source_evidence")
    op.execute("DROP FUNCTION guard_currency_source_evidence_reference()")
    op.execute("DROP FUNCTION currency_source_evidence_references()")
    op.execute("DROP FUNCTION guard_currency_source_evidence()")
