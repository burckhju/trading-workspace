from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.features.alert.domain.models import Alert, AlertStatus
from app.features.position_monitoring.domain.models import (
    MonitoringRule,
    MonitoringRuleState,
    MonitoringRuleType,
    PriceObservation,
)
from app.features.position_monitoring.service.application import PositionMonitoringService


class StateRepo:
    def __init__(self) -> None:
        self.values: dict[tuple[UUID, str], MonitoringRuleState] = {}

    async def get(self, *, position_id: UUID, rule_key: str) -> MonitoringRuleState | None:
        return self.values.get((position_id, rule_key))

    async def put(self, state: MonitoringRuleState) -> None:
        self.values[(state.position_id, state.rule_key)] = state


class AlertRepo:
    def __init__(self) -> None:
        self.values: dict[UUID, Alert] = {}

    async def add(self, alert: Alert) -> None:
        self.values[alert.id] = alert

    async def get(self, alert_id: UUID) -> Alert | None:
        return self.values.get(alert_id)

    async def resolve(self, alert_id: UUID, *, resolved_at: datetime) -> None:
        alert = self.values[alert_id]
        self.values[alert_id] = Alert(
            id=alert.id,
            position_id=alert.position_id,
            trade_id=alert.trade_id,
            alert_type=alert.alert_type,
            severity=alert.severity,
            rule_key=alert.rule_key,
            reason=alert.reason,
            observed_value=alert.observed_value,
            threshold_value=alert.threshold_value,
            market_data_observed_at=alert.market_data_observed_at,
            detected_at=alert.detected_at,
            status=AlertStatus.RESOLVED,
            resolved_at=resolved_at,
        )


@pytest.mark.asyncio
async def test_trigger_is_edge_deduplicated_and_can_retrigger_after_reset() -> None:
    states = StateRepo()
    alerts = AlertRepo()
    now = datetime(2026, 9, 3, 10, tzinfo=UTC)
    service = PositionMonitoringService(states=states, alerts=alerts, new_id=uuid4, now=lambda: now)
    position_id, trade_id = uuid4(), uuid4()
    rule = MonitoringRule("target", MonitoringRuleType.TARGET_REACHED, Decimal("120"))

    first = await service.evaluate(
        position_id=position_id,
        trade_id=trade_id,
        rule=rule,
        observation=PriceObservation(Decimal("121"), now),
    )
    repeated = await service.evaluate(
        position_id=position_id,
        trade_id=trade_id,
        rule=rule,
        observation=PriceObservation(Decimal("122"), now + timedelta(minutes=1)),
    )
    assert first.alert is not None
    assert repeated.alert is None
    assert len(alerts.values) == 1

    await service.evaluate(
        position_id=position_id,
        trade_id=trade_id,
        rule=rule,
        observation=PriceObservation(Decimal("119"), now + timedelta(minutes=2)),
    )
    assert alerts.values[first.alert.id].status is AlertStatus.RESOLVED

    retriggered = await service.evaluate(
        position_id=position_id,
        trade_id=trade_id,
        rule=rule,
        observation=PriceObservation(Decimal("120"), now + timedelta(minutes=3)),
    )
    assert retriggered.alert is not None
    assert retriggered.alert.id != first.alert.id
    assert len(alerts.values) == 2


@pytest.mark.asyncio
async def test_threshold_change_is_a_new_rule_state_transition() -> None:
    states = StateRepo()
    alerts = AlertRepo()
    now = datetime(2026, 9, 3, 10, tzinfo=UTC)
    service = PositionMonitoringService(states=states, alerts=alerts, new_id=uuid4, now=lambda: now)
    position_id, trade_id = uuid4(), uuid4()

    first = await service.evaluate(
        position_id=position_id,
        trade_id=trade_id,
        rule=MonitoringRule("stop", MonitoringRuleType.STOP_REACHED, Decimal("100")),
        observation=PriceObservation(Decimal("99"), now),
    )
    changed = await service.evaluate(
        position_id=position_id,
        trade_id=trade_id,
        rule=MonitoringRule("stop", MonitoringRuleType.STOP_REACHED, Decimal("101")),
        observation=PriceObservation(Decimal("99"), now + timedelta(minutes=1)),
    )

    assert first.alert is not None
    assert changed.alert is not None
    assert changed.alert.id != first.alert.id
    assert alerts.values[first.alert.id].status is AlertStatus.RESOLVED
