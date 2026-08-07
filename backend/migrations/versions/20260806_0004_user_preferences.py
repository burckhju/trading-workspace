"""Create actor-scoped user preferences.

Revision ID: 20260806_0004
Revises: 20260805_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260806_0004"
down_revision: str | None = "20260805_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(80), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "actor_id",
            "kind",
            "name",
            name="uq_user_preferences_scope_name",
        ),
    )
    op.create_index(
        "ix_user_preferences_scope",
        "user_preferences",
        ["workspace_id", "actor_id", "kind"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_preferences_scope", table_name="user_preferences")
    op.drop_table("user_preferences")
