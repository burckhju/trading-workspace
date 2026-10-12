"""Append-only quote samples and document-backed product valuation facts.

Revision ID: 20261012_0045
Revises: 20261004_0044
"""

import sqlalchemy as sa
from alembic import op

revision = "20261012_0045"
down_revision = "20261004_0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("SET LOCAL lock_timeout = '5s'")
    op.create_table(
        "warrant_quote_samples",
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
        sa.Column("slot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("day_utc", sa.Date(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("reason", sa.String(140), nullable=True),
        sa.Column("quote_fingerprint", sa.String(64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "workspace_id",
            "warrant_listing_id",
            "provider",
            "identity_key",
            "slot_at",
            name="uq_warrant_quote_sample_slot",
        ),
    )
    op.create_index(
        "ix_warrant_quote_sample_product_time",
        "warrant_quote_samples",
        ["workspace_id", "warrant_id", "captured_at"],
    )
    op.create_table(
        "warrant_valuation_evidence",
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
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("identity_key", sa.String(64), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "warrant_id", "revision", name="uq_warrant_valuation_evidence_revision"
        ),
        sa.CheckConstraint("revision > 0", name="revision_positive"),
    )
    op.create_index(
        "ix_warrant_valuation_evidence_product_time",
        "warrant_valuation_evidence",
        ["workspace_id", "warrant_id", "recorded_at"],
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
            CREATE FUNCTION guard_iv_data_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF TG_OP <> 'INSERT' THEN
                    RAISE EXCEPTION 'IV data evidence is append-only' USING ERRCODE = '23514';
                END IF;
                IF NOT EXISTS (SELECT 1 FROM warrants w WHERE w.id = NEW.warrant_id
                               AND w.workspace_id = NEW.workspace_id) THEN
                    RAISE EXCEPTION 'IV evidence workspace mismatch' USING ERRCODE = '23514';
                END IF;
                IF TG_TABLE_NAME = 'warrant_quote_samples' THEN
                    IF NOT EXISTS (SELECT 1 FROM warrant_listings l WHERE
                        l.id = NEW.warrant_listing_id AND l.warrant_id = NEW.warrant_id
                        AND l.workspace_id = NEW.workspace_id) THEN
                        RAISE EXCEPTION 'Quote sample listing mismatch' USING ERRCODE = '23514';
                    END IF;
                ELSE
                    IF NOT EXISTS (SELECT 1 FROM warrant_terms_versions t WHERE
                        t.id = NEW.terms_id AND t.warrant_id = NEW.warrant_id) THEN
                        RAISE EXCEPTION 'Valuation evidence terms mismatch' USING ERRCODE = '23514';
                    END IF;
                END IF;
                RETURN NEW;
            END $$
        """)
        for table in ("warrant_quote_samples", "warrant_valuation_evidence"):
            op.execute(
                f"CREATE TRIGGER trg_{table}_guard BEFORE INSERT OR UPDATE OR DELETE "
                f"ON {table} FOR EACH ROW EXECUTE FUNCTION guard_iv_data_evidence()"
            )


def downgrade() -> None:
    tables = ("warrant_quote_samples", "warrant_valuation_evidence")
    for table in tables:
        if op.get_bind().scalar(sa.text(f"SELECT 1 FROM {table} LIMIT 1")):
            raise RuntimeError("Cannot downgrade: immutable IV data evidence exists")
    for table in tables:
        op.drop_table(table)
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION guard_iv_data_evidence()")
