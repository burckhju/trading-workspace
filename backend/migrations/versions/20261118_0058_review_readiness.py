"""Add original review documents and finite calendar sources without activation.

Revision ID: 20261118_0058
Revises: 20261117_0057
"""

import sqlalchemy as sa
from alembic import op

revision = "20261118_0058"
down_revision = "20261117_0057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "product_review_documents",
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
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_reference", sa.String(2000), nullable=False),
        sa.Column("document_sha256", sa.String(64), nullable=False),
        sa.Column("document", sa.LargeBinary(), nullable=False),
        sa.Column("binding", sa.JSON(), nullable=False),
        sa.Column("facts", sa.JSON(), nullable=False),
        sa.Column("parser_version", sa.String(80), nullable=False),
        sa.UniqueConstraint(
            "workspace_id",
            "warrant_id",
            "kind",
            "revision_number",
            name="uq_product_review_document_revision",
        ),
        sa.CheckConstraint("revision_number >= 1", name="product_review_revision_positive"),
        sa.CheckConstraint("kind IN ('KID','LISTING_TERMS')", name="product_review_document_kind"),
    )
    op.create_index(
        "ix_product_review_document_history",
        "product_review_documents",
        ["workspace_id", "warrant_id", "kind", "recorded_at"],
    )
    op.create_table(
        "product_review_acquisition",
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "warrant_id",
            sa.Uuid(),
            sa.ForeignKey("warrants.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("outcome", sa.String(100), nullable=False),
        sa.Column("problems", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.create_table(
        "review_calendar_sources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("venue_mic", sa.String(4), nullable=False),
        sa.Column("source_version", sa.String(100), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.UniqueConstraint("workspace_id", "source_version", name="uq_review_calendar_version"),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
        CREATE FUNCTION guard_review_readiness_history() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'review readiness originals are append-only'
              USING ERRCODE = '23514';
        END; $$ LANGUAGE plpgsql;
        """)
        op.execute("""
        CREATE TRIGGER immutable_product_review_documents BEFORE UPDATE OR DELETE
          ON product_review_documents FOR EACH ROW
          EXECUTE FUNCTION guard_review_readiness_history();
        """)
        op.execute("""
        CREATE TRIGGER immutable_review_calendar_sources BEFORE UPDATE OR DELETE
          ON review_calendar_sources FOR EACH ROW
          EXECUTE FUNCTION guard_review_readiness_history();
        """)
        op.execute("""
        CREATE TRIGGER no_truncate_product_review_documents BEFORE TRUNCATE
          ON product_review_documents FOR EACH STATEMENT
          EXECUTE FUNCTION guard_review_readiness_history();
        """)
        op.execute("""
        CREATE TRIGGER no_truncate_review_calendar_sources BEFORE TRUNCATE
          ON review_calendar_sources FOR EACH STATEMENT
          EXECUTE FUNCTION guard_review_readiness_history();
        """)
        op.execute("""
        CREATE FUNCTION guard_product_review_document_scope() RETURNS trigger AS $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM warrants w JOIN warrant_terms_versions t
              ON t.warrant_id = w.id WHERE w.id = NEW.warrant_id
              AND w.workspace_id = NEW.workspace_id AND t.id = NEW.terms_id)
            OR NEW.retrieved_at > NEW.recorded_at THEN
                RAISE EXCEPTION 'product review document scope or clock mismatch'
                  USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END; $$ LANGUAGE plpgsql;
        """)
        op.execute("""
        CREATE TRIGGER product_review_document_scope BEFORE INSERT
          ON product_review_documents FOR EACH ROW
          EXECUTE FUNCTION guard_product_review_document_scope();
        """)


def downgrade() -> None:
    connection = op.get_bind()
    for table in ("product_review_documents", "review_calendar_sources"):
        if connection.scalar(sa.text(f"SELECT count(*) FROM {table}")):
            raise RuntimeError("Refusing to remove recorded original review evidence")
    if connection.dialect.name == "postgresql":
        op.execute("DROP FUNCTION guard_product_review_document_scope() CASCADE")
        op.execute("DROP FUNCTION guard_review_readiness_history() CASCADE")
    op.drop_table("review_calendar_sources")
    op.drop_table("product_review_acquisition")
    op.drop_index("ix_product_review_document_history", table_name="product_review_documents")
    op.drop_table("product_review_documents")
