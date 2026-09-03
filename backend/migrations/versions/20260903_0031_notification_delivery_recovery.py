"""Allow persisted in-progress notification delivery attempts.

Revision ID: 20260903_0031
Revises: 20260903_0030
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260903_0031"
down_revision: str | None = "20260903_0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "delivery_attempt_status_valid",
        "notification_delivery_attempts",
        type_="check",
    )
    op.create_check_constraint(
        "delivery_attempt_status_valid",
        "notification_delivery_attempts",
        "status IN ('IN_PROGRESS', 'DELIVERED', 'FAILED')",
    )


def downgrade() -> None:
    op.execute(
        "UPDATE notification_delivery_attempts "
        "SET status = 'FAILED', completed_at = COALESCE(completed_at, attempted_at), "
        "retryable = TRUE, error_code = COALESCE(error_code, 'DOWNGRADE_RECOVERY') "
        "WHERE status = 'IN_PROGRESS'"
    )
    op.drop_constraint(
        "delivery_attempt_status_valid",
        "notification_delivery_attempts",
        type_="check",
    )
    op.create_check_constraint(
        "delivery_attempt_status_valid",
        "notification_delivery_attempts",
        "status IN ('DELIVERED', 'FAILED')",
    )
