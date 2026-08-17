"""FT-010 execution correction supersession relation.

Revision ID: 20260817_0016
Revises: 20260817_0015
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260817_0016"
down_revision: str | None = "20260817_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "execution_records",
        sa.Column("supersedes_execution_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_execution_records_supersedes",
        "execution_records",
        "execution_records",
        ["supersedes_execution_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_execution_records_supersedes",
        "execution_records",
        ["supersedes_execution_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_execution_records_supersedes",
        "execution_records",
        type_="unique",
    )
    op.drop_constraint(
        "fk_execution_records_supersedes",
        "execution_records",
        type_="foreignkey",
    )
    op.drop_column("execution_records", "supersedes_execution_id")
