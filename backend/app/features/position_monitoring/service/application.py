from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from app.features.alert.domain.models import Alert, AlertSeverity, AlertType
from app.features.alert.persistence.repositories import AlertRepository
from app.features.position_monitoring.domain.evaluator import PositionRuleEvaluator
from app.features.position_monitoring.domain.models import (
    MonitoringRule,
    MonitoringRuleState,
    MonitoringRuleType,
    PriceObservation,
)
from app.features.position_monitoring.domain.transitions import decide_transition
from app.features.position_monitoring.persistence.repositories import MonitoringRuleStateRepository


class PositionMonitoringService:
    """Trigger-independent deterministic monitoring application service."""

    def __init__(
        self,
        *,
        states: MonitoringRuleStateRepository,
        alerts: AlertRepository,
        new_id: Callable[[], UUID],
        now: Callable[[], datetime],
    ) -> None:
        self._states = states
        self._alerts = alerts
        self._new_id = new_id
        self._now = now

    async def evaluate(
        self,
        *,
        position_id: UUID,
        trade_id: UUID,
        rule: MonitoringRule,
        observation: PriceObservation,
    ) -> Alert | None:
        current = await self._states.get(position_id=position_id, rule_key=rule.rule_key)
        evaluation = PositionRuleEvaluator.evaluate(rule=rule, observation=observation)
        decision = decide_transition(current=current, evaluation=evaluation)
        detected_at = self._now()
        alert: Alert | None = None
        active_alert_id = current.active_alert_id if current is not None else None

        if decision.create_alert:
            alert_type = (
                AlertType.STOP_REACHED
                if rule.rule_type is MonitoringRuleType.STOP_REACHED
                else AlertType.TARGET_REACHED
            )
            alert = Alert(
                id=self._new_id(),
                position_id=position_id,
                trade_id=trade_id,
                alert_type=alert_type,
                severity=(
                    AlertSeverity.WARNING
                    if alert_type is AlertType.STOP_REACHED
                    else AlertSeverity.INFO
                ),
                rule_key=rule.rule_key,
                reason=evaluation.reason,
                observed_value=observation.value,
                threshold_value=rule.threshold,
                market_data_observed_at=observation.observed_at,
                detected_at=detected_at,
            )
            await self._alerts.add(alert)
            active_alert_id = alert.id
        elif decision.resolve_alert and active_alert_id is not None:
            await self._alerts.resolve(active_alert_id, resolved_at=detected_at)
            active_alert_id = None

        first_seen_at = None
        if evaluation.triggered:
            first_seen_at = (
                current.first_seen_at
                if current is not None and current.triggered
                else observation.observed_at
            )

        await self._states.put(
            MonitoringRuleState(
                position_id=position_id,
                rule_key=rule.rule_key,
                triggered=evaluation.triggered,
                first_seen_at=first_seen_at,
                last_seen_at=observation.observed_at,
                last_observed_value=observation.value,
                threshold_value=rule.threshold,
                active_alert_id=active_alert_id,
            )
        )
        return alert
