from __future__ import annotations

from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.position_monitoring.domain.models import MonitoringRuleState
from app.features.position_monitoring.persistence.models import MonitoringRuleStateModel


class MonitoringRuleStateRepository(Protocol):
    async def get(self, *, position_id: UUID, rule_key: str) -> MonitoringRuleState | None: ...

    async def put(self, state: MonitoringRuleState) -> None: ...


class SqlAlchemyMonitoringRuleStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, *, position_id: UUID, rule_key: str) -> MonitoringRuleState | None:
        model = await self._session.scalar(
            select(MonitoringRuleStateModel).where(
                MonitoringRuleStateModel.position_id == position_id,
                MonitoringRuleStateModel.rule_key == rule_key,
            )
        )
        if model is None:
            return None
        return MonitoringRuleState(
            position_id=model.position_id,
            rule_key=model.rule_key,
            triggered=model.triggered,
            first_seen_at=model.first_seen_at,
            last_seen_at=model.last_seen_at,
            last_observed_value=model.last_observed_value,
            threshold_value=model.threshold_value,
            active_alert_id=model.active_alert_id,
        )

    async def put(self, state: MonitoringRuleState) -> None:
        model = await self._session.scalar(
            select(MonitoringRuleStateModel).where(
                MonitoringRuleStateModel.position_id == state.position_id,
                MonitoringRuleStateModel.rule_key == state.rule_key,
            )
        )
        if model is None:
            self._session.add(
                MonitoringRuleStateModel(
                    id=uuid4(),
                    position_id=state.position_id,
                    rule_key=state.rule_key,
                    triggered=state.triggered,
                    first_seen_at=state.first_seen_at,
                    last_seen_at=state.last_seen_at,
                    last_observed_value=state.last_observed_value,
                    threshold_value=state.threshold_value,
                    active_alert_id=state.active_alert_id,
                )
            )
            return
        model.triggered = state.triggered
        model.first_seen_at = state.first_seen_at
        model.last_seen_at = state.last_seen_at
        model.last_observed_value = state.last_observed_value
        model.threshold_value = state.threshold_value
        model.active_alert_id = state.active_alert_id
