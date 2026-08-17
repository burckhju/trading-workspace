"""FT-010 execution side evolution.

Revision ID: 20260817_0015
Revises: 20260817_0014
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260817_0015"
down_revision: str | None = "20260817_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "execution_records",
        sa.Column(
            "side",
            sa.String(length=16),
            nullable=False,
            server_default="BUY",
        ),
    )
    op.create_check_constraint(
        "ck_execution_records_side_valid",
        "execution_records",
        "side IN ('BUY', 'SELL')",
    )
    op.alter_column(
        "execution_records",
        "side",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_execution_records_side_valid",
        "execution_records",
        type_="check",
    )
    op.drop_column("execution_records", "side")
