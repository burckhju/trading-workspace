"""Position monitoring, alerts and notification delivery persistence.

Revision ID: 20260903_0030
Revises: 20260828_0029
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260903_0030"
down_revision: str | None = "20260828_0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("position_id", sa.Uuid(), nullable=False),
        sa.Column("trade_id", sa.Uuid(), nullable=False),
        sa.Column("alert_type", sa.String(length=40), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("rule_key", sa.String(length=200), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=False),
        sa.Column("observed_value", sa.Numeric(24, 10), nullable=False),
        sa.Column("threshold_value", sa.Numeric(24, 10), nullable=False),
        sa.Column("market_data_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("alert_type IN ('STOP_REACHED', 'TARGET_REACHED')", name="alert_type_valid"),
        sa.CheckConstraint("severity IN ('INFO', 'WARNING')", name="alert_severity_valid"),
        sa.CheckConstraint("status IN ('OPEN', 'RESOLVED')", name="alert_status_valid"),
        sa.ForeignKeyConstraint(["position_id"], ["positions.id"], name="fk_alerts_position", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["trade_id"], ["trades.id"], name="fk_alerts_trade", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_position_status_detected", "alerts", ["position_id", "status", "detected_at"])
    op.create_index("ix_alerts_trade_detected", "alerts", ["trade_id", "detected_at"])

    op.create_table(
        "monitoring_rule_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("position_id", sa.Uuid(), nullable=False),
        sa.Column("rule_key", sa.String(length=200), nullable=False),
        sa.Column("triggered", sa.Boolean(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_observed_value", sa.Numeric(24, 10), nullable=False),
        sa.Column("threshold_value", sa.Numeric(24, 10), nullable=False),
        sa.Column("active_alert_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["position_id"], ["positions.id"], name="fk_monitoring_rule_states_position", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["active_alert_id"], ["alerts.id"], name="fk_monitoring_rule_states_active_alert", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("position_id", "rule_key", name="uq_monitoring_rule_state_position_rule"),
    )
    op.create_index("ix_monitoring_rule_states_triggered", "monitoring_rule_states", ["triggered", "last_seen_at"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("alert_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("destination_key", sa.String(length=100), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.CheckConstraint("channel IN ('TELEGRAM')", name="notification_channel_valid"),
        sa.CheckConstraint("status IN ('PENDING', 'DELIVERED', 'FAILED')", name="notification_status_valid"),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"], name="fk_notifications_alert", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alert_id", "channel", "destination_key", name="uq_notification_alert_channel_destination"),
    )
    op.create_index("ix_notifications_status_created", "notifications", ["status", "created_at"])

    op.create_table(
        "notification_delivery_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("notification_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retryable", sa.Boolean(), nullable=False),
        sa.Column("provider_message_id", sa.String(length=200), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.CheckConstraint("attempt_number > 0", name="delivery_attempt_number_positive"),
        sa.CheckConstraint("status IN ('DELIVERED', 'FAILED')", name="delivery_attempt_status_valid"),
        sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"], name="fk_delivery_attempt_notification", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("notification_id", "attempt_number", name="uq_delivery_attempt_number"),
    )
    op.create_index("ix_delivery_attempt_notification_attempted", "notification_delivery_attempts", ["notification_id", "attempted_at"])


def downgrade() -> None:
    op.drop_index("ix_delivery_attempt_notification_attempted", table_name="notification_delivery_attempts")
    op.drop_table("notification_delivery_attempts")
    op.drop_index("ix_notifications_status_created", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_monitoring_rule_states_triggered", table_name="monitoring_rule_states")
    op.drop_table("monitoring_rule_states")
    op.drop_index("ix_alerts_trade_detected", table_name="alerts")
    op.drop_index("ix_alerts_position_status_detected", table_name="alerts")
    op.drop_table("alerts")
