"""Store exact issuer-page identity evidence on new warrant provider mappings.

Revision ID: 20260928_0042
Revises: 20260922_0041
"""

import sqlalchemy as sa
from alembic import op

revision = "20260928_0042"
down_revision = "20260922_0041"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("SET LOCAL lock_timeout = '5s'")
    op.add_column(
        "warrant_provider_mappings",
        sa.Column("identity_evidence", sa.JSON(none_as_null=True), nullable=True),
    )


def downgrade() -> None:
    if op.get_bind().scalar(
        sa.text(
            "SELECT count(*) FROM warrant_provider_mappings WHERE identity_evidence IS NOT NULL"
        )
    ):
        raise RuntimeError("Cannot downgrade: issuer route evidence exists")
    op.drop_column("warrant_provider_mappings", "identity_evidence")
