from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.alert.domain.models import Alert, AlertSeverity, AlertStatus, AlertType
from app.features.alert.persistence.models import AlertModel


class AlertRepository(Protocol):
    async def add(self, alert: Alert) -> None: ...

    async def get(self, alert_id: UUID) -> Alert | None: ...

    async def resolve(self, alert_id: UUID, *, resolved_at: datetime) -> None: ...


class SqlAlchemyAlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, alert: Alert) -> None:
        self._session.add(
            AlertModel(
                id=alert.id,
                position_id=alert.position_id,
                trade_id=alert.trade_id,
                alert_type=alert.alert_type.value,
                severity=alert.severity.value,
                rule_key=alert.rule_key,
                reason=alert.reason,
                observed_value=alert.observed_value,
                threshold_value=alert.threshold_value,
                market_data_observed_at=alert.market_data_observed_at,
                detected_at=alert.detected_at,
                status=alert.status.value,
                resolved_at=alert.resolved_at,
            )
        )

    async def get(self, alert_id: UUID) -> Alert | None:
        model = await self._session.scalar(select(AlertModel).where(AlertModel.id == alert_id))
        return None if model is None else self._to_domain(model)

    async def resolve(self, alert_id: UUID, *, resolved_at: datetime) -> None:
        model = await self._session.scalar(select(AlertModel).where(AlertModel.id == alert_id))
        if model is None:
            raise LookupError("alert not found")
        model.status = AlertStatus.RESOLVED.value
        model.resolved_at = resolved_at

    @staticmethod
    def _to_domain(model: AlertModel) -> Alert:
        return Alert(
            id=model.id,
            position_id=model.position_id,
            trade_id=model.trade_id,
            alert_type=AlertType(model.alert_type),
            severity=AlertSeverity(model.severity),
            rule_key=model.rule_key,
            reason=model.reason,
            observed_value=model.observed_value,
            threshold_value=model.threshold_value,
            market_data_observed_at=model.market_data_observed_at,
            detected_at=model.detected_at,
            status=AlertStatus(model.status),
            resolved_at=model.resolved_at,
        )
