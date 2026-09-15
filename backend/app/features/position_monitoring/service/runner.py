from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

from app.features.position_monitoring.service.runtime import PositionMonitoringRuntimeResult

logger = logging.getLogger(__name__)


class PositionMonitoringRuntime(Protocol):
    async def run(self) -> PositionMonitoringRuntimeResult: ...


class PositionMonitoringRunner:
    """Thin scheduler for repeated monitoring; business logic stays in runtime services."""

    def __init__(
        self,
        *,
        runtime: PositionMonitoringRuntime,
        interval_seconds: float,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self._runtime = runtime
        self._interval_seconds = interval_seconds
        self._stop = asyncio.Event()
        self._now = now
        self.running = False
        self.cycle_running = False
        self.last_cycle_started_at: datetime | None = None
        self.last_cycle_completed_at: datetime | None = None
        self.next_run_at: datetime | None = None
        self.last_error: str | None = None
        self.last_error_at: datetime | None = None
        self.last_result: dict[str, int] | None = None
        self.last_rule_checks: tuple[dict[str, str | None], ...] = ()

    def status(self) -> dict[str, Any]:
        return {
            "running": self.running,
            "cycle_running": self.cycle_running,
            "last_cycle_started_at": self.last_cycle_started_at,
            "last_cycle_completed_at": self.last_cycle_completed_at,
            "next_run_at": self.next_run_at,
            "last_error": self.last_error,
            "last_error_at": self.last_error_at,
            "last_result": self.last_result,
            "last_rule_checks": self.last_rule_checks,
        }

    async def run_forever(self) -> None:
        self.running = True
        try:
            await self._run_cycles()
        finally:
            self.running = self.cycle_running = False
            self.next_run_at = None

    async def _run_cycles(self) -> None:
        while not self._stop.is_set():
            self.cycle_running = True
            self.last_cycle_started_at = self._now()
            self.next_run_at = None
            try:
                result = await self._runtime.run()
                self.last_cycle_completed_at = self._now()
                self.last_error = None
                self.last_result = {
                    name: getattr(result.cycle, name)
                    for name in (
                        "positions_seen",
                        "positions_checked",
                        "rules_evaluated",
                        "blocked_rules",
                        "alerts_created",
                        "alerts_deduplicated",
                        "alerts_resolved",
                        "subject_errors",
                        "missing_market_data",
                        "stale_market_data",
                        "market_data_errors",
                        "position_errors",
                    )
                }
                self.last_rule_checks = result.cycle.rule_checks
                self.last_result.update(
                    alerts_invalidated=result.alerts_invalidated,
                    notifications_created=result.notifications_created,
                    notifications_delivered=result.notifications_delivered,
                    notification_failures=result.notification_failures,
                )
                logger.info(
                    "position_monitoring_cycle_completed",
                    extra={
                        "positions_seen": result.cycle.positions_seen,
                        "positions_checked": result.cycle.positions_checked,
                        "alerts_created": result.cycle.alerts_created,
                        "alerts_deduplicated": result.cycle.alerts_deduplicated,
                        "alerts_resolved": result.cycle.alerts_resolved,
                        "notifications_created": result.notifications_created,
                        "notifications_delivered": result.notifications_delivered,
                        "notification_failures": result.notification_failures,
                        "market_data_errors": result.cycle.market_data_errors,
                        "position_errors": result.cycle.position_errors,
                    },
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                self.last_error = "MONITORING_CYCLE_FAILED"
                self.last_error_at = self._now()
                logger.exception("position_monitoring_cycle_failed")
            finally:
                self.cycle_running = False

            self.next_run_at = self._now() + timedelta(seconds=self._interval_seconds)
            with suppress(TimeoutError):
                await asyncio.wait_for(self._stop.wait(), timeout=self._interval_seconds)

    def stop(self) -> None:
        self._stop.set()
