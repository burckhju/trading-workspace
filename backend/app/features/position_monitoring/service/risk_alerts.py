"""Reuse persistent alert edges. Inputs are qualified signals, never fake prices."""

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.alert.domain.models import Alert, AlertSeverity, AlertStatus, AlertType
from app.features.alert.persistence.repositories import SqlAlchemyAlertRepository
from app.features.alert.service.risk_lifecycle import invalidate_risk_alerts
from app.features.position_monitoring.domain.models import MonitoringRuleState, RuleEvaluation
from app.features.position_monitoring.domain.transitions import decide_transition
from app.features.position_monitoring.persistence.repositories import (
    SqlAlchemyMonitoringRuleStateRepository,
)
from app.features.position_monitoring.service.cycle import CreatedPositionAlert
from app.features.position_monitoring.service.risk_contracts import PositionRiskView


class RiskAlertService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._states = SqlAlchemyMonitoringRuleStateRepository(session)
        self._alerts = SqlAlchemyAlertRepository(session)

    async def process(
        self, view: PositionRiskView, *, evaluate: bool = True
    ) -> tuple[CreatedPositionAlert, ...]:
        if not view.configuration.enabled:
            return ()
        rules = (
            (
                "TREND",
                AlertType.RISK_TREND_CHANGED,
                view.assessment.trend_triggered,
                view.metrics.distance_sma20,
                view.configuration.parameters.hysteresis_fraction,
            ),
            (
                "VOLATILITY",
                AlertType.RISK_VOLATILITY_HIGH,
                view.assessment.volatility_triggered,
                view.metrics.realized_volatility20,
                view.configuration.parameters.volatility_high,
            ),
        )
        prefix = f"POSITION_RISK_V1:{view.configuration.revision}:{view.basis_key[:16]}:"
        if evaluate and view.metrics.status == "AVAILABLE":
            await invalidate_risk_alerts(
                self._session,
                position_id=view.position_id,
                now=view.evaluated_at,
                preserve_keys=tuple(prefix + r[0] for r in rules),
            )
        result: list[CreatedPositionAlert] = []
        for name, alert_type, triggered, value, threshold in rules:
            key = prefix + name
            current = await self._states.get(position_id=view.position_id, rule_key=key)
            active_id = current.active_alert_id if current else None
            if evaluate and triggered is not None and value is not None:
                decision = decide_transition(
                    current=current,
                    evaluation=RuleEvaluation(
                        triggered,
                        view.assessment.reason,
                    ),
                )
                # This is evaluation ordering, not a fabricated EOD quote timestamp.
                now = view.evaluated_at
                if decision.create_alert:
                    alert = Alert(
                        id=uuid4(),
                        position_id=view.position_id,
                        trade_id=view.trade_id,
                        alert_type=alert_type,
                        severity=AlertSeverity.WARNING,
                        rule_key=key,
                        reason=(
                            f"{name}: {view.assessment.interpretation}; "
                            f"{view.assessment.reason}"
                        ),
                        observed_value=value,
                        threshold_value=threshold,
                        market_data_observed_at=None,
                        detected_at=now,
                        price_context={
                            "basis": "UNDERLYING_RISK_SIGNAL",
                            "price_type": "FRACTION",
                            "currency": view.listing.currency if view.listing else None,
                            "trading_date": str(view.metrics.session),
                            "policy_version": view.assessment.policy_version,
                            "input_fingerprint": view.input_fingerprint,
                            "snapshot_id": str(view.snapshot_id),
                            "configuration_revision": str(view.configuration.revision),
                            "direction": view.assessment.direction,
                            "provider": (
                                view.input_prices[-1].provider.value if view.input_prices else None
                            ),
                            "provider_identity": view.listing.symbol if view.listing else None,
                            "quote_time_basis": "COMPLETED_SESSION_DATE_ONLY",
                            "execution_usable": "false",
                            "warning": "DESCRIPTIVE_RISK_NOT_A_SALE_SIGNAL",
                        },
                    )
                    await self._alerts.add(alert)
                    await self._session.flush()
                    active_id = alert.id
                elif decision.resolve_alert and active_id is not None:
                    await self._alerts.resolve(active_id, resolved_at=now)
                    active_id = None
                await self._states.put(
                    MonitoringRuleState(
                        view.position_id,
                        key,
                        triggered,
                        (
                            current.first_seen_at
                            if triggered and current and current.triggered
                            else now if triggered else None
                        ),
                        now,
                        value,
                        threshold,
                        active_id,
                        price_binding_key=None,
                        time_basis="EVALUATION_TIMESTAMP",
                    )
                )
            # Replay the OPEN alert to the existing idempotent outbox creator.
            # A crash after alert commit but before notification creation is recoverable.
            if active_id is not None:
                active_alert = await self._alerts.get(active_id)
                if active_alert is not None and active_alert.status is AlertStatus.OPEN:
                    product = view.product
                    result.append(
                        CreatedPositionAlert(
                            active_alert,
                            view.listing.symbol if view.listing else "",
                            product.name if product else None,
                            product.isin if product else None,
                            product.wkn if product else None,
                        )
                    )
        return tuple(result)
