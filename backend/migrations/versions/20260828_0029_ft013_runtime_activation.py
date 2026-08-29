"""FT-013 runtime activation history.

Revision ID: 20260828_0029
Revises: 20260827_0028
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260828_0029"
down_revision: str | None = "20260827_0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "model_runtime_activations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("model_id", sa.Uuid(), nullable=False),
        sa.Column("model_version_id", sa.Uuid(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_by", sa.Uuid(), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(
            ["workspace_id"], ["workspaces.id"], name="fk_runtime_activation_workspace", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["model_id"], ["governed_models.id"], name="fk_runtime_activation_model", ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["model_version_id"],
            ["governed_model_versions.id"],
            name="fk_runtime_activation_version",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_runtime_activation_model_activated",
        "model_runtime_activations",
        ["model_id", "activated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_runtime_activation_model_activated", table_name="model_runtime_activations")
    op.drop_table("model_runtime_activations")
