"""Record strike currency separately from the warrant listing currency.

Revision ID: 20260912_0033
Revises: 20260912_0032
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260912_0033"
down_revision: str | None = "20260912_0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing terms remain explicitly unknown. Neither the listing currency,
    # issuer domicile nor a default of EUR is evidence for the strike currency.
    op.add_column(
        "warrant_terms_versions",
        sa.Column("strike_currency_code", sa.String(length=3), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_warrant_terms_strike_currency"),
        "warrant_terms_versions",
        "currencies",
        ["strike_currency_code"],
        ["code"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "strike_currency_valid",
        "warrant_terms_versions",
        "strike_currency_code IS NULL OR "
        "(length(strike_currency_code) = 3 AND "
        "strike_currency_code = upper(strike_currency_code))",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_warrant_terms_versions_strike_currency_valid"),
        "warrant_terms_versions",
        type_="check",
    )
    op.drop_constraint(
        op.f("fk_warrant_terms_strike_currency"),
        "warrant_terms_versions",
        type_="foreignkey",
    )
    op.drop_column("warrant_terms_versions", "strike_currency_code")
