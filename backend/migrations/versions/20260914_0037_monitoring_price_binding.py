"""Explicit rule meaning and alert provenance; no reinterpretation of user prices.

Revision ID: 20260914_0037
Revises: 20260912_0036
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260914_0037"
down_revision: str | None = "20260912_0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(op.f("ck_alerts_alert_status_valid"), "alerts", type_="check")
    op.create_check_constraint(
        op.f("ck_alerts_alert_status_valid"),
        "alerts",
        "status IN ('OPEN', 'RESOLVED', 'INVALIDATED')",
    )
    op.add_column(
        "trade_management_events",
        sa.Column("price_binding", sa.JSON(none_as_null=True), nullable=True),
    )
    op.add_column(
        "monitoring_rule_states", sa.Column("price_binding_key", sa.String(100), nullable=True)
    )
    op.add_column("alerts", sa.Column("price_context", sa.JSON(none_as_null=True), nullable=True))
    op.add_column("alerts", sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("alerts", sa.Column("invalidation_reason", sa.String(100), nullable=True))


def downgrade() -> None:
    # Intentionally fail if INVALIDATED history exists; never silently rewrite it.
    op.drop_constraint(op.f("ck_alerts_alert_status_valid"), "alerts", type_="check")
    op.create_check_constraint(
        op.f("ck_alerts_alert_status_valid"), "alerts", "status IN ('OPEN', 'RESOLVED')"
    )
    for name in ("invalidation_reason", "invalidated_at", "price_context"):
        op.drop_column("alerts", name)
    op.drop_column("monitoring_rule_states", "price_binding_key")
    op.drop_column("trade_management_events", "price_binding")
