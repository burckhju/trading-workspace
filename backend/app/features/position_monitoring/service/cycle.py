from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from time import monotonic
from typing import Protocol
from uuid import UUID

from app.features.alert.domain.models import Alert
from app.features.market_data.service.contracts import LatestCompletedDailyPriceProvider
from app.features.position_monitoring.domain.models import (
    MonitoringRule,
    PriceObservation,
)
from app.features.position_monitoring.domain.transitions import TriggerTransition
from app.features.position_monitoring.service.application import (
    MonitoringEvaluationResult,
    OutOfOrderRuleObservation,
)
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
        parallel_positions: int = 1,
    ) -> None:
        if max_completed_price_age_days < 0:
            raise ValueError("max_completed_price_age_days must not be negative")
        if not 1 <= parallel_positions <= 4:
            raise ValueError("parallel_positions must be between 1 and 4")
        self._parallel_positions = parallel_positions
        self._subjects = subjects
        self._market_data = market_data
        self._products = products
        self._processor = processor
        self._now = now
        self._new_id = new_id
        self._max_age_days = max_completed_price_age_days

    async def run(self) -> MonitoringCycleResult:
        resolutions = await self._subjects.list_resolutions()
        # Only quote reads overlap. The processor owns one SQLAlchemy session,
        # so every state/alert transaction must remain serialized.
        processor_lock = asyncio.Lock()
        pending = iter(enumerate(resolutions))
        results: dict[int, MonitoringCycleResult] = {}

        async def worker() -> None:
            for index, resolution in pending:
                results[index] = await self._run_resolutions((resolution,), processor_lock)

        async with asyncio.TaskGroup() as group:
            for _ in range(min(self._parallel_positions, len(resolutions))):
                group.create_task(worker())
        ordered = [results[index] for index in sorted(results)]
        return MonitoringCycleResult(
            positions_seen=sum(result.positions_seen for result in ordered),
            positions_checked=sum(result.positions_checked for result in ordered),
            rules_evaluated=sum(result.rules_evaluated for result in ordered),
            alerts_created=sum(result.alerts_created for result in ordered),
            alerts_deduplicated=sum(result.alerts_deduplicated for result in ordered),
            alerts_resolved=sum(result.alerts_resolved for result in ordered),
            subject_errors=sum(result.subject_errors for result in ordered),
            missing_market_data=sum(result.missing_market_data for result in ordered),
            stale_market_data=sum(result.stale_market_data for result in ordered),
            market_data_errors=sum(result.market_data_errors for result in ordered),
            position_errors=sum(result.position_errors for result in ordered),
            blocked_rules=sum(result.blocked_rules for result in ordered),
            alerts=tuple(item for result in ordered for item in result.alerts),
            created_alerts=tuple(item for result in ordered for item in result.created_alerts),
            rule_checks=tuple(item for result in ordered for item in result.rule_checks),
        )

    async def _run_resolutions(
        self,
        resolutions: tuple[MonitoringSubjectResolution, ...],
        processor_lock: asyncio.Lock,
    ) -> MonitoringCycleResult:
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
                    "position_id": str(subject.position_id),
                    "isin": subject.warrant_isin,
                    "rule_key": rule.rule_key,
                    "threshold": str(rule.threshold),
                    **(rule.price_binding.as_dict() if rule.price_binding else {}),
                }
                price_started = monotonic()
                try:
                    result = await rule_price(
                        subject=subject,
                        rule=rule,
                        market_data=self._market_data,
                        products=products,
                        now=now,
                        max_age_days=self._max_age_days,
                        checked_at=self._now,
                    )
                except Exception as exc:
                    check.update(_error_context(exc))
                    check["price_request_seconds"] = f"{monotonic() - price_started:.3f}"
                    data_errors += 1
                    checks.append(
                        {**check, "status": "ERROR", "reason": "RULE_PRICE_REQUEST_FAILED"}
                    )
                    continue
                check["price_request_seconds"] = f"{monotonic() - price_started:.3f}"
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
                evaluation_started = monotonic()
                try:
                    async with processor_lock:
                        evaluation = await self._processor.process(
                            position_id=subject.position_id,
                            trade_id=subject.trade_id,
                            rule=rule,
                            observation=observation,
                        )
                except OutOfOrderRuleObservation as exc:
                    # Rejection is expected for an older retained quote. Keep the
                    # newer state, and report the exact ordering evidence.
                    stale += 1
                    checks[-1].update(
                        status="STALE",
                        reason="OUT_OF_ORDER_RULE_OBSERVATION",
                        previous_seen_at=exc.previous_seen_at.isoformat(),
                        previous_time_basis=exc.time_basis,
                    )
                    continue
                except Exception as exc:
                    position_errors += 1
                    checks[-1].update(
                        status="ERROR", reason="RULE_EVALUATION_FAILED", **_error_context(exc)
                    )
                    continue
                finally:
                    checks[-1]["evaluation_seconds"] = f"{monotonic() - evaluation_started:.3f}"
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


def _error_context(exc: Exception) -> dict[str, str]:
    # Never publish exception messages, SQL parameters or provider URLs.
    details = {"error_type": type(exc).__name__}
    code = str(exc) if isinstance(exc, ValueError) else ""
    if code in {
        "RULE_OBSERVATION_ORDERING_TIME_UNKNOWN",
        "RULE_OBSERVATION_TIMESTAMP_UNKNOWN",
        "RULE_PRICE_BASIS_UNCONFIRMED",
        "RULE_PRICE_IDENTITY_OR_CURRENCY_MISMATCH",
        "INVALID_OBSERVED_PRICE",
    }:
        details["error_code"] = code
    sqlstate = getattr(getattr(exc, "orig", None), "sqlstate", None)
    if isinstance(sqlstate, str) and re.fullmatch(r"[0-9A-Z]{5}", sqlstate):
        details["sqlstate"] = sqlstate
    return details
