"""Immutable saved-evidence target assessments; no baseline runtime activation.

Revision ID: 20261114_0051
Revises: 20261114_0050
"""

import sqlalchemy as sa
from alembic import op

revision = "20261114_0051"
down_revision = "20261114_0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hebeltrader_target_assessments",
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
        *[
            sa.Column(name, sa.Uuid(), sa.ForeignKey(target, ondelete="RESTRICT"))
            for name, target in (
                ("source_version_id", "external_observation_versions.id"),
                ("evidence_revision_id", "position_baseline_evidence.id"),
                ("previous_assessment_id", "hebeltrader_target_assessments.id"),
            )
        ],
        sa.Column("definition_version", sa.String(64), nullable=False),
        sa.Column("baseline_id", sa.String(64), nullable=False),
        sa.Column("baseline_version", sa.String(32), nullable=False),
        sa.Column("basis_id", sa.String(64), nullable=False),
        sa.Column("input_fingerprint", sa.String(64), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), nullable=False),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.UniqueConstraint("previous_assessment_id", name="uq_hebeltrader_target_successor"),
        sa.CheckConstraint("id <> previous_assessment_id", name="hebeltrader_target_not_self"),
        sa.CheckConstraint("basis_id ~ '^[0-9a-f]{64}$'", name="hebeltrader_target_basis"),
        sa.CheckConstraint(
            "input_fingerprint ~ '^[0-9a-f]{64}$'", name="hebeltrader_target_fingerprint"
        ),
    )
    op.create_index(
        "uq_hebeltrader_target_root",
        "hebeltrader_target_assessments",
        ["workspace_id", "position_id"],
        unique=True,
        postgresql_where=sa.text("previous_assessment_id IS NULL"),
    )
    op.create_index(
        "ix_hebeltrader_target_history",
        "hebeltrader_target_assessments",
        ["workspace_id", "position_id", "recorded_at"],
    )
    op.create_table(
        "hebeltrader_target_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        *[
            sa.Column(name, sa.Uuid(), sa.ForeignKey(target, ondelete="RESTRICT"), nullable=False)
            for name, target in (
                ("workspace_id", "workspaces.id"),
                ("trade_id", "trades.id"),
                ("position_id", "positions.id"),
                ("assessment_id", "hebeltrader_target_assessments.id"),
            )
        ],
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), nullable=False),
        sa.UniqueConstraint("workspace_id", "request_id", name="uq_hebeltrader_target_request"),
        sa.CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'", name="hebeltrader_target_request_fingerprint"
        ),
    )
    op.execute("""
    CREATE FUNCTION guard_hebeltrader_target_rows() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE previous hebeltrader_target_assessments; evidence position_baseline_evidence;
      cancelled timestamptz; open_quantity integer; target jsonb;
    BEGIN
      IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'hebeltrader target evidence is immutable'
          USING ERRCODE='23514', CONSTRAINT='tw_hebeltrader_targets_immutable';
      END IF;
      IF TG_TABLE_NAME = 'hebeltrader_target_requests' THEN
        SELECT * INTO previous FROM hebeltrader_target_assessments
          WHERE id=NEW.assessment_id;
        IF NOT FOUND OR previous.workspace_id <> NEW.workspace_id
           OR previous.trade_id <> NEW.trade_id OR previous.position_id <> NEW.position_id
           OR previous.recorded_at > NEW.recorded_at THEN
          RAISE EXCEPTION 'target request assessment scope or chronology mismatch'
            USING ERRCODE='23503', CONSTRAINT='tw_hebeltrader_target_request_scope';
        END IF;
        RETURN NEW;
      END IF;
      SELECT cancelled_at INTO cancelled FROM trades
        WHERE id=NEW.trade_id AND workspace_id=NEW.workspace_id
          AND product_id=NEW.product_id FOR UPDATE;
      IF NOT FOUND THEN
        RAISE EXCEPTION 'target assessment trade/workspace/product scope mismatch'
          USING ERRCODE='23503', CONSTRAINT='tw_hebeltrader_target_trade_scope';
      END IF;
      SELECT p.open_quantity INTO open_quantity FROM positions p
        WHERE p.id=NEW.position_id AND p.trade_id=NEW.trade_id AND p.product_id=NEW.product_id;
      IF NOT FOUND THEN
        RAISE EXCEPTION 'target assessment position scope mismatch'
          USING ERRCODE='23503', CONSTRAINT='tw_hebeltrader_target_position_scope';
      END IF;
      IF cancelled IS NOT NULL OR open_quantity <= 0 THEN
        RAISE EXCEPTION 'closed or cancelled position cannot receive a new target assessment'
          USING ERRCODE='23514', CONSTRAINT='tw_hebeltrader_target_closed';
      END IF;
      PERFORM w.id FROM warrants w JOIN underlyings u ON u.id=w.underlying_id
        WHERE w.id=NEW.product_id AND w.workspace_id=NEW.workspace_id
          AND w.underlying_id=NEW.underlying_id AND u.workspace_id=NEW.workspace_id;
      IF NOT FOUND THEN
        RAISE EXCEPTION 'target assessment underlying scope mismatch'
          USING ERRCODE='23503', CONSTRAINT='tw_hebeltrader_target_underlying_scope';
      END IF;
      IF NEW.definition_version <> 'hebeltrader-targets-v1'
         OR NEW.baseline_id <> 'HEBELTRADER_CONFIRMED_BASELINE'
         OR NEW.baseline_version <> '1.0.0' THEN
        RAISE EXCEPTION 'unsupported target assessment definition'
          USING ERRCODE='23514', CONSTRAINT='tw_hebeltrader_target_definition';
      END IF;
      IF NEW.previous_assessment_id IS NOT NULL THEN
        SELECT * INTO previous FROM hebeltrader_target_assessments
          WHERE id=NEW.previous_assessment_id;
        IF NOT FOUND OR previous.workspace_id <> NEW.workspace_id
           OR previous.trade_id <> NEW.trade_id OR previous.position_id <> NEW.position_id
           OR previous.product_id <> NEW.product_id OR previous.underlying_id <> NEW.underlying_id
        THEN
          RAISE EXCEPTION 'target assessment predecessor scope mismatch'
            USING ERRCODE='23503', CONSTRAINT='tw_hebeltrader_target_predecessor_scope';
        END IF;
        IF NEW.recorded_at < previous.recorded_at THEN
          RAISE EXCEPTION 'target assessment predecessor chronology mismatch'
            USING ERRCODE='23514', CONSTRAINT='tw_hebeltrader_target_chronology';
        END IF;
      END IF;
      IF NEW.evidence_revision_id IS NOT NULL THEN
        SELECT * INTO evidence FROM position_baseline_evidence WHERE id=NEW.evidence_revision_id;
        IF NOT FOUND OR evidence.workspace_id <> NEW.workspace_id
           OR evidence.trade_id <> NEW.trade_id OR evidence.position_id <> NEW.position_id
           OR evidence.product_id <> NEW.product_id OR evidence.underlying_id <> NEW.underlying_id
           OR evidence.recorded_at > NEW.recorded_at THEN
          RAISE EXCEPTION 'target assessment execution evidence scope mismatch'
            USING ERRCODE='23503', CONSTRAINT='tw_hebeltrader_target_evidence_scope';
        END IF;
        IF NEW.source_version_id IS NOT NULL
           AND evidence.source_version_id IS DISTINCT FROM NEW.source_version_id THEN
          RAISE EXCEPTION 'target assessment source differs from execution evidence pin'
            USING ERRCODE='23503', CONSTRAINT='tw_hebeltrader_target_evidence_source';
        END IF;
      END IF;
      IF NEW.source_version_id IS NOT NULL THEN
        PERFORM v.id FROM external_observation_versions v
          JOIN external_observations o ON o.id=v.external_observation_id
          JOIN external_observation_import_rows r ON r.id=v.import_row_id
          WHERE v.id=NEW.source_version_id AND o.workspace_id=NEW.workspace_id
            AND v.product_id=NEW.product_id AND v.underlying_id=NEW.underlying_id
            AND v.source_name='HEBELTRADER' AND v.source_type='NEWSLETTER_RECOMMENDATION'
            AND v.recording_method='FILE_IMPORT' AND v.imported_at IS NOT NULL
            AND v.recorded_at <= NEW.recorded_at AND v.imported_at <= NEW.recorded_at
            AND r.workspace_id=NEW.workspace_id AND r.disposition='ACCEPTED'
            AND r.resolved_product_id=NEW.product_id AND r.resolved_underlying_id=NEW.underlying_id
            AND r.validation_status='VALID' AND r.accepted_external_observation_version_id=v.id;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'target assessment source scope or confirmation mismatch'
            USING ERRCODE='23503', CONSTRAINT='tw_hebeltrader_target_source_scope';
        END IF;
      END IF;
      IF jsonb_typeof(NEW.inputs::jsonb) IS DISTINCT FROM 'object'
         OR jsonb_typeof(NEW.result::jsonb) IS DISTINCT FROM 'object'
         OR jsonb_typeof(NEW.result::jsonb->'targets') IS DISTINCT FROM 'array'
         OR jsonb_array_length(NEW.result::jsonb->'targets') <> 2 THEN
        RAISE EXCEPTION 'target assessment snapshot shape invalid'
          USING ERRCODE='23514', CONSTRAINT='tw_hebeltrader_target_snapshot';
      END IF;
      IF (SELECT count(DISTINCT value->>'target')
          FROM jsonb_array_elements(NEW.result::jsonb->'targets')) <> 2 THEN
        RAISE EXCEPTION 'target assessment target identity invalid'
          USING ERRCODE='23514', CONSTRAINT='tw_hebeltrader_target_snapshot';
      END IF;
      FOR target IN SELECT value FROM jsonb_array_elements(NEW.result::jsonb->'targets') LOOP
        IF target->>'target' NOT IN ('Z1','Z2') OR target->>'target' IS NULL
           OR target->>'status' NOT IN ('PROVEN','NOT_PROVEN','NOT_ASSESSABLE','REVIEW_REQUIRED')
           OR target->>'status' IS NULL THEN
          RAISE EXCEPTION 'target assessment status invalid'
            USING ERRCODE='23514', CONSTRAINT='tw_hebeltrader_target_snapshot';
        END IF;
      END LOOP;
      RETURN NEW;
    END $$;
    CREATE TRIGGER guard_hebeltrader_target_assessments
      BEFORE INSERT OR UPDATE OR DELETE ON hebeltrader_target_assessments
      FOR EACH ROW EXECUTE FUNCTION guard_hebeltrader_target_rows();
    CREATE TRIGGER guard_hebeltrader_target_requests
      BEFORE INSERT OR UPDATE OR DELETE ON hebeltrader_target_requests
      FOR EACH ROW EXECUTE FUNCTION guard_hebeltrader_target_rows();
    """)


def downgrade() -> None:
    op.execute("""
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM hebeltrader_target_assessments)
         OR EXISTS (SELECT 1 FROM hebeltrader_target_requests) THEN
        RAISE EXCEPTION 'Refusing downgrade: hebeltrader target evidence would be lost';
      END IF;
    END $$;
    DROP TRIGGER guard_hebeltrader_target_requests ON hebeltrader_target_requests;
    DROP TRIGGER guard_hebeltrader_target_assessments ON hebeltrader_target_assessments;
    DROP FUNCTION guard_hebeltrader_target_rows();
    """)
    op.drop_table("hebeltrader_target_requests")
    op.drop_table("hebeltrader_target_assessments")
