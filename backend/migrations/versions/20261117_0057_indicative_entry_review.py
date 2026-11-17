"""Separate indicative review history; no activation, source qualification or backfill.

Revision ID: 20261117_0057
Revises: 20261117_0056
"""

import sqlalchemy as sa
from alembic import op

revision = "20261117_0057"
down_revision = "20261117_0056"
branch_labels = None
depends_on = None


def _scope_columns() -> list[sa.Column]:  # type: ignore[type-arg]
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "trade_id",
            sa.Uuid(),
            sa.ForeignKey("trades.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "position_id",
            sa.Uuid(),
            sa.ForeignKey("positions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("rule_version", sa.String(64), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "indicative_entry_assessments",
        *_scope_columns(),
        sa.Column(
            "previous_assessment_id",
            sa.Uuid(),
            sa.ForeignKey("indicative_entry_assessments.id", ondelete="RESTRICT"),
        ),
        sa.Column("input_fingerprint", sa.String(64), nullable=False),
        sa.Column("owner_basis_id", sa.String(64), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ordering_at", sa.DateTime(timezone=True)),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "previous_assessment_id", name="uq_indicative_entry_successor"
        ),
        sa.CheckConstraint(
            "outcome IN ('BELOW_ENTRY','AT_OR_ABOVE_ENTRY','NOT_REACHED','UNAVAILABLE','CLOSED')",
            name="indicative_entry_outcome",
        ),
    )
    op.create_index(
        "uq_indicative_entry_root",
        "indicative_entry_assessments",
        ["workspace_id", "position_id", "rule_version"],
        unique=True,
        postgresql_where=sa.text("previous_assessment_id IS NULL"),
        sqlite_where=sa.text("previous_assessment_id IS NULL"),
    )
    op.create_index(
        "ix_indicative_entry_history",
        "indicative_entry_assessments",
        ["workspace_id", "position_id", "recorded_at"],
    )
    op.create_table(
        "indicative_entry_episodes",
        *_scope_columns(),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("event_key", sa.String(64)),
        sa.Column("episode_number", sa.Integer(), nullable=False),
        sa.Column(
            "opening_assessment_id",
            sa.Uuid(),
            sa.ForeignKey("indicative_entry_assessments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "closing_assessment_id",
            sa.Uuid(),
            sa.ForeignKey("indicative_entry_assessments.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "alert_id",
            sa.Uuid(),
            sa.ForeignKey("alerts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("close_reason", sa.String(100)),
        sa.UniqueConstraint(
            "opening_assessment_id", "kind", name="uq_indicative_entry_episode_opening"
        ),
        sa.UniqueConstraint("alert_id", name="uq_indicative_entry_episode_alert"),
        sa.UniqueConstraint(
            "workspace_id",
            "position_id",
            "rule_version",
            "kind",
            "event_key",
            name="uq_indicative_review_event",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "position_id",
            "rule_version",
            "kind",
            "episode_number",
            name="uq_indicative_entry_episode_number",
        ),
        sa.CheckConstraint(
            "episode_number > 0", name="indicative_entry_episode_positive"
        ),
        sa.CheckConstraint(
            "kind IN ('ENTRY_LOSS','REVIEW_DUE','DATA_UNAVAILABLE')",
            name="indicative_entry_kind",
        ),
    )
    op.create_index(
        "uq_indicative_entry_active",
        "indicative_entry_episodes",
        ["workspace_id", "position_id", "rule_version", "kind"],
        unique=True,
        postgresql_where=sa.text("closed_at IS NULL"),
        sqlite_where=sa.text("closed_at IS NULL"),
    )
    if op.get_bind().dialect.name == "postgresql":
        _guards()


def _guards() -> None:
    op.execute("""
    CREATE FUNCTION guard_indicative_entry_assessment() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'Review assessments are append-only' USING ERRCODE='23514';
      END IF;
      IF NOT EXISTS (SELECT 1 FROM trades t JOIN positions p ON p.trade_id=t.id
                     WHERE t.id=NEW.trade_id AND t.workspace_id=NEW.workspace_id
                     AND p.id=NEW.position_id)
         OR (NEW.previous_assessment_id IS NOT NULL AND NOT EXISTS (
             SELECT 1 FROM indicative_entry_assessments a WHERE a.id=NEW.previous_assessment_id
             AND a.workspace_id=NEW.workspace_id AND a.position_id=NEW.position_id
             AND a.trade_id=NEW.trade_id AND a.rule_version=NEW.rule_version)) THEN
        RAISE EXCEPTION 'Review assessment scope mismatch' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$
    """)
    op.execute("""
    CREATE TRIGGER tw_indicative_entry_assessment_guard
    BEFORE INSERT OR UPDATE OR DELETE ON indicative_entry_assessments
    FOR EACH ROW EXECUTE FUNCTION guard_indicative_entry_assessment()
    """)
    op.execute("""
    CREATE TRIGGER tw_indicative_entry_assessment_no_truncate
    BEFORE TRUNCATE ON indicative_entry_assessments
    FOR EACH STATEMENT EXECUTE FUNCTION guard_indicative_entry_assessment()
    """)
    op.execute("""
    CREATE FUNCTION guard_indicative_entry_episode() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP IN ('DELETE','TRUNCATE') OR (TG_OP = 'UPDATE' AND (
          OLD.closed_at IS NOT NULL OR NEW.closed_at IS NULL OR
          (to_jsonb(NEW)-'closed_at'-'closing_assessment_id'-'close_reason') IS DISTINCT FROM
          (to_jsonb(OLD)-'closed_at'-'closing_assessment_id'-'close_reason'))) THEN
        RAISE EXCEPTION 'Review episode history is immutable' USING ERRCODE='23514';
      END IF;
      IF NOT EXISTS (SELECT 1 FROM indicative_entry_assessments a JOIN alerts l
          ON l.id=NEW.alert_id WHERE a.id=NEW.opening_assessment_id
          AND a.workspace_id=NEW.workspace_id AND a.trade_id=NEW.trade_id
          AND a.position_id=NEW.position_id AND a.rule_version=NEW.rule_version
          AND l.trade_id=NEW.trade_id AND l.position_id=NEW.position_id
          AND ((NEW.kind='ENTRY_LOSS' AND a.outcome='BELOW_ENTRY'
                AND l.alert_type='INDICATIVE_ENTRY_LOSS')
            OR (NEW.kind='REVIEW_DUE' AND a.result->>'review_due'='true'
                AND NEW.event_key=a.result->>'review_event_key'
                AND l.alert_type='POSITION_REVIEW_DUE')
            OR (NEW.kind='DATA_UNAVAILABLE' AND a.outcome='UNAVAILABLE'
                AND l.alert_type='POSITION_DATA_UNAVAILABLE'))) THEN
        RAISE EXCEPTION 'Review episode scope mismatch' USING ERRCODE='23514';
      END IF;
      IF NEW.closed_at IS NOT NULL AND (NEW.closed_at < NEW.opened_at OR NEW.close_reason IS NULL OR
          NOT EXISTS (SELECT 1 FROM indicative_entry_assessments a
          WHERE a.id=NEW.closing_assessment_id
          AND a.workspace_id=NEW.workspace_id AND a.position_id=NEW.position_id
          AND a.trade_id=NEW.trade_id AND a.rule_version=NEW.rule_version
          AND (a.outcome='CLOSED'
               OR (NEW.kind='ENTRY_LOSS' AND a.outcome='AT_OR_ABOVE_ENTRY')
               OR (NEW.kind='REVIEW_DUE' AND (a.result->>'review_due'='false'
                   OR (a.result->>'review_due'='true'
                       AND NEW.event_key IS DISTINCT FROM a.result->>'review_event_key')))
               OR (NEW.kind='DATA_UNAVAILABLE' AND a.outcome<>'UNAVAILABLE')))) THEN
        RAISE EXCEPTION 'Review episode close requires recorded resolution' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$
    """)
    op.execute("""
    CREATE TRIGGER tw_indicative_entry_episode_guard
    BEFORE INSERT OR UPDATE OR DELETE ON indicative_entry_episodes
    FOR EACH ROW EXECUTE FUNCTION guard_indicative_entry_episode()
    """)
    op.execute("""
    CREATE TRIGGER tw_indicative_entry_episode_no_truncate
    BEFORE TRUNCATE ON indicative_entry_episodes
    FOR EACH STATEMENT EXECUTE FUNCTION guard_indicative_entry_episode()
    """)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM indicative_entry_assessments)")
    ).scalar():
        raise RuntimeError(
            "Immutable indicative review history exists; destructive downgrade refused"
        )
    if bind.dialect.name == "postgresql":
        for suffix in ("assessment", "episode"):
            table = (
                "indicative_entry_assessments"
                if suffix == "assessment"
                else "indicative_entry_episodes"
            )
            op.execute(f"DROP TRIGGER tw_indicative_entry_{suffix}_guard ON {table}")
            op.execute(
                f"DROP TRIGGER tw_indicative_entry_{suffix}_no_truncate ON {table}"
            )
            op.execute(f"DROP FUNCTION guard_indicative_entry_{suffix}()")
    op.drop_table("indicative_entry_episodes")
    op.drop_table("indicative_entry_assessments")
