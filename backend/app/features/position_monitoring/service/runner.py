from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import Protocol

from app.features.position_monitoring.service.runtime import PositionMonitoringRuntimeResult

logger = logging.getLogger(__name__)


class PositionMonitoringRuntime(Protocol):
    async def run(self) -> PositionMonitoringRuntimeResult: ...


class PositionMonitoringRunner:
    """Thin scheduler for repeated monitoring; business logic stays in runtime services."""

    def __init__(self, *, runtime: PositionMonitoringRuntime, interval_seconds: float) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self._runtime = runtime
        self._interval_seconds = interval_seconds
        self._stop = asyncio.Event()

    async def run_forever(self) -> None:
        while not self._stop.is_set():
            try:
                result = await self._runtime.run()
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
                logger.exception("position_monitoring_cycle_failed")

            with suppress(TimeoutError):
                await asyncio.wait_for(self._stop.wait(), timeout=self._interval_seconds)

    def stop(self) -> None:
        self._stop.set()
