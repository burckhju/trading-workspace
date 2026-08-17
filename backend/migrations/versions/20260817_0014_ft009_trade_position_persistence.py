"""FT-009 trade and position persistence.

Revision ID: 20260817_0014
Revises: 20260816_0013
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260817_0014"
down_revision: str | None = "20260816_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trades",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("origin", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("trade_plan_id", sa.Uuid(), nullable=True),
        sa.Column("trade_plan_version_id", sa.Uuid(), nullable=True),
        sa.Column("product_selection_id", sa.Uuid(), nullable=True),
        sa.Column("product_evaluation_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            """
            (
                origin = 'WORKSPACE_SELECTION'
                AND trade_plan_id IS NOT NULL
                AND trade_plan_version_id IS NOT NULL
                AND product_selection_id IS NOT NULL
                AND product_evaluation_id IS NOT NULL
            )
            OR
            (
                origin = 'EXTERNAL'
                AND trade_plan_id IS NULL
                AND trade_plan_version_id IS NULL
                AND product_selection_id IS NULL
                AND product_evaluation_id IS NULL
            )
            """,
            name="ck_trades_origin_provenance",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="RESTRICT",
            name="fk_trades_workspace",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["warrants.id"],
            ondelete="RESTRICT",
            name="fk_trades_product",
        ),
        sa.ForeignKeyConstraint(
            ["trade_plan_id"],
            ["trade_plans.id"],
            ondelete="RESTRICT",
            name="fk_trades_trade_plan",
        ),
        sa.ForeignKeyConstraint(
            ["trade_plan_version_id"],
            ["trade_plan_versions.id"],
            ondelete="RESTRICT",
            name="fk_trades_trade_plan_version",
        ),
        sa.ForeignKeyConstraint(
            ["product_selection_id"],
            ["product_selections.id"],
            ondelete="RESTRICT",
            name="fk_trades_product_selection",
        ),
        sa.ForeignKeyConstraint(
            ["product_evaluation_id"],
            ["product_evaluations.id"],
            ondelete="RESTRICT",
            name="fk_trades_product_evaluation",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_trades_workspace_created",
        "trades",
        ["workspace_id", "created_at"],
    )

    op.create_table(
        "execution_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trade_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price_per_unit", sa.Numeric(24, 10), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), nullable=False),
        sa.CheckConstraint(
            "quantity > 0",
            name="ck_execution_records_quantity_positive",
        ),
        sa.CheckConstraint(
            "price_per_unit > 0",
            name="ck_execution_records_price_positive",
        ),
        sa.CheckConstraint(
            "recorded_at >= executed_at",
            name="ck_execution_records_recorded_not_before_executed",
        ),
        sa.ForeignKeyConstraint(
            ["trade_id"],
            ["trades.id"],
            ondelete="RESTRICT",
            name="fk_execution_records_trade",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["warrants.id"],
            ondelete="RESTRICT",
            name="fk_execution_records_product",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_execution_records_trade_executed",
        "execution_records",
        ["trade_id", "executed_at"],
    )

    op.create_table(
        "positions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trade_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("open_quantity", sa.Integer(), nullable=False),
        sa.Column("cost_basis", sa.Numeric(30, 10), nullable=False),
        sa.Column("average_entry_price", sa.Numeric(24, 10), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_execution_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "open_quantity > 0",
            name="ck_positions_open_quantity_positive",
        ),
        sa.CheckConstraint(
            "cost_basis > 0",
            name="ck_positions_cost_basis_positive",
        ),
        sa.CheckConstraint(
            "average_entry_price > 0",
            name="ck_positions_average_entry_price_positive",
        ),
        sa.CheckConstraint(
            "last_execution_at >= opened_at",
            name="ck_positions_last_execution_not_before_opened",
        ),
        sa.ForeignKeyConstraint(
            ["trade_id"],
            ["trades.id"],
            ondelete="RESTRICT",
            name="fk_positions_trade",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["warrants.id"],
            ondelete="RESTRICT",
            name="fk_positions_product",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "trade_id",
            name="uq_positions_trade",
        ),
    )

    op.create_index(
        "ix_positions_product",
        "positions",
        ["product_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_positions_product",
        table_name="positions",
    )
    op.drop_table("positions")

    op.drop_index(
        "ix_execution_records_trade_executed",
        table_name="execution_records",
    )
    op.drop_table("execution_records")

    op.drop_index(
        "ix_trades_workspace_created",
        table_name="trades",
    )
    op.drop_table("trades")
