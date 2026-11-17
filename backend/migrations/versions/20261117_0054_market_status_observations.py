"""Independent original market-status observations and explicit delivery gaps.

Revision ID: 20261117_0054
Revises: 20261116_0053
"""

import sqlalchemy as sa
from alembic import op

revision = "20261117_0054"
down_revision = "20261116_0053"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "warrant_market_status_observations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "warrant_id",
            sa.Uuid(),
            sa.ForeignKey("warrants.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "warrant_listing_id",
            sa.Uuid(),
            sa.ForeignKey("warrant_listings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("identity_key", sa.String(64), nullable=False),
        sa.Column("isin", sa.String(12), nullable=False),
        sa.Column("venue_mic", sa.String(4), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True)),
        sa.Column("retrieved_at", sa.DateTime(timezone=True)),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_contract", sa.String(100)),
        sa.Column("source_reference", sa.String(200)),
        sa.Column("original", sa.JSON(none_as_null=True)),
        sa.Column("reason", sa.String(140)),
        sa.UniqueConstraint("workspace_id", "fingerprint", name="uq_warrant_status_fact"),
        sa.CheckConstraint("kind IN ('STATUS','GAP')", name="warrant_status_kind"),
        sa.CheckConstraint(
            "(kind = 'STATUS' AND observed_at IS NOT NULL AND original IS NOT NULL "
            "AND retrieved_at IS NOT NULL AND reason IS NULL) OR "
            "(kind = 'GAP' AND observed_at IS NULL AND original IS NULL AND reason IS NOT NULL)",
            name="warrant_status_payload_kind",
        ),
        sa.CheckConstraint("retrieved_at <= captured_at", name="warrant_status_receipt_order"),
        sa.CheckConstraint("observed_at <= retrieved_at", name="warrant_status_original_order"),
    )
    op.create_index(
        "ix_warrant_status_route_event",
        "warrant_market_status_observations",
        ["workspace_id", "warrant_listing_id", "provider", "identity_key", "observed_at"],
    )
    op.create_index(
        "ix_warrant_status_capture",
        "warrant_market_status_observations",
        ["workspace_id", "warrant_listing_id", "captured_at"],
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
        CREATE FUNCTION guard_warrant_market_status_observations()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE evidence jsonb;
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'Original market status observations are append-only'
                    USING ERRCODE = '23514';
            END IF;
            IF NEW.identity_key !~ '^[0-9a-f]{64}$'
               OR NEW.fingerprint !~ '^[0-9a-f]{64}$'
               OR NOT EXISTS (
                   SELECT 1 FROM warrant_listings l JOIN warrants w ON w.id=l.warrant_id
                   JOIN trading_venues v ON v.id=l.trading_venue_id
                   WHERE l.id=NEW.warrant_listing_id AND l.warrant_id=NEW.warrant_id
                     AND l.workspace_id=NEW.workspace_id AND w.workspace_id=NEW.workspace_id
                     AND w.isin=NEW.isin AND v.mic=NEW.venue_mic
               ) THEN
                RAISE EXCEPTION 'Original market status route mismatch'
                    USING ERRCODE = '23514';
            END IF;
            IF NEW.kind = 'STATUS' THEN
                evidence := NEW.original::jsonb;
                IF jsonb_typeof(evidence) IS DISTINCT FROM 'object'
                   OR (evidence->>'version') IS DISTINCT FROM 'original-market-status-evidence-v1'
                   OR (evidence->>'isin') IS DISTINCT FROM NEW.isin
                   OR (evidence->>'venue_mic') IS DISTINCT FROM NEW.venue_mic
                   OR (evidence->>'source_contract') IS DISTINCT FROM NEW.source_contract
                   OR (evidence->>'source_reference') IS DISTINCT FROM NEW.source_reference
                   OR (evidence->>'observed_at')::timestamptz IS DISTINCT FROM NEW.observed_at
                   OR (evidence->>'generated_at')::timestamptz > NEW.retrieved_at
                   OR (evidence->>'generated_at') IS NULL
                   OR (evidence->>'observed_at')::timestamptz >
                        (evidence->>'generated_at')::timestamptz
                   OR COALESCE(evidence->>'status','') NOT IN ('OPEN','CLOSED','SUSPENDED','UNKNOWN')
                   OR (evidence->>'original_status_text') IS DISTINCT FROM (evidence->>'status')
                   OR (evidence->>'original_time_text')::timestamptz IS DISTINCT FROM NEW.observed_at
                   OR (evidence->>'time_basis') IS DISTINCT FROM 'SEPARATE_STATUS_TIMESTAMP'
                   OR (evidence->>'temporal_meaning') IS DISTINCT FROM 'OBSERVED_AT_INSTANT' THEN
                    RAISE EXCEPTION 'Original market status evidence mismatch'
                        USING ERRCODE = '23514';
                END IF;
            END IF;
            RETURN NEW;
        END $$
        """)
        op.execute("""
        CREATE TRIGGER trg_warrant_market_status_guard
          BEFORE INSERT OR UPDATE OR DELETE ON warrant_market_status_observations
          FOR EACH ROW EXECUTE FUNCTION guard_warrant_market_status_observations()
        """)
        op.execute("""
        CREATE TRIGGER trg_warrant_market_status_no_truncate
          BEFORE TRUNCATE ON warrant_market_status_observations
          FOR EACH STATEMENT EXECUTE FUNCTION guard_warrant_market_status_observations()
        """)


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT 1 FROM warrant_market_status_observations LIMIT 1")):
        raise RuntimeError("Cannot downgrade: immutable market status observations exist")
    op.drop_table("warrant_market_status_observations")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION guard_warrant_market_status_observations()")
