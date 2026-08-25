"""FT-006 governed ModelVersion provenance.

Revision ID: 20260825_0024
Revises: 20260825_0023
"""

import sqlalchemy as sa
from alembic import op

revision = "20260825_0024"
down_revision = "20260825_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "market_analysis_runs",
        sa.Column("governed_model_version_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_market_analysis_runs_governed_model_version",
        "market_analysis_runs",
        "governed_model_versions",
        ["governed_model_version_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_market_analysis_runs_governed_model_version",
        "market_analysis_runs",
        ["governed_model_version_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_market_analysis_runs_governed_model_version",
        table_name="market_analysis_runs",
    )
    op.drop_constraint(
        "fk_market_analysis_runs_governed_model_version",
        "market_analysis_runs",
        type_="foreignkey",
    )
    op.drop_column("market_analysis_runs", "governed_model_version_id")
