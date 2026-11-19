"""One indicative review family across explicit policy versions; no activation.

Revision ID: 20261118_0059
Revises: 20261118_0058
"""

import sqlalchemy as sa
from alembic import op

revision = "20261118_0059"
down_revision = "20261118_0058"
branch_labels = None
depends_on = None

FAMILY = "('indicative-entry-review-v1','indicative-entry-review-v2')"
FAMILY_FILTER = f"rule_version IN {FAMILY}"


def upgrade() -> None:
    definitions = (
        (
            "uq_indicative_family_root",
            "indicative_entry_assessments",
            ["workspace_id", "position_id"],
            f"previous_assessment_id IS NULL AND {FAMILY_FILTER}",
        ),
        (
            "uq_indicative_family_active",
            "indicative_entry_episodes",
            ["workspace_id", "position_id", "kind"],
            f"closed_at IS NULL AND {FAMILY_FILTER}",
        ),
        (
            "uq_indicative_family_event",
            "indicative_entry_episodes",
            ["workspace_id", "position_id", "kind", "event_key"],
            FAMILY_FILTER,
        ),
        (
            "uq_indicative_family_number",
            "indicative_entry_episodes",
            ["workspace_id", "position_id", "kind", "episode_number"],
            FAMILY_FILTER,
        ),
    )
    for name, table, columns, predicate in definitions:
        op.create_index(
            name,
            table,
            columns,
            unique=True,
            postgresql_where=sa.text(predicate),
            sqlite_where=sa.text(predicate),
        )
    if op.get_bind().dialect.name == "postgresql":
        _guards(allow_family=True)


def _guards(*, allow_family: bool) -> None:
    # Opening versions remain immutable. Only predecessor and closure links
    # may cross the two explicitly known policies of this same rule family.
    version_match = "a.rule_version=NEW.rule_version"
    if allow_family:
        version_match = (
            f"({version_match} OR (a.rule_version IN {FAMILY} "
            f"AND NEW.rule_version IN {FAMILY}))"
        )
    op.execute(f"""
    CREATE OR REPLACE FUNCTION guard_indicative_entry_assessment()
    RETURNS trigger LANGUAGE plpgsql AS $$
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
             AND a.trade_id=NEW.trade_id AND {version_match})) THEN
        RAISE EXCEPTION 'Review assessment scope mismatch' USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $$
    """)
    op.execute(f"""
    CREATE OR REPLACE FUNCTION guard_indicative_entry_episode()
    RETURNS trigger LANGUAGE plpgsql AS $$
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
          AND a.trade_id=NEW.trade_id AND {version_match}
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


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM indicative_entry_assessments "
            "WHERE rule_version='indicative-entry-review-v2') OR EXISTS "
            "(SELECT 1 FROM indicative_entry_episodes "
            "WHERE rule_version='indicative-entry-review-v2')"
        )
    ).scalar():
        raise RuntimeError("Immutable V2 review history exists; destructive downgrade refused")
    if bind.dialect.name == "postgresql":
        _guards(allow_family=False)
    for name, table in (
        ("uq_indicative_family_number", "indicative_entry_episodes"),
        ("uq_indicative_family_event", "indicative_entry_episodes"),
        ("uq_indicative_family_active", "indicative_entry_episodes"),
        ("uq_indicative_family_root", "indicative_entry_assessments"),
    ):
        op.drop_index(name, table_name=table)
