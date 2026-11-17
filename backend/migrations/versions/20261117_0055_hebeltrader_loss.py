"""B04/B57 assessment ledger and durable loss episodes; no activation or backfill.

Revision ID: 20261117_0055
Revises: 20261117_0054
"""

import sqlalchemy as sa
from alembic import op

revision = "20261117_0055"
down_revision = "20261117_0054"
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
            "trade_id", sa.Uuid(), sa.ForeignKey("trades.id", ondelete="RESTRICT"), nullable=False
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
    op.drop_constraint(op.f("ck_alerts_alert_type_valid"), "alerts", type_="check")
    op.create_check_constraint(
        op.f("ck_alerts_alert_type_valid"),
        "alerts",
        "alert_type IN ('STOP_REACHED', 'TARGET_REACHED', 'RISK_TREND_CHANGED', "
        "'RISK_VOLATILITY_HIGH', 'HEBELTRADER_B04_LOSS')",
    )
    op.create_table(
        "hebeltrader_loss_assessments",
        *_scope_columns(),
        sa.Column(
            "previous_assessment_id",
            sa.Uuid(),
            sa.ForeignKey("hebeltrader_loss_assessments.id", ondelete="RESTRICT"),
        ),
        sa.Column("input_fingerprint", sa.String(64), nullable=False),
        sa.Column("owner_basis_id", sa.String(64), nullable=False),
        sa.Column("outcome", sa.String(32), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bid_at", sa.DateTime(timezone=True)),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.UniqueConstraint("previous_assessment_id", name="uq_hebeltrader_loss_successor"),
        sa.CheckConstraint(
            "outcome IN ('LOSS','RECOVERED','NOT_ASSESSABLE','NOT_REACHED','CLOSED')",
            name="hebeltrader_loss_outcome",
        ),
    )
    op.create_index(
        "uq_hebeltrader_loss_root",
        "hebeltrader_loss_assessments",
        ["workspace_id", "position_id", "rule_version"],
        unique=True,
        postgresql_where=sa.text("previous_assessment_id IS NULL"),
        sqlite_where=sa.text("previous_assessment_id IS NULL"),
    )
    op.create_index(
        "ix_hebeltrader_loss_history",
        "hebeltrader_loss_assessments",
        ["workspace_id", "position_id", "recorded_at"],
    )
    op.create_table(
        "hebeltrader_loss_episodes",
        *_scope_columns(),
        sa.Column("episode_number", sa.Integer(), nullable=False),
        sa.Column(
            "opening_assessment_id",
            sa.Uuid(),
            sa.ForeignKey("hebeltrader_loss_assessments.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "closing_assessment_id",
            sa.Uuid(),
            sa.ForeignKey("hebeltrader_loss_assessments.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "alert_id", sa.Uuid(), sa.ForeignKey("alerts.id", ondelete="RESTRICT"), nullable=False
        ),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("close_reason", sa.String(100)),
        sa.UniqueConstraint("opening_assessment_id", name="uq_hebeltrader_loss_episode_opening"),
        sa.UniqueConstraint("alert_id", name="uq_hebeltrader_loss_episode_alert"),
        sa.UniqueConstraint(
            "workspace_id",
            "position_id",
            "rule_version",
            "episode_number",
            name="uq_hebeltrader_loss_episode_number",
        ),
        sa.CheckConstraint("episode_number > 0", name="hebeltrader_loss_episode_positive"),
    )
    op.create_index(
        "uq_hebeltrader_loss_active",
        "hebeltrader_loss_episodes",
        ["workspace_id", "position_id", "rule_version"],
        unique=True,
        postgresql_where=sa.text("closed_at IS NULL"),
        sqlite_where=sa.text("closed_at IS NULL"),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
        CREATE FUNCTION guard_hebeltrader_loss_assessment() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP <> 'INSERT' THEN
            RAISE EXCEPTION 'B04 assessments are append-only' USING ERRCODE='23514';
          END IF;
          IF NOT EXISTS (SELECT 1 FROM trades t JOIN positions p ON p.trade_id=t.id
                         WHERE t.id=NEW.trade_id AND t.workspace_id=NEW.workspace_id
                         AND p.id=NEW.position_id)
             OR (NEW.previous_assessment_id IS NOT NULL AND NOT EXISTS (
                 SELECT 1 FROM hebeltrader_loss_assessments a WHERE a.id=NEW.previous_assessment_id
                 AND a.workspace_id=NEW.workspace_id AND a.position_id=NEW.position_id
                 AND a.trade_id=NEW.trade_id AND a.rule_version=NEW.rule_version)) THEN
            RAISE EXCEPTION 'B04 assessment scope mismatch' USING ERRCODE='23514';
          END IF;
          RETURN NEW;
        END $$
        """)
        op.execute("""
        CREATE TRIGGER tw_hebeltrader_loss_assessment_guard
        BEFORE INSERT OR UPDATE OR DELETE ON hebeltrader_loss_assessments
        FOR EACH ROW EXECUTE FUNCTION guard_hebeltrader_loss_assessment()
        """)
        op.execute("""
        CREATE TRIGGER tw_hebeltrader_loss_assessment_no_truncate
        BEFORE TRUNCATE ON hebeltrader_loss_assessments
        FOR EACH STATEMENT EXECUTE FUNCTION guard_hebeltrader_loss_assessment()
        """)
        op.execute("""
        CREATE FUNCTION guard_hebeltrader_loss_episode() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF TG_OP IN ('DELETE','TRUNCATE') OR (TG_OP = 'UPDATE' AND (
              OLD.closed_at IS NOT NULL OR NEW.closed_at IS NULL OR
              (to_jsonb(NEW)-'closed_at'-'closing_assessment_id'-'close_reason') IS DISTINCT FROM
              (to_jsonb(OLD)-'closed_at'-'closing_assessment_id'-'close_reason'))) THEN
            RAISE EXCEPTION 'B04 episode history is immutable' USING ERRCODE='23514';
          END IF;
          IF NOT EXISTS (SELECT 1 FROM hebeltrader_loss_assessments a JOIN alerts l
              ON l.id=NEW.alert_id WHERE a.id=NEW.opening_assessment_id AND a.outcome='LOSS'
              AND a.workspace_id=NEW.workspace_id AND a.trade_id=NEW.trade_id
              AND a.position_id=NEW.position_id AND a.rule_version=NEW.rule_version
              AND l.trade_id=NEW.trade_id AND l.position_id=NEW.position_id
              AND l.alert_type='HEBELTRADER_B04_LOSS') THEN
            RAISE EXCEPTION 'B04 episode scope mismatch' USING ERRCODE='23514';
          END IF;
          IF NEW.closed_at IS NOT NULL AND (NEW.closed_at < NEW.opened_at OR NEW.close_reason IS NULL OR
              NOT EXISTS (SELECT 1 FROM hebeltrader_loss_assessments a
              WHERE a.id=NEW.closing_assessment_id AND a.outcome IN ('RECOVERED','CLOSED')
              AND a.workspace_id=NEW.workspace_id AND a.position_id=NEW.position_id
              AND a.trade_id=NEW.trade_id AND a.rule_version=NEW.rule_version)) THEN
            RAISE EXCEPTION 'B04 episode close requires qualified recovery or sale' USING ERRCODE='23514';
          END IF;
          RETURN NEW;
        END $$
        """)
        op.execute("""
        CREATE TRIGGER tw_hebeltrader_loss_episode_guard
        BEFORE INSERT OR UPDATE OR DELETE ON hebeltrader_loss_episodes
        FOR EACH ROW EXECUTE FUNCTION guard_hebeltrader_loss_episode()
        """)
        op.execute("""
        CREATE TRIGGER tw_hebeltrader_loss_episode_no_truncate
        BEFORE TRUNCATE ON hebeltrader_loss_episodes
        FOR EACH STATEMENT EXECUTE FUNCTION guard_hebeltrader_loss_episode()
        """)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM hebeltrader_loss_assessments) OR EXISTS ("
            "SELECT 1 FROM alerts WHERE alert_type NOT IN ('STOP_REACHED', 'TARGET_REACHED'))"
        )
    ).scalar():
        raise RuntimeError("B04 history or new alert types exist; destructive downgrade refused")
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER tw_hebeltrader_loss_episode_guard ON hebeltrader_loss_episodes")
        op.execute(
            "DROP TRIGGER tw_hebeltrader_loss_episode_no_truncate ON hebeltrader_loss_episodes"
        )
        op.execute("DROP FUNCTION guard_hebeltrader_loss_episode()")
        op.execute(
            "DROP TRIGGER tw_hebeltrader_loss_assessment_guard ON hebeltrader_loss_assessments"
        )
        op.execute(
            "DROP TRIGGER tw_hebeltrader_loss_assessment_no_truncate ON hebeltrader_loss_assessments"
        )
        op.execute("DROP FUNCTION guard_hebeltrader_loss_assessment()")
    op.drop_table("hebeltrader_loss_episodes")
    op.drop_table("hebeltrader_loss_assessments")
    op.drop_constraint(op.f("ck_alerts_alert_type_valid"), "alerts", type_="check")
    op.create_check_constraint(
        op.f("ck_alerts_alert_type_valid"),
        "alerts",
        "alert_type IN ('STOP_REACHED', 'TARGET_REACHED')",
    )
