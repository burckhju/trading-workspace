"""Store reviewed currency catalogs without changing existing currency permissions.

Revision ID: 20260912_0035
Revises: 20260912_0034
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260912_0035"
down_revision: str | None = "20260912_0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "currency_catalog_releases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("document", postgresql.JSONB(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_currency_catalog_releases")),
        sa.UniqueConstraint("version", name=op.f("uq_currency_catalog_releases_version")),
        sa.UniqueConstraint("checksum", name=op.f("uq_currency_catalog_releases_checksum")),
    )
    op.create_table(
        "currency_catalog_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("release_id", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_currency_catalog_state")),
        sa.CheckConstraint("id = 1", name=op.f("ck_currency_catalog_state_singleton")),
        sa.ForeignKeyConstraint(
            ["release_id"],
            ["currency_catalog_releases.id"],
            name=op.f("fk_currency_catalog_state_release_id_currency_catalog_releases"),
            ondelete="RESTRICT",
        ),
    )
    op.execute(sa.text("INSERT INTO currency_catalog_state (id, release_id) VALUES (1, NULL)"))
    # No alteration or backfill of currencies, warrant terms or historical prices.


def downgrade() -> None:
    # Catalog metadata is lost on downgrade; export/back up before rollback.
    # Locally enabled currency rows and their existing product references remain intact.
    op.drop_table("currency_catalog_state")
    op.drop_table("currency_catalog_releases")
