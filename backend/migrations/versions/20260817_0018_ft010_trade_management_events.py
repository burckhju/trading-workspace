"""FT-010 immutable trade management events.

Revision ID: 20260817_0018
Revises: 20260817_0017
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260817_0018"
down_revision: str | None = "20260817_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trade_management_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trade_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), nullable=False),
        sa.Column("numeric_value", sa.Numeric(24, 10), nullable=True),
        sa.Column("text_value", sa.String(length=4000), nullable=True),
        sa.Column("supersedes_event_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "event_type IN ('STOP_CHANGED', 'TARGET_CHANGED', "
            "'THESIS_UPDATED', 'MANAGEMENT_NOTE')",
            name="ck_trade_management_events_event_type_valid",
        ),
        sa.CheckConstraint(
            "recorded_at >= effective_at",
            name="ck_trade_management_events_recorded_not_before_effective",
        ),
        sa.CheckConstraint(
            """
            (
                event_type IN ('STOP_CHANGED', 'TARGET_CHANGED')
                AND numeric_value IS NOT NULL
                AND numeric_value > 0
                AND text_value IS NULL
            )
            OR
            (
                event_type IN ('THESIS_UPDATED', 'MANAGEMENT_NOTE')
                AND text_value IS NOT NULL
                AND numeric_value IS NULL
            )
            """,
            name="ck_trade_management_events_payload_valid",
        ),
        sa.ForeignKeyConstraint(
            ["trade_id"],
            ["trades.id"],
            ondelete="RESTRICT",
            name="fk_trade_management_events_trade",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_event_id"],
            ["trade_management_events.id"],
            ondelete="RESTRICT",
            name="fk_trade_management_events_supersedes",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "supersedes_event_id",
            name="uq_trade_management_events_supersedes",
        ),
    )
    op.create_index(
        "ix_trade_management_events_trade_effective",
        "trade_management_events",
        ["trade_id", "effective_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_trade_management_events_trade_effective",
        table_name="trade_management_events",
    )
    op.drop_table("trade_management_events")
