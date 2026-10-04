"""Append-only risk configuration and qualified evaluation snapshots.

Revision ID: 20261004_0044
Revises: 20261004_0043
"""

import sqlalchemy as sa
from alembic import op

revision = "20261004_0044"
down_revision = "20261004_0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("SET LOCAL lock_timeout = '5s'")
    op.create_table(
        "position_risk_configurations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "position_id",
            sa.Uuid(),
            sa.ForeignKey("positions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("parameters", sa.JSON(), nullable=False),
        sa.Column("configured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.Uuid(), nullable=False),
        sa.Column("correlation_id", sa.String(100), nullable=True),
        sa.UniqueConstraint(
            "position_id", "revision", name="uq_position_risk_configuration_revision"
        ),
    )
    op.create_table(
        "position_risk_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.Uuid(),
            sa.ForeignKey("workspaces.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "position_id",
            sa.Uuid(),
            sa.ForeignKey("positions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("configuration_revision", sa.Integer(), nullable=False),
        sa.Column("input_fingerprint", sa.String(64), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "position_id", "input_fingerprint", name="uq_position_risk_snapshot_input"
        ),
    )
    op.create_index(
        "ix_position_risk_snapshot_position_time",
        "position_risk_snapshots",
        ["position_id", "evaluated_at"],
    )


def downgrade() -> None:
    for table in ("position_risk_configurations", "position_risk_snapshots"):
        if op.get_bind().scalar(sa.text(f"SELECT count(*) FROM {table}")):
            raise RuntimeError("Cannot downgrade: immutable risk history exists")
    op.drop_table("position_risk_snapshots")
    op.drop_table("position_risk_configurations")
