from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.features.alert.domain.models import Alert
from app.features.market_data.domain.enums import QualityStatus
from app.features.market_data.service.contracts import LatestCompletedDailyPriceProvider
from app.features.market_data.service.types import LatestDailyPriceRequest
from app.features.position_monitoring.domain.models import (
    MonitoringRule,
    MonitoringRuleType,
    PriceObservation,
)
from app.features.position_monitoring.domain.transitions import TriggerTransition
from app.features.position_monitoring.service.application import MonitoringEvaluationResult
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


class PositionMonitoringCycleService:
    """Run one isolated monitoring cycle independently from its scheduler."""

    def __init__(
        self,
        *,
        subjects: MonitoringSubjectSource,
        market_data: LatestCompletedDailyPriceProvider,
        processor: MonitoringRuleProcessor,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        new_id: Callable[[], UUID],
        max_completed_price_age_days: int = 4,
    ) -> None:
        if max_completed_price_age_days < 0:
            raise ValueError("max_completed_price_age_days must not be negative")
        self._subjects = subjects
        self._market_data = market_data
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

        for resolution in resolutions:
            subject = resolution.subject
            if subject is None:
                subject_errors += 1
                continue
            try:
                result = await self._market_data.get_latest_completed_daily_price(
                    LatestDailyPriceRequest(
                        workspace_id=subject.workspace_id,
                        listing_id=subject.listing_id,
                        mapping_id=subject.mapping_id,
                        correlation_id=self._new_id(),
                        as_of_date=now.date(),
                    )
                )
            except Exception:
                data_errors += 1
                continue
            price = result.data
            if price is None:
                missing += 1
                continue
            if result.quality_status is not QualityStatus.VALID:
                data_errors += 1
                continue
            if (now.date() - price.trading_date).days > self._max_age_days:
                stale += 1
                continue

            checked += 1
            try:
                for rule in subject.rules:
                    value = (
                        price.low
                        if rule.rule_type is MonitoringRuleType.STOP_REACHED
                        else price.high
                    )
                    evaluation = await self._processor.process(
                        position_id=subject.position_id,
                        trade_id=subject.trade_id,
                        rule=rule,
                        observation=PriceObservation(
                            value=value,
                            observed_at=price.source_updated_at or price.retrieved_at,
                        ),
                    )
                    rules_evaluated += 1
                    if evaluation.alert is not None:
                        alerts_created += 1
                        alerts.append(evaluation.alert)
                        created_alerts.append(
                            CreatedPositionAlert(
                                alert=evaluation.alert,
                                symbol=subject.symbol,
                            )
                        )
                    if evaluation.transition is TriggerTransition.STAYED_TRIGGERED:
                        deduplicated += 1
                    elif evaluation.transition is TriggerTransition.EXITED:
                        resolved += 1
            except Exception:
                position_errors += 1
                continue

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
        )
