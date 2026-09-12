"""Auditable trade cancellation and one open trade per workspace / warrant.

Revision ID: 20260912_0036
Revises: 20260912_0035

Existing duplicates are retained for explicit operator cancellation. No user IDs,
executions, positions or prices are changed by this migration.
"""

import re
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260912_0036"
down_revision: str | None = "20260912_0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _execute(script: str) -> None:
    for statement in re.split(r"\n(?=CREATE (?:FUNCTION|TRIGGER))", script.strip()):
        op.execute(statement)


def upgrade() -> None:
    for column in (
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by", sa.Uuid(), nullable=True),
        sa.Column("cancellation_reason", sa.String(1000), nullable=True),
        sa.Column("duplicate_of_trade_id", sa.Uuid(), nullable=True),
    ):
        op.add_column("trades", column)
    op.create_foreign_key(
        "fk_trades_duplicate_of",
        "trades",
        "trades",
        ["duplicate_of_trade_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "cancellation_consistent",
        "trades",
        "(cancelled_at IS NULL AND cancelled_by IS NULL AND cancellation_reason IS NULL AND duplicate_of_trade_id IS NULL) OR "
        "(cancelled_at IS NOT NULL AND cancelled_by IS NOT NULL AND cancellation_reason IS NOT NULL AND length(trim(cancellation_reason)) > 0)",
    )
    op.add_column("execution_records", sa.Column("executed_on", sa.Date(), nullable=True))
    op.add_column(
        "execution_records", sa.Column("execution_timezone", sa.String(64), nullable=True)
    )
    op.create_check_constraint(
        "execution_calendar_consistent",
        "execution_records",
        "(executed_on IS NULL) = (execution_timezone IS NULL)",
    )
    for name in ("opened_on", "last_execution_on", "closed_on"):
        op.add_column("positions", sa.Column(name, sa.Date(), nullable=True))
    op.add_column("execution_records", sa.Column("request_key", sa.String(64), nullable=True))
    op.add_column(
        "execution_records", sa.Column("request_fingerprint", sa.String(64), nullable=True)
    )
    op.create_unique_constraint(
        "uq_execution_records_request_key", "execution_records", ["request_key"]
    )
    op.create_check_constraint(
        "request_identity_consistent",
        "execution_records",
        "(request_key IS NULL) = (request_fingerprint IS NULL)",
    )
    op.create_index(
        "ix_positions_product_open",
        "positions",
        ["product_id"],
        postgresql_where=sa.text("open_quantity > 0"),
    )

    # A partial unique index cannot be added while legacy duplicates remain. This
    # lock + trigger enforces NEW/reopened positions without silently resolving old data.
    _execute("""
CREATE FUNCTION enforce_single_open_warrant_trade() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE parent trades%ROWTYPE; other_id uuid;
BEGIN
    SELECT * INTO parent FROM trades WHERE id = NEW.trade_id FOR UPDATE;
    IF parent.id IS NULL OR parent.product_id <> NEW.product_id THEN
        RAISE EXCEPTION 'position/trade product mismatch' USING ERRCODE='23514', CONSTRAINT='tw_position_identity';
    END IF;
    IF parent.cancelled_at IS NOT NULL THEN
        RAISE EXCEPTION 'cancelled trade is read only' USING ERRCODE='23514', CONSTRAINT='tw_cancelled_trade_write';
    END IF;
    IF TG_OP = 'UPDATE' THEN
        IF NEW.trade_id <> OLD.trade_id OR NEW.product_id <> OLD.product_id THEN
            RAISE EXCEPTION 'position identity is immutable' USING ERRCODE='23514', CONSTRAINT='tw_position_identity';
        END IF;
        IF OLD.open_quantity > 0 OR NEW.open_quantity = 0 THEN RETURN NEW; END IF;
    END IF;
    IF NEW.open_quantity = 0 THEN RETURN NEW; END IF;
    PERFORM 1 FROM warrants WHERE id = NEW.product_id AND workspace_id = parent.workspace_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'position workspace/product mismatch' USING ERRCODE='23514', CONSTRAINT='tw_position_identity';
    END IF;
    SELECT t.id INTO other_id FROM trades t JOIN positions p ON p.trade_id=t.id
    WHERE t.workspace_id=parent.workspace_id AND t.product_id=NEW.product_id
      AND t.cancelled_at IS NULL AND p.open_quantity>0 AND t.id<>NEW.trade_id
    ORDER BY t.created_at,t.id LIMIT 1;
    IF other_id IS NOT NULL THEN
        RAISE EXCEPTION 'another open trade exists: %', other_id USING ERRCODE='23505', CONSTRAINT='tw_one_open_trade';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER single_open_warrant_trade BEFORE INSERT OR UPDATE ON positions
FOR EACH ROW EXECUTE FUNCTION enforce_single_open_warrant_trade();
""")
    _execute("""
CREATE FUNCTION enforce_trade_cancellation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.product_id <> OLD.product_id OR NEW.workspace_id <> OLD.workspace_id THEN
        RAISE EXCEPTION 'trade identity is immutable' USING ERRCODE='23514', CONSTRAINT='tw_trade_identity';
    END IF;
    IF OLD.cancelled_at IS NOT NULL AND
      (NEW.cancelled_at,NEW.cancelled_by,NEW.cancellation_reason,NEW.duplicate_of_trade_id)
      IS DISTINCT FROM (OLD.cancelled_at,OLD.cancelled_by,OLD.cancellation_reason,OLD.duplicate_of_trade_id) THEN
        RAISE EXCEPTION 'cancellation is immutable' USING ERRCODE='23514', CONSTRAINT='tw_cancelled_trade_write';
    END IF;
    IF OLD.cancelled_at IS NULL AND NEW.cancelled_at IS NOT NULL THEN
        IF EXISTS(SELECT 1 FROM execution_records WHERE trade_id=NEW.id AND side='SELL')
          OR EXISTS(SELECT 1 FROM post_trade_observations WHERE trade_id=NEW.id)
          OR EXISTS(SELECT 1 FROM trade_journals WHERE trade_id=NEW.id)
          OR EXISTS(SELECT 1 FROM ft011_evidence WHERE trade_id=NEW.id)
          OR EXISTS(SELECT 1 FROM external_observation_trade_link_versions WHERE trade_id=NEW.id) THEN
            RAISE EXCEPTION 'dependent sale/review/learning records require separate correction'
              USING ERRCODE='23514', CONSTRAINT='tw_cancellation_dependencies';
        END IF;
        IF NEW.duplicate_of_trade_id IS NOT NULL AND NOT EXISTS(
            SELECT 1 FROM trades t JOIN positions p ON p.trade_id=t.id
            WHERE t.id=NEW.duplicate_of_trade_id AND t.id<>NEW.id
              AND t.workspace_id=NEW.workspace_id AND t.product_id=NEW.product_id
              AND t.cancelled_at IS NULL AND p.open_quantity>0
        ) THEN
            RAISE EXCEPTION 'retained duplicate target must be an open trade of the same product'
              USING ERRCODE='23514', CONSTRAINT='tw_cancellation_dependencies';
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trade_cancellation_guard BEFORE UPDATE ON trades
FOR EACH ROW EXECUTE FUNCTION enforce_trade_cancellation();
CREATE FUNCTION reject_cancelled_trade_fact() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE cancelled timestamptz;
BEGIN
    SELECT cancelled_at INTO cancelled FROM trades WHERE id=NEW.trade_id FOR UPDATE;
    IF cancelled IS NOT NULL THEN
        RAISE EXCEPTION 'cancelled trade is read only' USING ERRCODE='23514', CONSTRAINT='tw_cancelled_trade_write';
    END IF;
    RETURN NEW;
END $$;
""")
    for table in (
        "execution_records",
        "trade_management_events",
        "alerts",
        "post_trade_observations",
        "trade_journals",
        "ft011_evidence",
        "external_observation_trade_link_versions",
    ):
        op.execute(
            f"CREATE TRIGGER active_trade_fact BEFORE INSERT ON {table} FOR EACH ROW EXECUTE FUNCTION reject_cancelled_trade_fact()"
        )

    _execute("""
CREATE FUNCTION reject_cancelled_trade_notification() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE cancelled timestamptz;
BEGIN
    SELECT t.cancelled_at INTO cancelled FROM trades t JOIN alerts a ON a.trade_id=t.id
      WHERE a.id=NEW.alert_id FOR UPDATE OF t;
    IF cancelled IS NOT NULL THEN
        RAISE EXCEPTION 'cancelled trade cannot create notifications'
          USING ERRCODE='23514', CONSTRAINT='tw_cancelled_trade_write';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER active_trade_notification BEFORE INSERT ON notifications
FOR EACH ROW EXECUTE FUNCTION reject_cancelled_trade_notification();
""")


def downgrade() -> None:
    # Do not permit rollback to software that would resurrect cancelled positions.
    op.execute("""DO $$ BEGIN
      IF EXISTS(SELECT 1 FROM trades WHERE cancelled_at IS NOT NULL) THEN
        RAISE EXCEPTION 'Cannot remove trade cancellation support while cancelled trades exist';
      END IF;
    END $$""")
    for table in (
        "execution_records",
        "trade_management_events",
        "alerts",
        "post_trade_observations",
        "trade_journals",
        "ft011_evidence",
        "external_observation_trade_link_versions",
    ):
        op.execute(f"DROP TRIGGER active_trade_fact ON {table}")
    op.execute("DROP TRIGGER active_trade_notification ON notifications")
    op.execute("DROP FUNCTION reject_cancelled_trade_notification()")
    op.execute("DROP FUNCTION reject_cancelled_trade_fact()")
    op.execute("DROP TRIGGER trade_cancellation_guard ON trades")
    op.execute("DROP FUNCTION enforce_trade_cancellation()")
    op.execute("DROP TRIGGER single_open_warrant_trade ON positions")
    op.execute("DROP FUNCTION enforce_single_open_warrant_trade()")
    op.drop_index("ix_positions_product_open", table_name="positions")
    op.drop_constraint(
        op.f("ck_execution_records_request_identity_consistent"), "execution_records", type_="check"
    )
    op.drop_constraint("uq_execution_records_request_key", "execution_records", type_="unique")
    op.drop_column("execution_records", "request_fingerprint")
    op.drop_column("execution_records", "request_key")
    for name in ("opened_on", "last_execution_on", "closed_on"):
        op.drop_column("positions", name)
    op.drop_constraint(
        op.f("ck_execution_records_execution_calendar_consistent"),
        "execution_records",
        type_="check",
    )
    op.drop_column("execution_records", "execution_timezone")
    op.drop_column("execution_records", "executed_on")
    op.drop_constraint(op.f("ck_trades_cancellation_consistent"), "trades", type_="check")
    op.drop_constraint("fk_trades_duplicate_of", "trades", type_="foreignkey")
    for name in ("duplicate_of_trade_id", "cancellation_reason", "cancelled_by", "cancelled_at"):
        op.drop_column("trades", name)
