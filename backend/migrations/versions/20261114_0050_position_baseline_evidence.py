"""Append-only baseline references to existing position, execution and source facts.

Revision ID: 20261114_0050
Revises: 20261109_0049
"""

import sqlalchemy as sa
from alembic import op

revision = "20261114_0050"
down_revision = "20261109_0049"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "position_baseline_evidence",
        sa.Column("id", sa.Uuid(), primary_key=True),
        *[
            sa.Column(name, sa.Uuid(), sa.ForeignKey(target, ondelete="RESTRICT"), nullable=False)
            for name, target in (
                ("workspace_id", "workspaces.id"),
                ("trade_id", "trades.id"),
                ("position_id", "positions.id"),
                ("product_id", "warrants.id"),
                ("underlying_id", "underlyings.id"),
            )
        ],
        sa.Column(
            "source_version_id",
            sa.Uuid(),
            sa.ForeignKey("external_observation_versions.id", ondelete="RESTRICT"),
        ),
        sa.Column("declaration", sa.JSON(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column(
            "supersedes_evidence_id",
            sa.Uuid(),
            sa.ForeignKey("position_baseline_evidence.id", ondelete="RESTRICT"),
        ),
        sa.UniqueConstraint("workspace_id", "request_id", name="uq_position_baseline_request"),
        sa.UniqueConstraint("supersedes_evidence_id", name="uq_position_baseline_successor"),
        sa.CheckConstraint("id <> supersedes_evidence_id", name="baseline_evidence_not_self"),
        sa.CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'", name="baseline_evidence_fingerprint"
        ),
    )
    op.create_index(
        "uq_position_baseline_root",
        "position_baseline_evidence",
        ["workspace_id", "position_id"],
        unique=True,
        postgresql_where=sa.text("supersedes_evidence_id IS NULL"),
    )
    op.create_index(
        "ix_position_baseline_history",
        "position_baseline_evidence",
        ["workspace_id", "position_id", "recorded_at"],
    )
    op.create_table(
        "position_baseline_execution_refs",
        sa.Column(
            "evidence_id",
            sa.Uuid(),
            sa.ForeignKey("position_baseline_evidence.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "execution_id",
            sa.Uuid(),
            sa.ForeignKey("execution_records.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("role", sa.String(16), primary_key=True),
        sa.CheckConstraint(
            "role IN ('ENTRY_BUY','UNDERLYING_BUY','Z1_SELL')", name="baseline_execution_role"
        ),
    )
    op.execute("""
    CREATE FUNCTION guard_position_baseline_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE previous position_baseline_evidence; data jsonb; item jsonb;
      execution uuid; ids uuid[]; group_ids jsonb; expected_side text; role text;
      cancelled timestamptz;
    BEGIN
      IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'position baseline evidence is immutable'
          USING ERRCODE='23514', CONSTRAINT='tw_baseline_evidence_immutable';
      END IF;
      SELECT cancelled_at INTO cancelled FROM trades
        WHERE id=NEW.trade_id AND workspace_id=NEW.workspace_id
          AND product_id=NEW.product_id FOR UPDATE;
      IF NOT FOUND THEN
        RAISE EXCEPTION 'baseline evidence trade/workspace/product scope mismatch'
          USING ERRCODE='23503', CONSTRAINT='tw_baseline_trade_scope';
      END IF;
      IF cancelled IS NOT NULL THEN
        RAISE EXCEPTION 'cancelled trade cannot receive baseline evidence'
          USING ERRCODE='23514', CONSTRAINT='tw_baseline_cancelled';
      END IF;
      PERFORM id FROM positions WHERE id=NEW.position_id AND trade_id=NEW.trade_id
        AND product_id=NEW.product_id;
      IF NOT FOUND THEN
        RAISE EXCEPTION 'baseline evidence position scope mismatch'
          USING ERRCODE='23503', CONSTRAINT='tw_baseline_position_scope';
      END IF;
      PERFORM w.id FROM warrants w JOIN underlyings u ON u.id=w.underlying_id
        WHERE w.id=NEW.product_id AND w.workspace_id=NEW.workspace_id
          AND w.underlying_id=NEW.underlying_id AND u.workspace_id=NEW.workspace_id;
      IF NOT FOUND THEN
        RAISE EXCEPTION 'baseline evidence underlying scope mismatch'
          USING ERRCODE='23503', CONSTRAINT='tw_baseline_underlying_scope';
      END IF;
      IF NEW.supersedes_evidence_id IS NOT NULL THEN
        SELECT * INTO previous FROM position_baseline_evidence
          WHERE id=NEW.supersedes_evidence_id;
        IF NOT FOUND OR previous.workspace_id <> NEW.workspace_id
           OR previous.trade_id <> NEW.trade_id OR previous.position_id <> NEW.position_id
           OR previous.product_id <> NEW.product_id OR previous.underlying_id <> NEW.underlying_id
        THEN
          RAISE EXCEPTION 'baseline evidence predecessor scope mismatch'
            USING ERRCODE='23503', CONSTRAINT='tw_baseline_predecessor_scope';
        END IF;
        IF NEW.recorded_at < previous.recorded_at THEN
          RAISE EXCEPTION 'baseline evidence predecessor chronology mismatch'
            USING ERRCODE='23514', CONSTRAINT='tw_baseline_chronology';
        END IF;
      END IF;
      data := NEW.declaration::jsonb;
      IF jsonb_typeof(data) IS DISTINCT FROM 'object'
         OR jsonb_typeof(data->'underlying_trades') IS DISTINCT FROM 'array'
         OR jsonb_typeof(data->'z1_sales') IS DISTINCT FROM 'array'
         OR NOT data ? 'entry_order' OR NOT data ? 'source_version_id'
         OR (data->'entry_order' <> 'null'::jsonb
             AND jsonb_typeof(data->'entry_order') IS DISTINCT FROM 'object') THEN
        RAISE EXCEPTION 'baseline evidence declaration shape invalid'
          USING ERRCODE='23514', CONSTRAINT='tw_baseline_declaration';
      END IF;
      IF NEW.source_version_id IS DISTINCT FROM (data->>'source_version_id')::uuid THEN
        RAISE EXCEPTION 'baseline evidence source reference mismatch'
          USING ERRCODE='23514', CONSTRAINT='tw_baseline_source_reference';
      END IF;
      IF NEW.source_version_id IS NOT NULL THEN
        PERFORM v.id FROM external_observation_versions v
          JOIN external_observations o ON o.id=v.external_observation_id
          JOIN external_observation_import_rows r ON r.id=v.import_row_id
          WHERE v.id=NEW.source_version_id AND o.workspace_id=NEW.workspace_id
            AND v.product_id=NEW.product_id AND v.underlying_id=NEW.underlying_id
            AND v.source_name='HEBELTRADER' AND v.source_type='NEWSLETTER_RECOMMENDATION'
            AND v.recording_method='FILE_IMPORT' AND v.imported_at IS NOT NULL
            AND v.recorded_at <= NEW.recorded_at AND r.workspace_id=NEW.workspace_id
            AND r.resolved_product_id=NEW.product_id AND r.resolved_underlying_id=NEW.underlying_id
            AND r.disposition='ACCEPTED' AND r.validation_status='VALID'
            AND r.accepted_external_observation_version_id=v.id;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'baseline evidence source version scope or confirmation mismatch'
            USING ERRCODE='23503', CONSTRAINT='tw_baseline_source_scope';
        END IF;
      END IF;
      FOREACH role IN ARRAY ARRAY['ENTRY_BUY','UNDERLYING_BUY','Z1_SELL'] LOOP
        group_ids := CASE role
          WHEN 'ENTRY_BUY' THEN COALESCE(data->'entry_order'->'execution_ids', '[]'::jsonb)
          WHEN 'UNDERLYING_BUY' THEN data->'underlying_trades' ELSE data->'z1_sales' END;
        IF jsonb_typeof(group_ids) IS DISTINCT FROM 'array'
           OR jsonb_array_length(group_ids) > 2000
           OR (role='ENTRY_BUY' AND data->'entry_order' <> 'null'::jsonb
               AND jsonb_array_length(group_ids)=0) THEN
          RAISE EXCEPTION 'baseline execution references invalid or unbounded'
            USING ERRCODE='23514', CONSTRAINT='tw_baseline_execution_refs';
        END IF;
        ids := '{}';
        expected_side := CASE WHEN role='Z1_SELL' THEN 'SELL' ELSE 'BUY' END;
        FOR item IN SELECT value FROM jsonb_array_elements(group_ids) LOOP
          execution := CASE WHEN role='ENTRY_BUY' THEN (item #>> '{}')::uuid
                            ELSE (item->>'execution_id')::uuid END;
          IF execution IS NULL OR execution = ANY(ids) THEN
            RAISE EXCEPTION 'baseline execution reference missing or duplicated'
              USING ERRCODE='23514', CONSTRAINT='tw_baseline_execution_refs';
          END IF;
          ids := array_append(ids, execution);
          PERFORM id FROM execution_records WHERE id=execution AND trade_id=NEW.trade_id
            AND product_id=NEW.product_id AND side=expected_side
            AND recorded_at <= NEW.recorded_at;
          IF NOT FOUND THEN
            RAISE EXCEPTION 'baseline execution trade/product/side/time scope mismatch'
              USING ERRCODE='23503', CONSTRAINT='tw_baseline_execution_scope';
          END IF;
          IF role='UNDERLYING_BUY' AND (
            item->'binding'->>'basis' IS DISTINCT FROM 'UNDERLYING'
            OR (item->'binding'->>'instrument_id')::uuid IS DISTINCT FROM NEW.underlying_id
            OR item->>'price_kind' IS DISTINCT FROM 'TRADE') THEN
            RAISE EXCEPTION 'baseline underlying observation identity or price axis mismatch'
              USING ERRCODE='23514', CONSTRAINT='tw_baseline_underlying_observation';
          END IF;
          IF role='Z1_SELL' AND data->'z1_sales_reviewed' IS DISTINCT FROM 'true'::jsonb THEN
            RAISE EXCEPTION 'baseline sale attribution requires explicit review'
              USING ERRCODE='23514', CONSTRAINT='tw_baseline_sale_review';
          END IF;
        END LOOP;
      END LOOP;
      RETURN NEW;
    END $$;
    """)
    op.execute("""
    CREATE TRIGGER trg_position_baseline_evidence BEFORE INSERT OR UPDATE OR DELETE
      ON position_baseline_evidence FOR EACH ROW
      EXECUTE FUNCTION guard_position_baseline_evidence();
    """)
    op.execute("""
    CREATE FUNCTION position_baseline_evidence_references() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      INSERT INTO position_baseline_execution_refs(evidence_id, execution_id, role)
        SELECT NEW.id, value::uuid, 'ENTRY_BUY'
        FROM jsonb_array_elements_text(NEW.declaration::jsonb->'entry_order'->'execution_ids');
      INSERT INTO position_baseline_execution_refs(evidence_id, execution_id, role)
        SELECT NEW.id, (item->>'execution_id')::uuid, 'UNDERLYING_BUY'
        FROM jsonb_array_elements(NEW.declaration::jsonb->'underlying_trades') AS item;
      INSERT INTO position_baseline_execution_refs(evidence_id, execution_id, role)
        SELECT NEW.id, (item->>'execution_id')::uuid, 'Z1_SELL'
        FROM jsonb_array_elements(NEW.declaration::jsonb->'z1_sales') AS item;
      RETURN NEW;
    END $$;
    """)
    op.execute("""
    CREATE TRIGGER trg_position_baseline_references AFTER INSERT ON position_baseline_evidence
      FOR EACH ROW EXECUTE FUNCTION position_baseline_evidence_references();
    """)
    op.execute("""
    CREATE FUNCTION guard_position_baseline_execution_reference()
      RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP <> 'INSERT' OR pg_trigger_depth() < 2 THEN
        RAISE EXCEPTION 'position baseline execution reference is immutable'
          USING ERRCODE='23514', CONSTRAINT='tw_baseline_reference_immutable';
      END IF;
      RETURN NEW;
    END $$;
    """)
    op.execute("""
    CREATE TRIGGER trg_position_baseline_reference_guard BEFORE INSERT OR UPDATE OR DELETE
      ON position_baseline_execution_refs FOR EACH ROW
      EXECUTE FUNCTION guard_position_baseline_execution_reference();
    """)


def downgrade() -> None:
    op.execute("""
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM position_baseline_evidence) THEN
        RAISE EXCEPTION 'Refusing downgrade: position baseline evidence would be lost';
      END IF;
    END $$;
    """)
    op.drop_table("position_baseline_execution_refs")
    op.drop_table("position_baseline_evidence")
    op.execute("DROP FUNCTION guard_position_baseline_execution_reference()")
    op.execute("DROP FUNCTION position_baseline_evidence_references()")
    op.execute("DROP FUNCTION guard_position_baseline_evidence()")
