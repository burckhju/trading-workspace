"""FT-012 journal source pin, optimistic draft revision and immutable finals.

Revision ID: 20261014_0046
Revises: 20261012_0045
"""

import sqlalchemy as sa
from alembic import op

revision = "20261014_0046"
down_revision = "20261012_0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "trade_journal_versions",
        sa.Column("edit_revision", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "trade_journal_versions",
        sa.Column("source_exit_review_version_id", sa.Uuid(), nullable=True),
    )
    op.create_check_constraint(
        "ck_journal_edit_revision_positive", "trade_journal_versions", "edit_revision >= 1"
    )
    op.create_foreign_key(
        "fk_journal_review_source",
        "trade_journal_versions",
        "exit_review_versions",
        ["source_exit_review_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.execute("""
    CREATE FUNCTION guard_trade_journal_identity() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'UPDATE' AND NEW IS DISTINCT FROM OLD THEN
        RAISE EXCEPTION 'journal identity is immutable' USING ERRCODE = '23514';
      END IF;
      IF NOT EXISTS (SELECT 1 FROM trades t WHERE t.id=NEW.trade_id
          AND t.workspace_id=NEW.workspace_id) THEN
        RAISE EXCEPTION 'journal trade workspace mismatch' USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END $$;
    """)
    op.execute("""
    CREATE TRIGGER trg_trade_journal_identity BEFORE INSERT OR UPDATE ON trade_journals
      FOR EACH ROW EXECUTE FUNCTION guard_trade_journal_identity();
    """)
    op.execute("""
    CREATE FUNCTION guard_trade_journal_version() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP <> 'INSERT' THEN
        IF OLD.status = 'FINALIZED' THEN
          RAISE EXCEPTION 'finalized journal history is immutable' USING ERRCODE = '23514';
        END IF;
        IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
        IF (NEW.id, NEW.trade_journal_id, NEW.version, NEW.created_at, NEW.created_by,
            NEW.supersedes_version_id) IS DISTINCT FROM
           (OLD.id, OLD.trade_journal_id, OLD.version, OLD.created_at, OLD.created_by,
            OLD.supersedes_version_id) OR NEW.edit_revision <> OLD.edit_revision + 1 THEN
          RAISE EXCEPTION 'journal identity/revision conflict' USING ERRCODE = '23514';
        END IF;
      END IF;
      IF NEW.supersedes_version_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM trade_journal_versions p WHERE p.id = NEW.supersedes_version_id
        AND p.trade_journal_id = NEW.trade_journal_id AND p.status = 'FINALIZED'
        AND p.version + 1 = NEW.version
      ) THEN
        RAISE EXCEPTION 'journal predecessor mismatch' USING ERRCODE = '23514';
      END IF;
      IF NEW.source_exit_review_version_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM trade_journals j
        JOIN post_trade_observations o ON o.trade_id = j.trade_id AND o.workspace_id = j.workspace_id
        JOIN exit_reviews r ON r.post_trade_observation_id = o.id AND r.workspace_id = j.workspace_id
        JOIN exit_review_versions v ON v.exit_review_id = r.id
        WHERE j.id = NEW.trade_journal_id AND v.id = NEW.source_exit_review_version_id AND v.status = 'FINALIZED'
      ) THEN
        RAISE EXCEPTION 'journal review source mismatch' USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END $$;
    """)
    op.execute("""
    CREATE TRIGGER trg_trade_journal_immutable
      BEFORE INSERT OR UPDATE OR DELETE ON trade_journal_versions
      FOR EACH ROW EXECUTE FUNCTION guard_trade_journal_version();
    """)
    op.execute("""
    CREATE FUNCTION guard_journal_evidence() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'journal evidence source is immutable' USING ERRCODE = '23514';
      END IF;
      IF NOT EXISTS (
        SELECT 1 FROM trade_journal_versions v JOIN trade_journals j ON j.id=v.trade_journal_id
        JOIN learning_evidence e ON e.workspace_id=j.workspace_id
        WHERE v.id=NEW.trade_journal_version_id AND v.status='FINALIZED'
          AND e.id=NEW.learning_evidence_id AND e.evidence_type='TRADE_JOURNAL_VERSION'
      ) THEN
        RAISE EXCEPTION 'journal evidence requires same-workspace finalized source'
          USING ERRCODE = '23514';
      END IF;
      RETURN NEW;
    END $$;
    """)
    op.execute("""
    CREATE TRIGGER trg_journal_evidence_immutable
      BEFORE INSERT OR UPDATE OR DELETE ON trade_journal_version_evidence
      FOR EACH ROW EXECUTE FUNCTION guard_journal_evidence();
    """)


def downgrade() -> None:
    # Do not destroy provenance/revisions written using this feature.
    op.execute("""
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM trade_journal_versions
        WHERE source_exit_review_version_id IS NOT NULL OR edit_revision <> 1) THEN
        RAISE EXCEPTION 'journal provenance exists: restore a verified backup instead of downgrade';
      END IF;
    END $$;
    """)
    op.execute("DROP TRIGGER trg_trade_journal_identity ON trade_journals")
    op.execute("DROP FUNCTION guard_trade_journal_identity()")
    op.execute("DROP TRIGGER trg_journal_evidence_immutable ON trade_journal_version_evidence")
    op.execute("DROP FUNCTION guard_journal_evidence()")
    op.execute("DROP TRIGGER trg_trade_journal_immutable ON trade_journal_versions")
    op.execute("DROP FUNCTION guard_trade_journal_version()")
    op.drop_constraint("fk_journal_review_source", "trade_journal_versions", type_="foreignkey")
    op.drop_constraint("ck_journal_edit_revision_positive", "trade_journal_versions", type_="check")
    op.drop_column("trade_journal_versions", "source_exit_review_version_id")
    op.drop_column("trade_journal_versions", "edit_revision")
