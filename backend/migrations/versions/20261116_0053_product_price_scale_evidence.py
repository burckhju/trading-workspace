"""Immutable product price-scale source documents, without position mutations.

Revision ID: 20261116_0053
Revises: 20261115_0052
"""

import sqlalchemy as sa
from alembic import op

revision = "20261116_0053"
down_revision = "20261115_0052"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_price_scale_evidence",
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
            "terms_id",
            sa.Uuid(),
            sa.ForeignKey("warrant_terms_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column(
            "supersedes_revision_id",
            sa.Uuid(),
            sa.ForeignKey("product_price_scale_evidence.id", ondelete="RESTRICT"),
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
        sa.UniqueConstraint("workspace_id", "request_id", name="uq_product_price_scale_request"),
        sa.UniqueConstraint("supersedes_revision_id", name="uq_product_price_scale_successor"),
        sa.UniqueConstraint(
            "workspace_id",
            "warrant_id",
            "revision_number",
            name="uq_product_price_scale_revision",
        ),
        sa.CheckConstraint("revision_number >= 1", name="product_price_scale_revision_positive"),
        sa.CheckConstraint("id <> supersedes_revision_id", name="product_price_scale_not_self"),
        sa.CheckConstraint(
            "length(manifest_sha256) = 64 AND length(document_sha256) = 64 "
            "AND length(request_fingerprint) = 64",
            name="product_price_scale_hash_lengths",
        ),
    )
    op.create_index(
        "uq_product_price_scale_root",
        "product_price_scale_evidence",
        ["workspace_id", "warrant_id"],
        unique=True,
        postgresql_where=sa.text("supersedes_revision_id IS NULL"),
        sqlite_where=sa.text("supersedes_revision_id IS NULL"),
    )
    op.create_index(
        "ix_product_price_scale_history",
        "product_price_scale_evidence",
        ["workspace_id", "warrant_id", "recorded_at"],
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
        CREATE FUNCTION guard_product_price_scale_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE
            manifest jsonb;
            binding jsonb;
            provenance jsonb;
            previous product_price_scale_evidence%ROWTYPE;
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'Product price scale evidence is append-only'
                    USING ERRCODE = '23514';
            END IF;
            IF octet_length(NEW.manifest_json) NOT BETWEEN 1 AND 64000
               OR octet_length(NEW.document_bytes) NOT BETWEEN 1 AND 2000000
               OR NEW.manifest_sha256 !~ '^[0-9a-f]{64}$'
               OR NEW.document_sha256 !~ '^[0-9a-f]{64}$'
               OR NEW.request_fingerprint !~ '^[0-9a-f]{64}$'
               OR encode(sha256(convert_to(NEW.manifest_json, 'UTF8')), 'hex')
                    <> NEW.manifest_sha256
               OR encode(sha256(NEW.document_bytes), 'hex') <> NEW.document_sha256 THEN
                RAISE EXCEPTION 'Product price scale original hash or size mismatch'
                    USING ERRCODE = '23514';
            END IF;
            manifest := NEW.manifest_json::jsonb;
            binding := manifest->'binding';
            provenance := NEW.source::jsonb;
            IF jsonb_typeof(manifest) IS DISTINCT FROM 'object'
               OR jsonb_typeof(binding) IS DISTINCT FROM 'object'
               OR jsonb_typeof(provenance) IS DISTINCT FROM 'object'
               OR COALESCE(manifest->>'schema_version', 'product-price-scale-evidence-v1')
                    <> 'product-price-scale-evidence-v1'
               OR (manifest->>'axis') IS DISTINCT FROM 'WARRANT'
               OR (manifest->>'unit') IS DISTINCT FROM 'CURRENCY_PER_WARRANT'
               OR COALESCE(manifest->>'status', '') NOT IN
                    ('UNCHANGED_ORIGINAL', 'ADJUSTMENT_REQUIRED', 'WITHDRAWN')
               OR COALESCE(manifest->>'currency', '') !~ '^[A-Z]{3}$'
               OR COALESCE(binding->>'isin', '') !~ '^[A-Z]{2}[A-Z0-9]{9}[0-9]$'
               OR (binding->>'warrant_id')::uuid IS DISTINCT FROM NEW.warrant_id
               OR (binding->>'current_terms_id')::uuid IS DISTINCT FROM NEW.terms_id
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
               OR (manifest->>'source_published_at' IS NOT NULL
                    AND manifest->>'source_published_on' IS NOT NULL)
               OR length(trim(COALESCE(provenance->>'review_reference', ''))) NOT BETWEEN 3 AND 1000
               OR length(trim(COALESCE(provenance->>'document_filename', ''))) NOT BETWEEN 3 AND 255
               OR COALESCE(provenance->>'document_media_type', '') NOT IN
                    ('application/pdf','application/json','text/csv','text/plain','text/html')
               OR COALESCE(manifest->>'valid_from', '') !~ '(Z|[+-][0-9]{2}:[0-9]{2})$'
               OR COALESCE(manifest->>'valid_until', '') !~ '(Z|[+-][0-9]{2}:[0-9]{2})$'
               OR (manifest->>'valid_from')::timestamptz >= (manifest->>'valid_until')::timestamptz
               OR extract(year FROM (manifest->>'valid_until')::timestamptz) >= 9999
               OR (provenance->>'reviewed_at') IS NULL
               OR (provenance->>'reviewed_at')::timestamptz > NEW.recorded_at
               OR (provenance->>'retrieved_at')::timestamptz > NEW.recorded_at
               OR (manifest->>'source_published_at')::timestamptz
                    > (provenance->>'reviewed_at')::timestamptz THEN
                RAISE EXCEPTION 'Product price scale manifest or provenance scope mismatch'
                    USING ERRCODE = '23514';
            END IF;
            PERFORM 1 FROM warrants w WHERE w.id = NEW.warrant_id
                AND w.workspace_id = NEW.workspace_id FOR UPDATE;
            IF NOT FOUND OR NOT EXISTS (
                SELECT 1 FROM warrants w JOIN warrant_terms_versions t ON t.warrant_id = w.id
                WHERE w.id = NEW.warrant_id AND w.workspace_id = NEW.workspace_id
                  AND w.isin = binding->>'isin'
                  AND w.issuer_id = (binding->>'issuer_id')::uuid
                  AND w.underlying_id = (binding->>'underlying_id')::uuid
                  AND t.id = NEW.terms_id AND t.effective_to IS NULL
                  AND t.created_at <= NEW.recorded_at AND t.effective_from <= NEW.recorded_at
            ) THEN
                RAISE EXCEPTION 'Product price scale product or terms binding mismatch'
                    USING ERRCODE = '23514';
            END IF;
            IF NEW.supersedes_revision_id IS NULL THEN
                IF NEW.revision_number <> 1 THEN
                    RAISE EXCEPTION 'Product price scale root revision mismatch'
                        USING ERRCODE = '23514';
                END IF;
            ELSE
                SELECT * INTO previous FROM product_price_scale_evidence
                    WHERE id = NEW.supersedes_revision_id;
                IF NOT FOUND OR previous.workspace_id <> NEW.workspace_id
                   OR previous.warrant_id <> NEW.warrant_id
                   OR previous.revision_number + 1 <> NEW.revision_number
                   OR previous.recorded_at > NEW.recorded_at THEN
                    RAISE EXCEPTION 'Product price scale predecessor scope or time mismatch'
                        USING ERRCODE = '23514';
                END IF;
            END IF;
            RETURN NEW;
        END $$
        """)
        op.execute("""
        CREATE TRIGGER trg_product_price_scale_evidence_guard
            BEFORE INSERT OR UPDATE OR DELETE ON product_price_scale_evidence
            FOR EACH ROW EXECUTE FUNCTION guard_product_price_scale_evidence()
        """)
        op.execute("""
        CREATE TRIGGER trg_product_price_scale_evidence_no_truncate
            BEFORE TRUNCATE ON product_price_scale_evidence
            FOR EACH STATEMENT EXECUTE FUNCTION guard_product_price_scale_evidence()
        """)


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT 1 FROM product_price_scale_evidence LIMIT 1")):
        raise RuntimeError("Cannot downgrade: immutable product price scale evidence exists")
    op.drop_table("product_price_scale_evidence")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION guard_product_price_scale_evidence()")
