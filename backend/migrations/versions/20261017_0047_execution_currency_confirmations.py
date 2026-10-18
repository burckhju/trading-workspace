"""Append-only user-confirmed currency provenance for exact execution IDs.

Revision ID: 20261017_0047
Revises: 20261014_0046
No execution values or historic currencies are inferred or backfilled.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261017_0047"
down_revision = "20261014_0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint("uq_trades_workspace_id_id", "trades", ["workspace_id", "id"])
    op.create_unique_constraint(
        "uq_execution_records_trade_id_id", "execution_records", ["trade_id", "id"]
    )
    op.create_table(
        "execution_currency_confirmations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("trade_id", sa.Uuid(), nullable=False),
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("currency_code", sa.String(3), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("note", sa.String(1000), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_by", sa.Uuid(), nullable=False),
        sa.Column("supersedes_confirmation_id", sa.Uuid(), nullable=True),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id", "trade_id"],
            ["trades.workspace_id", "trades.id"],
            name="fk_execution_currency_trade_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["trade_id", "execution_id"],
            ["execution_records.trade_id", "execution_records.id"],
            name="fk_execution_currency_execution_scope",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["currency_code"],
            ["currencies.code"],
            name="fk_execution_currency_code",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "id", "workspace_id", "trade_id", "execution_id", name="uq_execution_currency_identity"
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_confirmation_id", "workspace_id", "trade_id", "execution_id"],
            [
                "execution_currency_confirmations.id",
                "execution_currency_confirmations.workspace_id",
                "execution_currency_confirmations.trade_id",
                "execution_currency_confirmations.execution_id",
            ],
            name="fk_execution_currency_predecessor",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("supersedes_confirmation_id", name="uq_execution_currency_successor"),
        sa.UniqueConstraint("workspace_id", "request_id", name="uq_execution_currency_request"),
        sa.CheckConstraint("currency_code ~ '^[A-Z]{3}$'", name="execution_currency_code_valid"),
        sa.CheckConstraint("source = 'USER_CONFIRMED'", name="execution_currency_source_valid"),
        sa.CheckConstraint(
            "note IS NULL OR (length(trim(note)) BETWEEN 1 AND 1000)",
            name="execution_currency_note_valid",
        ),
        sa.CheckConstraint("id <> supersedes_confirmation_id", name="execution_currency_not_self"),
        sa.CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'", name="execution_currency_fingerprint_valid"
        ),
    )
    op.create_index(
        "uq_execution_currency_root",
        "execution_currency_confirmations",
        ["execution_id"],
        unique=True,
        postgresql_where=sa.text("supersedes_confirmation_id IS NULL"),
    )
    op.execute("""
    CREATE FUNCTION guard_execution_currency_confirmation() RETURNS trigger LANGUAGE plpgsql AS $$
    DECLARE cancelled timestamptz; predecessor_time timestamptz;
    BEGIN
      IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'execution currency confirmation is immutable'
          USING ERRCODE='23514', CONSTRAINT='tw_execution_currency_immutable';
      END IF;
      -- Commands and direct inserts share the existing bounded trade lock.
      SELECT cancelled_at INTO cancelled FROM trades
        WHERE id=NEW.trade_id AND workspace_id=NEW.workspace_id FOR UPDATE;
      IF NOT FOUND THEN
        RAISE EXCEPTION 'execution currency trade/workspace mismatch'
          USING ERRCODE='23503', CONSTRAINT='fk_execution_currency_trade_scope';
      END IF;
      IF cancelled IS NOT NULL THEN
        RAISE EXCEPTION 'cancelled trade does not accept new currency confirmations'
          USING ERRCODE='23514', CONSTRAINT='tw_execution_currency_cancelled';
      END IF;
      IF NEW.supersedes_confirmation_id IS NOT NULL THEN
        SELECT confirmed_at INTO predecessor_time FROM execution_currency_confirmations
          WHERE id=NEW.supersedes_confirmation_id AND workspace_id=NEW.workspace_id
            AND trade_id=NEW.trade_id AND execution_id=NEW.execution_id;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'execution currency predecessor mismatch'
            USING ERRCODE='23503', CONSTRAINT='fk_execution_currency_predecessor';
        END IF;
        IF NEW.confirmed_at < predecessor_time THEN
          RAISE EXCEPTION 'currency confirmation cannot precede its predecessor'
            USING ERRCODE='23514', CONSTRAINT='tw_execution_currency_chronology';
        END IF;
      END IF;
      RETURN NEW;
    END $$;
    """)
    op.execute("""
    CREATE TRIGGER trg_execution_currency_confirmation
      BEFORE INSERT OR UPDATE OR DELETE ON execution_currency_confirmations
      FOR EACH ROW EXECUTE FUNCTION guard_execution_currency_confirmation();
    """)


def downgrade() -> None:
    op.execute("""
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM execution_currency_confirmations) THEN
        RAISE EXCEPTION 'Refusing downgrade: execution currency provenance would be lost';
      END IF;
    END $$;
    """)
    op.drop_table("execution_currency_confirmations")
    op.execute("DROP FUNCTION guard_execution_currency_confirmation()")
    op.drop_constraint("uq_execution_records_trade_id_id", "execution_records", type_="unique")
    op.drop_constraint("uq_trades_workspace_id_id", "trades", type_="unique")
