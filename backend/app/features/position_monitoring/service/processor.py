from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.alert.persistence.repositories import SqlAlchemyAlertRepository
from app.features.position_monitoring.domain.models import MonitoringRule, PriceObservation
from app.features.position_monitoring.persistence.repositories import (
    SqlAlchemyMonitoringRuleStateRepository,
)
from app.features.position_monitoring.service.application import (
    MonitoringEvaluationResult,
    PositionMonitoringService,
)


class SqlAlchemyMonitoringRuleProcessor:
    """Persist each rule transition atomically so one bad position cannot poison the cycle."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._service = PositionMonitoringService(
            states=SqlAlchemyMonitoringRuleStateRepository(session),
            alerts=SqlAlchemyAlertRepository(session),
            new_id=uuid4,
            now=lambda: datetime.now(UTC),
        )

    async def process(
        self,
        *,
        position_id: UUID,
        trade_id: UUID,
        rule: MonitoringRule,
        observation: PriceObservation,
    ) -> MonitoringEvaluationResult:
        try:
            result = await self._service.evaluate(
                position_id=position_id,
                trade_id=trade_id,
                rule=rule,
                observation=observation,
            )
            await self._session.commit()
            return result
        except Exception:
            await self._session.rollback()
            raise
