"""FT-010 deterministic position projection state.

Revision ID: 20260817_0017
Revises: 20260817_0016
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260817_0017"
down_revision: str | None = "20260817_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "positions",
        sa.Column(
            "realized_gross_pnl",
            sa.Numeric(30, 10),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "positions",
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.alter_column("positions", "realized_gross_pnl", server_default=None)

    op.drop_constraint(
        "ck_positions_open_quantity_positive",
        "positions",
        type_="check",
    )
    op.drop_constraint(
        "ck_positions_cost_basis_positive",
        "positions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_positions_open_quantity_non_negative",
        "positions",
        "open_quantity >= 0",
    )
    op.create_check_constraint(
        "ck_positions_cost_basis_non_negative",
        "positions",
        "cost_basis >= 0",
    )
    op.create_check_constraint(
        "ck_positions_position_state_consistent",
        "positions",
        "(open_quantity = 0 AND cost_basis = 0) "
        "OR (open_quantity > 0 AND cost_basis > 0)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_positions_position_state_consistent",
        "positions",
        type_="check",
    )
    op.drop_constraint(
        "ck_positions_cost_basis_non_negative",
        "positions",
        type_="check",
    )
    op.drop_constraint(
        "ck_positions_open_quantity_non_negative",
        "positions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_positions_cost_basis_positive",
        "positions",
        "cost_basis > 0",
    )
    op.create_check_constraint(
        "ck_positions_open_quantity_positive",
        "positions",
        "open_quantity > 0",
    )

    op.drop_column("positions", "closed_at")
    op.drop_column("positions", "realized_gross_pnl")
