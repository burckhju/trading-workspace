"""FT-012 review signal opened_by audit field."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260824_0021"
down_revision = "20260820_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "lesson_review_signals",
        sa.Column(
            "opened_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "lesson_review_signals",
        "opened_by",
    )
