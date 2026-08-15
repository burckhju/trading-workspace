"""FT-003 issuer reference-data persistence.

Revision ID: 20260815_0010
Revises: 20260813_0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260815_0010"
down_revision: str | None = "20260813_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "issuers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("legal_name", sa.String(length=200), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=True),
        sa.Column("lei", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(trim(legal_name)) > 0",
            name="ck_issuers_legal_name_not_blank",
        ),
        sa.CheckConstraint(
            "length(trim(display_name)) > 0",
            name="ck_issuers_display_name_not_blank",
        ),
        sa.CheckConstraint(
            "country_code IS NULL OR "
            "(length(country_code) = 2 AND country_code = upper(country_code))",
            name="ck_issuers_country_code_iso_shape",
        ),
        sa.CheckConstraint(
            "lei IS NULL OR (length(lei) = 20 AND lei = upper(lei))",
            name="ck_issuers_lei_canonical_shape",
        ),
        sa.CheckConstraint("version >= 1", name="ck_issuers_version_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lei", name="uq_issuers_lei"),
    )


def downgrade() -> None:
    op.drop_table("issuers")
