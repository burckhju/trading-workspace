"""Keep unknown source timestamps null and label rule-state ordering clocks.

Revision ID: 20260922_0041
Revises: 20260919_0040
"""

import sqlalchemy as sa
from alembic import op

revision = "20260922_0041"
down_revision = "20260919_0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("alerts") as batch:
        batch.alter_column(
            "market_data_observed_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=True,
        )
    op.add_column(
        "monitoring_rule_states",
        sa.Column(
            "time_basis", sa.String(24), nullable=False, server_default="SOURCE_TIMESTAMP"
        ),
    )


def downgrade() -> None:
    connection = op.get_bind()
    if connection.scalar(
        sa.text("SELECT count(*) FROM alerts WHERE market_data_observed_at IS NULL")
    ):
        raise RuntimeError("Cannot downgrade: alerts retain unknown source timestamps")
    if connection.scalar(
        sa.text(
            "SELECT count(*) FROM monitoring_rule_states WHERE time_basis != 'SOURCE_TIMESTAMP'"
        )
    ):
        raise RuntimeError("Cannot downgrade: receipt-ordered rule states exist")
    op.drop_column("monitoring_rule_states", "time_basis")
    with op.batch_alter_table("alerts") as batch:
        batch.alter_column(
            "market_data_observed_at",
            existing_type=sa.DateTime(timezone=True),
            nullable=False,
        )
