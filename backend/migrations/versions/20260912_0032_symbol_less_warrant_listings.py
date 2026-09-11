"""Allow warrant listings when a venue publishes no exchange symbol.

Revision ID: 20260912_0032
Revises: 20260903_0031
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260912_0032"
down_revision: str | None = "20260903_0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_PREVIOUS_SYMBOL_CHECK = "ck_warrant_listings_ck_warrant_listings_symbol_not_blank"
_CURRENT_SYMBOL_CHECK = "ck_warrant_listings_symbol_not_blank"


def upgrade() -> None:
    # 20260815_0011 created this check with a fully qualified name while the
    # metadata naming convention also prefixes check constraints. Mark the
    # persisted name as already formatted so Alembic does not prefix it again.
    op.drop_constraint(
        op.f(_PREVIOUS_SYMBOL_CHECK),
        "warrant_listings",
        type_="check",
    )
    op.alter_column(
        "warrant_listings",
        "symbol",
        existing_type=sa.String(length=64),
        nullable=True,
    )
    op.create_check_constraint(
        "symbol_not_blank",
        "warrant_listings",
        "symbol IS NULL OR length(trim(symbol)) > 0",
    )
    op.create_index(
        "uq_warrant_listings_symbol_less_warrant_venue",
        "warrant_listings",
        ["workspace_id", "warrant_id", "trading_venue_id"],
        unique=True,
        postgresql_where=sa.text("symbol IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_warrant_listings_symbol_less_warrant_venue",
        table_name="warrant_listings",
    )
    op.drop_constraint(
        op.f(_CURRENT_SYMBOL_CHECK),
        "warrant_listings",
        type_="check",
    )
    op.execute(
        "UPDATE warrant_listings "
        "SET symbol = 'NOSYM-' || left(replace(id::text, '-', ''), 32) "
        "WHERE symbol IS NULL"
    )
    op.alter_column(
        "warrant_listings",
        "symbol",
        existing_type=sa.String(length=64),
        nullable=False,
    )
    op.create_check_constraint(
        op.f(_PREVIOUS_SYMBOL_CHECK),
        "warrant_listings",
        "length(trim(symbol)) > 0",
    )
