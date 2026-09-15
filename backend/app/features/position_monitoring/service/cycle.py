from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.features.alert.domain.models import Alert
from app.features.market_data.service.contracts import LatestCompletedDailyPriceProvider
from app.features.position_monitoring.domain.models import (
    MonitoringRule,
    PriceObservation,
)
from app.features.position_monitoring.domain.transitions import TriggerTransition
from app.features.position_monitoring.service.application import MonitoringEvaluationResult
from app.features.position_monitoring.service.rule_prices import (
    CycleProductValuations,
    ProductValuationReader,
    rule_price,
)
from app.features.position_monitoring.service.subjects import MonitoringSubjectResolution


class MonitoringSubjectSource(Protocol):
    async def list_resolutions(self) -> tuple[MonitoringSubjectResolution, ...]: ...


class MonitoringRuleProcessor(Protocol):
    async def process(
        self,
        *,
        position_id: UUID,
        trade_id: UUID,
        rule: MonitoringRule,
        observation: PriceObservation,
    ) -> MonitoringEvaluationResult: ...


@dataclass(frozen=True, slots=True)
class CreatedPositionAlert:
    alert: Alert
    symbol: str
    warrant_name: str | None = None
    warrant_isin: str | None = None
    warrant_wkn: str | None = None


@dataclass(frozen=True, slots=True)
class MonitoringCycleResult:
    positions_seen: int
    positions_checked: int
    rules_evaluated: int
    alerts_created: int
    alerts_deduplicated: int
    alerts_resolved: int
    subject_errors: int
    missing_market_data: int
    stale_market_data: int
    market_data_errors: int
    position_errors: int
    alerts: tuple[Alert, ...]
    created_alerts: tuple[CreatedPositionAlert, ...]
    blocked_rules: int = 0
    rule_checks: tuple[dict[str, str | None], ...] = ()


class PositionMonitoringCycleService:
    """Run one isolated monitoring cycle independently from its scheduler."""

    def __init__(
        self,
        *,
        subjects: MonitoringSubjectSource,
        market_data: LatestCompletedDailyPriceProvider | None,
        products: ProductValuationReader | None = None,
        processor: MonitoringRuleProcessor,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        new_id: Callable[[], UUID],
        max_completed_price_age_days: int = 4,
    ) -> None:
        if max_completed_price_age_days < 0:
            raise ValueError("max_completed_price_age_days must not be negative")
        self._subjects = subjects
        self._market_data = market_data
        self._products = products
        self._processor = processor
        self._now = now
        self._new_id = new_id
        self._max_age_days = max_completed_price_age_days

    async def run(self) -> MonitoringCycleResult:
        resolutions = await self._subjects.list_resolutions()
        checked = rules_evaluated = alerts_created = deduplicated = resolved = 0
        subject_errors = missing = stale = data_errors = position_errors = 0
        alerts: list[Alert] = []
        created_alerts: list[CreatedPositionAlert] = []
        now = self._now()

        checks: list[dict[str, str | None]] = []
        blocked = 0
        products = CycleProductValuations(self._products) if self._products else None
        for resolution in resolutions:
            subject = resolution.subject
            if subject is None:
                subject_errors += 1
                continue
            position_checked = False
            for rule in subject.rules:
                check: dict[str, str | None] = {
                    "trade_id": str(subject.trade_id),
                    "rule_key": rule.rule_key,
                    "threshold": str(rule.threshold),
                    **(rule.price_binding.as_dict() if rule.price_binding else {}),
                }
                try:
                    result = await rule_price(
                        subject=subject,
                        rule=rule,
                        market_data=self._market_data,
                        products=products,
                        now=now,
                        max_age_days=self._max_age_days,
                    )
                except Exception:
                    data_errors += 1
                    checks.append(
                        {**check, "status": "ERROR", "reason": "RULE_PRICE_REQUEST_FAILED"}
                    )
                    continue
                checks.append({**check, "status": result.status, "reason": result.reason})
                if result.observation is None:
                    if result.status == "BLOCKED":
                        blocked += 1
                    elif result.status == "MISSING":
                        missing += 1
                    elif result.status == "STALE":
                        stale += 1
                    else:
                        data_errors += 1
                    continue
                observation = result.observation
                checks[-1].update(observation.context or {})
                checks[-1]["observed_value"] = str(observation.value)
                try:
                    evaluation = await self._processor.process(
                        position_id=subject.position_id,
                        trade_id=subject.trade_id,
                        rule=rule,
                        observation=observation,
                    )
                except Exception:
                    position_errors += 1
                    checks[-1].update(status="ERROR", reason="RULE_EVALUATION_FAILED")
                    continue
                position_checked = True
                rules_evaluated += 1
                if evaluation.alert is not None:
                    alerts_created += 1
                    alerts.append(evaluation.alert)
                    created_alerts.append(
                        CreatedPositionAlert(
                            evaluation.alert,
                            (
                                subject.warrant_isin or subject.symbol
                                if rule.price_binding
                                and rule.price_binding.basis.value == "WARRANT"
                                else subject.symbol
                            ),
                            warrant_name=subject.warrant_name,
                            warrant_isin=subject.warrant_isin,
                            warrant_wkn=subject.warrant_wkn,
                        )
                    )
                if evaluation.transition is TriggerTransition.STAYED_TRIGGERED:
                    deduplicated += 1
                elif evaluation.transition is TriggerTransition.EXITED:
                    resolved += 1
            if position_checked:
                checked += 1

        return MonitoringCycleResult(
            positions_seen=len(resolutions),
            positions_checked=checked,
            rules_evaluated=rules_evaluated,
            alerts_created=alerts_created,
            alerts_deduplicated=deduplicated,
            alerts_resolved=resolved,
            subject_errors=subject_errors,
            missing_market_data=missing,
            stale_market_data=stale,
            market_data_errors=data_errors,
            position_errors=position_errors,
            alerts=tuple(alerts),
            created_alerts=tuple(created_alerts),
            blocked_rules=blocked,
            rule_checks=tuple(checks),
        )
