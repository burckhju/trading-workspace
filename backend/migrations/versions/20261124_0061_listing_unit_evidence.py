"""Append-only current listing-unit originals; no rule activation or history rewrite.

Revision ID: 20261124_0061
Revises: 20261118_0060
"""

import sqlalchemy as sa
from alembic import op

revision = "20261124_0061"
down_revision = "20261118_0060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_listing_unit_evidence",
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
            "listing_id",
            sa.Uuid(),
            sa.ForeignKey("warrant_listings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "terms_id",
            sa.Uuid(),
            sa.ForeignKey("warrant_terms_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "previous_revision_id",
            sa.Uuid(),
            sa.ForeignKey("product_listing_unit_evidence.id", ondelete="RESTRICT"),
        ),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column(
            "kid_revision_id",
            sa.Uuid(),
            sa.ForeignKey("product_review_documents.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("kid_document_sha256", sa.String(64), nullable=False),
        sa.Column("product_class", sa.String(80), nullable=False),
        sa.Column("binding", sa.JSON(), nullable=False),
        sa.Column("source", sa.JSON(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("review_reference", sa.Text(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), nullable=False),
        sa.CheckConstraint("revision_number > 0", name="listing_unit_revision_positive"),
        sa.CheckConstraint("id <> previous_revision_id", name="listing_unit_not_self"),
        sa.CheckConstraint(
            "length(request_fingerprint)=64 AND length(kid_document_sha256)=64",
            name="listing_unit_hash_lengths",
        ),
    )
    op.create_index(
        "uq_listing_unit_root",
        "product_listing_unit_evidence",
        ["workspace_id", "listing_id"],
        unique=True,
        postgresql_where=sa.text("previous_revision_id IS NULL"),
        sqlite_where=sa.text("previous_revision_id IS NULL"),
    )
    op.create_index(
        "uq_listing_unit_successor",
        "product_listing_unit_evidence",
        ["previous_revision_id"],
        unique=True,
    )
    op.create_index(
        "uq_listing_unit_revision",
        "product_listing_unit_evidence",
        ["workspace_id", "listing_id", "revision_number"],
        unique=True,
    )
    op.create_index(
        "uq_listing_unit_request",
        "product_listing_unit_evidence",
        ["workspace_id", "request_id"],
        unique=True,
    )
    op.create_index(
        "ix_listing_unit_history",
        "product_listing_unit_evidence",
        ["workspace_id", "listing_id", "recorded_at"],
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
        CREATE FUNCTION guard_listing_unit_original() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP <> 'INSERT' THEN
            RAISE EXCEPTION 'Current listing unit originals are append-only'
              USING ERRCODE='23514';
          END IF;
          IF NOT EXISTS (
            SELECT 1 FROM warrants w
            JOIN warrant_listings l ON l.warrant_id=w.id AND l.workspace_id=w.workspace_id
            JOIN warrant_terms_versions t ON t.warrant_id=w.id
            JOIN product_review_documents d ON d.warrant_id=w.id AND d.workspace_id=w.workspace_id
            WHERE w.id=NEW.warrant_id AND w.workspace_id=NEW.workspace_id
              AND l.id=NEW.listing_id AND t.id=NEW.terms_id
              AND d.id=NEW.kid_revision_id AND d.kind='KID' AND d.terms_id=NEW.terms_id
              AND d.document_sha256=NEW.kid_document_sha256
              AND d.recorded_at<=NEW.recorded_at
          ) OR NEW.reviewed_at>NEW.recorded_at THEN
            RAISE EXCEPTION 'Current listing unit scope or original clock mismatch'
              USING ERRCODE='23514';
          END IF;
          IF NOT COALESCE(
            NEW.binding::jsonb->'product'->>'warrant_id'=NEW.warrant_id::text
            AND NEW.binding::jsonb->'product'->>'current_terms_id'=NEW.terms_id::text
            AND NEW.binding::jsonb->'route'->>'listing_id'=NEW.listing_id::text,
            FALSE
          ) THEN
            RAISE EXCEPTION 'Current listing unit binding mismatch' USING ERRCODE='23514';
          END IF;
          IF (NEW.previous_revision_id IS NULL AND NEW.revision_number<>1)
            OR (NEW.previous_revision_id IS NOT NULL AND NOT EXISTS (
              SELECT 1 FROM product_listing_unit_evidence previous
              WHERE previous.id=NEW.previous_revision_id
                AND previous.workspace_id=NEW.workspace_id
                AND previous.warrant_id=NEW.warrant_id
                AND previous.listing_id=NEW.listing_id
                AND previous.revision_number+1=NEW.revision_number
                AND previous.recorded_at<=NEW.recorded_at
            )) THEN
            RAISE EXCEPTION 'Current listing unit revision mismatch' USING ERRCODE='23514';
          END IF;
          RETURN NEW;
        END $$
        """)
        op.execute("""
        CREATE TRIGGER listing_unit_original_guard
          BEFORE INSERT OR UPDATE OR DELETE ON product_listing_unit_evidence
          FOR EACH ROW EXECUTE FUNCTION guard_listing_unit_original()
        """)
        op.execute("""
        CREATE TRIGGER listing_unit_no_truncate BEFORE TRUNCATE ON product_listing_unit_evidence
          FOR EACH STATEMENT EXECUTE FUNCTION guard_listing_unit_original()
        """)


def downgrade() -> None:
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT count(*) FROM product_listing_unit_evidence")):
        raise RuntimeError("Refusing to remove recorded current listing-unit originals")
    if connection.dialect.name == "postgresql":
        op.execute("DROP FUNCTION guard_listing_unit_original() CASCADE")
    op.drop_table("product_listing_unit_evidence")
