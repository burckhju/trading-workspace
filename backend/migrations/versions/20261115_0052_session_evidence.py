"""Immutable, scoped original session manifests and source documents.

Revision ID: 20261115_0052
Revises: 20261114_0051
"""

import sqlalchemy as sa
from alembic import op

revision = "20261115_0052"
down_revision = "20261114_0051"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_session_evidence",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("instrument_kind", sa.String(16), nullable=False),
        sa.Column("instrument_id", sa.Uuid(), nullable=False),
        sa.Column("underlying_id", sa.Uuid(), sa.ForeignKey("underlyings.id", ondelete="RESTRICT")),
        sa.Column("warrant_id", sa.Uuid(), sa.ForeignKey("warrants.id", ondelete="RESTRICT")),
        sa.Column("listing_id", sa.Uuid(), sa.ForeignKey("listings.id", ondelete="RESTRICT")),
        sa.Column(
            "warrant_listing_id",
            sa.Uuid(),
            sa.ForeignKey("warrant_listings.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "trading_venue_id",
            sa.Uuid(),
            sa.ForeignKey("trading_venues.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column(
            "supersedes_revision_id",
            sa.Uuid(),
            sa.ForeignKey("market_session_evidence.id", ondelete="RESTRICT"),
        ),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), nullable=False),
        sa.Column("manifest_json", sa.Text(), nullable=False),
        sa.Column("manifest_sha256", sa.String(64), nullable=False),
        sa.Column("document_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("document_sha256", sa.String(64), nullable=False),
        sa.Column("source", sa.JSON(), nullable=False),
        sa.UniqueConstraint("workspace_id", "request_id", name="uq_session_evidence_request"),
        sa.UniqueConstraint("supersedes_revision_id", name="uq_session_evidence_successor"),
        sa.UniqueConstraint(
            "workspace_id",
            "instrument_kind",
            "instrument_id",
            "revision_number",
            name="uq_session_evidence_revision",
        ),
        sa.CheckConstraint("revision_number >= 1", name="session_evidence_revision_positive"),
        sa.CheckConstraint("id <> supersedes_revision_id", name="session_evidence_not_self"),
        sa.CheckConstraint(
            "(instrument_kind = 'UNDERLYING' AND underlying_id = instrument_id "
            "AND underlying_id IS NOT NULL AND listing_id IS NOT NULL "
            "AND warrant_id IS NULL AND warrant_listing_id IS NULL) OR "
            "(instrument_kind = 'WARRANT' AND warrant_id = instrument_id "
            "AND warrant_id IS NOT NULL AND warrant_listing_id IS NOT NULL "
            "AND underlying_id IS NULL AND listing_id IS NULL)",
            name="session_evidence_owner_matches_kind",
        ),
        sa.CheckConstraint(
            "length(manifest_sha256) = 64 AND length(document_sha256) = 64 "
            "AND length(request_fingerprint) = 64",
            name="session_evidence_hash_lengths",
        ),
    )
    op.create_index(
        "uq_session_evidence_root",
        "market_session_evidence",
        ["workspace_id", "instrument_kind", "instrument_id"],
        unique=True,
        postgresql_where=sa.text("supersedes_revision_id IS NULL"),
        sqlite_where=sa.text("supersedes_revision_id IS NULL"),
    )
    op.create_index(
        "ix_session_evidence_history",
        "market_session_evidence",
        ["workspace_id", "instrument_kind", "instrument_id", "recorded_at"],
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
        CREATE FUNCTION guard_market_session_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            manifest jsonb;
            binding jsonb;
            provenance jsonb;
            previous market_session_evidence%ROWTYPE;
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'Session evidence is append-only' USING ERRCODE = '23514';
            END IF;
            IF octet_length(NEW.manifest_json) NOT BETWEEN 1 AND 2000000
               OR octet_length(NEW.document_bytes) NOT BETWEEN 1 AND 2000000
               OR NEW.manifest_sha256 !~ '^[0-9a-f]{64}$'
               OR NEW.document_sha256 !~ '^[0-9a-f]{64}$'
               OR NEW.request_fingerprint !~ '^[0-9a-f]{64}$'
               OR encode(sha256(convert_to(NEW.manifest_json, 'UTF8')), 'hex')
                    <> NEW.manifest_sha256
               OR encode(sha256(NEW.document_bytes), 'hex') <> NEW.document_sha256 THEN
                RAISE EXCEPTION 'Session evidence original hash or size mismatch'
                    USING ERRCODE = '23514';
            END IF;
            manifest := NEW.manifest_json::jsonb;
            binding := manifest->'binding';
            provenance := NEW.source::jsonb;
            IF jsonb_typeof(manifest) IS DISTINCT FROM 'object'
               OR jsonb_typeof(binding) IS DISTINCT FROM 'object'
               OR jsonb_typeof(provenance) IS DISTINCT FROM 'object'
               OR COALESCE(manifest->>'schema_version', 'session-evidence-manifest-v1')
                    <> 'session-evidence-manifest-v1'
               OR COALESCE(manifest->>'evidence_status', 'ACTIVE') NOT IN ('ACTIVE','WITHDRAWN')
               OR jsonb_typeof(manifest->'days') IS DISTINCT FROM 'array'
               OR jsonb_array_length(manifest->'days') > 3660
               OR (binding->>'instrument_kind') IS DISTINCT FROM NEW.instrument_kind
               OR (binding->>'instrument_id')::uuid IS DISTINCT FROM NEW.instrument_id
               OR (binding->>'listing_id')::uuid IS DISTINCT FROM
                    COALESCE(NEW.listing_id, NEW.warrant_listing_id)
               OR (binding->>'trading_venue_id')::uuid IS DISTINCT FROM NEW.trading_venue_id
               OR (manifest->>'source_document_sha256') IS DISTINCT FROM NEW.document_sha256
               OR (provenance->>'manifest_sha256') IS DISTINCT FROM NEW.manifest_sha256
               OR (provenance->>'document_sha256') IS DISTINCT FROM NEW.document_sha256
               OR (provenance->>'recorded_by')::uuid IS DISTINCT FROM NEW.recorded_by
               OR (provenance->>'publisher') IS DISTINCT FROM (manifest->>'source_publisher')
               OR (provenance->>'reference') IS DISTINCT FROM (manifest->>'source_reference')
               OR (provenance->>'published_at')::timestamptz IS DISTINCT FROM
                    (manifest->>'source_published_at')::timestamptz
               OR (provenance->>'published_on')::date IS DISTINCT FROM
                    (manifest->>'source_published_on')::date
               OR length(trim(COALESCE(provenance->>'review_reference', ''))) NOT BETWEEN 3 AND 1000
               OR (provenance->>'reviewed_at') IS NULL
               OR (provenance->>'reviewed_at')::timestamptz > NEW.recorded_at
               OR (provenance->>'retrieved_at')::timestamptz > NEW.recorded_at
               OR (manifest->>'source_published_at')::timestamptz
                    > (provenance->>'reviewed_at')::timestamptz THEN
                RAISE EXCEPTION 'Session evidence manifest or provenance scope mismatch'
                    USING ERRCODE = '23514';
            END IF;
            IF NEW.instrument_kind = 'UNDERLYING' THEN
                IF NOT EXISTS (
                    SELECT 1 FROM underlyings u JOIN listings l ON l.underlying_id = u.id
                    WHERE u.id = NEW.instrument_id AND u.workspace_id = NEW.workspace_id
                      AND l.id = NEW.listing_id AND l.workspace_id = NEW.workspace_id
                      AND l.trading_venue_id = NEW.trading_venue_id
                ) THEN
                    RAISE EXCEPTION 'Session evidence underlying listing scope mismatch'
                        USING ERRCODE = '23514';
                END IF;
            ELSIF NEW.instrument_kind = 'WARRANT' THEN
                IF NOT EXISTS (
                    SELECT 1 FROM warrants w JOIN warrant_listings l ON l.warrant_id = w.id
                    WHERE w.id = NEW.instrument_id AND w.workspace_id = NEW.workspace_id
                      AND l.id = NEW.warrant_listing_id AND l.workspace_id = NEW.workspace_id
                      AND l.trading_venue_id = NEW.trading_venue_id
                ) THEN
                    RAISE EXCEPTION 'Session evidence warrant listing scope mismatch'
                        USING ERRCODE = '23514';
                END IF;
            ELSE
                RAISE EXCEPTION 'Session evidence instrument kind mismatch' USING ERRCODE = '23514';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM trading_venues v WHERE v.id = NEW.trading_venue_id
                           AND v.mic = binding->>'venue_mic') THEN
                RAISE EXCEPTION 'Session evidence venue scope mismatch' USING ERRCODE = '23514';
            END IF;
            IF NEW.supersedes_revision_id IS NULL THEN
                IF NEW.revision_number <> 1 THEN
                    RAISE EXCEPTION 'Session evidence root revision mismatch'
                        USING ERRCODE = '23514';
                END IF;
            ELSE
                SELECT * INTO previous FROM market_session_evidence
                    WHERE id = NEW.supersedes_revision_id;
                IF NOT FOUND OR previous.workspace_id <> NEW.workspace_id
                   OR previous.instrument_kind <> NEW.instrument_kind
                   OR previous.instrument_id <> NEW.instrument_id
                   OR previous.revision_number + 1 <> NEW.revision_number
                   OR previous.recorded_at > NEW.recorded_at THEN
                    RAISE EXCEPTION 'Session evidence predecessor scope or time mismatch'
                        USING ERRCODE = '23514';
                END IF;
            END IF;
            RETURN NEW;
        END $$
        """)
        op.execute("""
        CREATE TRIGGER trg_market_session_evidence_guard
            BEFORE INSERT OR UPDATE OR DELETE ON market_session_evidence
            FOR EACH ROW EXECUTE FUNCTION guard_market_session_evidence()
        """)
        op.execute("""
        CREATE TRIGGER trg_market_session_evidence_no_truncate
            BEFORE TRUNCATE ON market_session_evidence
            FOR EACH STATEMENT EXECUTE FUNCTION guard_market_session_evidence()
        """)


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT 1 FROM market_session_evidence LIMIT 1")):
        raise RuntimeError("Cannot downgrade: immutable session evidence exists")
    op.drop_table("market_session_evidence")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION guard_market_session_evidence()")
