"""Explicit, mapping-revision-bound index series semantics for charts.

Revision ID: 20261004_0043
Revises: 20260928_0042
"""

import sqlalchemy as sa
from alembic import op

revision = "20261004_0043"
down_revision = "20260928_0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reference_series_definitions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "market_reference_id",
            sa.Uuid(),
            sa.ForeignKey("market_references.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "mapping_id",
            sa.Uuid(),
            sa.ForeignKey("provider_instrument_mappings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("mapping_version", sa.Integer(), nullable=False),
        sa.Column("return_basis", sa.String(30), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=False),
        sa.Column("confirmed_by", sa.String(200), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("mapping_version >= 1", name="ck_reference_series_definition_version"),
        sa.CheckConstraint(
            "return_basis IN ('PRICE_INDEX', 'TOTAL_RETURN_INDEX')",
            name="ck_reference_series_definition_basis",
        ),
    )
    op.create_index(
        "ix_reference_series_definitions_market_reference_id",
        "reference_series_definitions",
        ["market_reference_id"],
    )

    op.execute("""
        CREATE FUNCTION guard_reference_series_definition() RETURNS trigger AS $$
        BEGIN
            IF TG_OP <> 'INSERT' THEN
                RAISE EXCEPTION 'reference series evidence is append-only'
                    USING ERRCODE = '23514';
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM provider_instrument_mappings m
                JOIN market_data_instruments i ON i.id = m.market_data_instrument_id
                JOIN market_references r ON r.id = i.market_reference_id
                WHERE m.id = NEW.mapping_id AND m.workspace_id = NEW.workspace_id
                  AND i.workspace_id = NEW.workspace_id AND r.workspace_id = NEW.workspace_id
                  AND r.id = NEW.market_reference_id AND m.version = NEW.mapping_version
            ) THEN
                RAISE EXCEPTION 'series evidence mapping owner/revision mismatch'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trg_reference_series_definition_guard
        BEFORE INSERT OR UPDATE OR DELETE ON reference_series_definitions
        FOR EACH ROW EXECUTE FUNCTION guard_reference_series_definition();
    """)


def downgrade() -> None:
    # Preserve operator provenance; a populated history needs an explicit migration plan.
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT EXISTS (SELECT 1 FROM reference_series_definitions)")):
        raise RuntimeError("Cannot downgrade populated reference series definitions")
    if connection.scalar(sa.text("SELECT EXISTS (SELECT 1 FROM underlyings WHERE type = 'ETF')")):
        raise RuntimeError("Cannot downgrade while ETF master data needs this application version")
    op.drop_table("reference_series_definitions")
    op.execute("DROP FUNCTION guard_reference_series_definition()")
