"""Alert-owned invalidation for explicitly superseded risk configurations."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.alert.persistence.models import AlertModel


async def invalidate_risk_alerts(
    session: AsyncSession,
    *,
    position_id: UUID,
    now: datetime,
    preserve_keys: tuple[str, ...] = (),
) -> None:
    rows = (
        await session.scalars(
            select(AlertModel)
            .where(
                AlertModel.position_id == position_id,
                AlertModel.rule_key.startswith("POSITION_RISK_V1:"),
                AlertModel.status == "OPEN",
            )
            .with_for_update()
        )
    ).all()
    for row in rows:
        if row.rule_key not in preserve_keys:
            row.status = "INVALIDATED"
            row.invalidated_at = now
            row.invalidation_reason = "RISK_CONFIGURATION_OR_IDENTITY_SUPERSEDED"
