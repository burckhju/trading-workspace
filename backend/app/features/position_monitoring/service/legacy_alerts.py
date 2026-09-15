"""Quarantine legacy alerts whose instrument/currency meaning was never recorded."""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.alert.persistence.models import AlertModel
from app.features.position_monitoring.persistence.models import MonitoringRuleStateModel


async def invalidate_unbound_alerts(session: AsyncSession, *, now: datetime) -> int:
    ids = tuple(
        (
            await session.scalars(
                select(AlertModel.id)
                .where(
                    AlertModel.status == "OPEN",
                    AlertModel.price_context.is_(None),
                )
                .with_for_update()
            )
        ).all()
    )
    if not ids:
        return 0
    await session.execute(
        update(AlertModel)
        .where(AlertModel.id.in_(ids))
        .values(
            status="INVALIDATED",
            invalidated_at=now,
            invalidation_reason="LEGACY_RULE_PRICE_BASIS_UNCONFIRMED",
        )
    )
    await session.execute(
        update(MonitoringRuleStateModel)
        .where(MonitoringRuleStateModel.active_alert_id.in_(ids))
        .values(triggered=False, active_alert_id=None, first_seen_at=None)
    )
    await session.commit()
    return len(ids)
