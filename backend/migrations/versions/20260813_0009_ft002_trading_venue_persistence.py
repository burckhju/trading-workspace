"""FT-002 trading venue persistence hardening.

Revision ID: 20260813_0009
Revises: 20260811_0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260813_0009"
down_revision: str | None = "20260811_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("trading_venues", sa.Column("version", sa.Integer(), nullable=True))
    op.execute("UPDATE trading_venues SET mic = upper(trim(mic)), version = 1")
    op.alter_column("trading_venues", "version", nullable=False)
    op.create_check_constraint(
        "ck_trading_venues_mic_uppercase", "trading_venues", "mic = upper(mic)"
    )
    op.create_check_constraint(
        "ck_trading_venues_version_positive", "trading_venues", "version >= 1"
    )
    op.alter_column("audit_events", "workspace_id", existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    # Global FT-002 audit rows cannot satisfy the pre-S7A NOT NULL workspace contract.
    # Removing only TradingVenue audit rows is the narrow, explicit rollback behavior.
    op.execute(
        "DELETE FROM audit_events "
        "WHERE workspace_id IS NULL AND aggregate_type = 'TRADING_VENUE'"
    )
    op.alter_column("audit_events", "workspace_id", existing_type=sa.Uuid(), nullable=False)
    op.drop_constraint("ck_trading_venues_version_positive", "trading_venues", type_="check")
    op.drop_constraint("ck_trading_venues_mic_uppercase", "trading_venues", type_="check")
    op.drop_column("trading_venues", "version")
