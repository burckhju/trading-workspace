"""Seed gettex MIC venues used by delayed quote mappings.

Revision ID: 20260919_0040
Revises: 20260918_0039
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision: str = "20260919_0040"
down_revision: str | None = "20260918_0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MUND_ID = UUID("da6686fe-4ce8-5b53-8ea5-709f2890490a")
_MUNC_ID = UUID("9014559f-a847-55c4-b52e-37fd2cd98ed1")
_REFERENCE_VERSION = "ISO10383-2026-08-10"


def upgrade() -> None:
    connection = op.get_bind()
    table = sa.table(
        "trading_venues",
        sa.column("id", sa.Uuid()),
        sa.column("mic", sa.String()),
        sa.column("name", sa.String()),
        sa.column("country_code", sa.String()),
        sa.column("timezone", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("reference_version", sa.String()),
        sa.column("version", sa.Integer()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    now = datetime.now(UTC)
    venues = (
        (
            _MUND_ID,
            "MUND",
            "BOERSE MUENCHEN - GETTEX - FREIVERKEHR",
        ),
        (
            _MUNC_ID,
            "MUNC",
            "BOERSE MUENCHEN - GETTEX - REGULIERTER MARKT",
        ),
    )
    for venue_id, mic, name in venues:
        existing = connection.execute(
            sa.select(table.c.id, table.c.name, table.c.country_code, table.c.timezone).where(
                table.c.mic == mic
            )
        ).one_or_none()
        if existing is not None:
            if (
                existing.name != name
                or existing.country_code != "DE"
                or existing.timezone != "Europe/Berlin"
            ):
                raise RuntimeError(f"{mic}_REFERENCE_DATA_CONFLICT")
            continue
        connection.execute(
            table.insert().values(
                id=venue_id,
                mic=mic,
                name=name,
                country_code="DE",
                timezone="Europe/Berlin",
                is_active=True,
                reference_version=_REFERENCE_VERSION,
                version=1,
                created_at=now,
                updated_at=now,
            )
        )


def downgrade() -> None:
    connection = op.get_bind()
    table = sa.table(
        "trading_venues",
        sa.column("id", sa.Uuid()),
        sa.column("mic", sa.String()),
    )
    connection.execute(
        table.delete().where(
            table.c.id.in_((_MUND_ID, _MUNC_ID)),
            table.c.mic.in_(("MUND", "MUNC")),
        )
    )
