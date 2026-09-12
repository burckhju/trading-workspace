"""Provide USD and CHF reference data for monetary warrant strikes.

Revision ID: 20260912_0034
Revises: 20260912_0033
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import insert

revision: str = "20260912_0034"
down_revision: str | None = "20260912_0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Application seed version, not a claim about the publication date of ISO 4217.
REFERENCE_VERSION = "TW-CURRENCIES-20260912"


def upgrade() -> None:
    currencies = sa.table(
        "currencies",
        sa.column("code", sa.String(3)),
        sa.column("name", sa.String(100)),
        sa.column("minor_unit", sa.SmallInteger()),
        sa.column("is_active", sa.Boolean()),
        sa.column("reference_version", sa.String(50)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(UTC)
    rows = [
        {
            "code": code,
            "name": name,
            "minor_unit": 2,
            "is_active": True,
            "reference_version": REFERENCE_VERSION,
            "created_at": now,
            "updated_at": now,
        }
        for code, name in (("USD", "US Dollar"), ("CHF", "Swiss Franc"))
    ]
    # Preserve existing names, provenance, timestamps and deliberate deactivations.
    # The EUR-only initial migration remains immutable. Never backfill product terms.
    op.execute(insert(currencies).values(rows).on_conflict_do_nothing(index_elements=["code"]))


def downgrade() -> None:
    # Data-preserving rollback: currencies may already be referenced by listings or
    # historical terms. Removing them would lose data or violate foreign keys.
    # Re-upgrade is safe because the insert is idempotent.
    pass
