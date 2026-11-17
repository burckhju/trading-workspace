"""Separate indicative and non-price review alerts; no activation or backfill.

Revision ID: 20261117_0056
Revises: 20261117_0055
"""

import sqlalchemy as sa
from alembic import op

revision = "20261117_0056"
down_revision = "20261117_0055"
branch_labels = None
depends_on = None

_OLD_TYPES = (
    "'STOP_REACHED', 'TARGET_REACHED', 'RISK_TREND_CHANGED', "
    "'RISK_VOLATILITY_HIGH', 'HEBELTRADER_B04_LOSS'"
)
_NEW_TYPES = "'INDICATIVE_ENTRY_LOSS', 'POSITION_REVIEW_DUE', 'POSITION_DATA_UNAVAILABLE'"


def upgrade() -> None:
    op.drop_constraint(op.f("ck_alerts_alert_type_valid"), "alerts", type_="check")
    op.create_check_constraint(
        op.f("ck_alerts_alert_type_valid"), "alerts", f"alert_type IN ({_OLD_TYPES}, {_NEW_TYPES})"
    )
    for column in ("observed_value", "threshold_value"):
        op.alter_column("alerts", column, existing_type=sa.Numeric(24, 10), nullable=True)
    op.create_check_constraint(
        op.f("ck_alerts_alert_value_shape"),
        "alerts",
        "(alert_type IN ('POSITION_REVIEW_DUE', 'POSITION_DATA_UNAVAILABLE') "
        "AND observed_value IS NULL AND threshold_value IS NULL) OR "
        "(alert_type NOT IN ('POSITION_REVIEW_DUE', 'POSITION_DATA_UNAVAILABLE') "
        "AND observed_value IS NOT NULL AND threshold_value IS NOT NULL)",
    )


def downgrade() -> None:
    if (
        op.get_bind()
        .execute(
            sa.text(f"SELECT EXISTS (SELECT 1 FROM alerts WHERE alert_type IN ({_NEW_TYPES}))")
        )
        .scalar()
    ):
        raise RuntimeError("Position review history exists; destructive downgrade refused")
    op.drop_constraint(op.f("ck_alerts_alert_value_shape"), "alerts", type_="check")
    for column in ("observed_value", "threshold_value"):
        op.alter_column("alerts", column, existing_type=sa.Numeric(24, 10), nullable=False)
    op.drop_constraint(op.f("ck_alerts_alert_type_valid"), "alerts", type_="check")
    op.create_check_constraint(
        op.f("ck_alerts_alert_type_valid"), "alerts", f"alert_type IN ({_OLD_TYPES})"
    )
