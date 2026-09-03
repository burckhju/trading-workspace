import asyncio

import pytest

from app.features.position_monitoring.service.cycle import MonitoringCycleResult
from app.features.position_monitoring.service.runner import PositionMonitoringRunner
from app.features.position_monitoring.service.runtime import PositionMonitoringRuntimeResult


class Runtime:
    def __init__(self) -> None:
        self.called = asyncio.Event()
        self.calls = 0

    async def run(self) -> PositionMonitoringRuntimeResult:
        self.calls += 1
        self.called.set()
        return PositionMonitoringRuntimeResult(
            cycle=MonitoringCycleResult(
                positions_seen=0,
                positions_checked=0,
                rules_evaluated=0,
                alerts_created=0,
                alerts_deduplicated=0,
                alerts_resolved=0,
                subject_errors=0,
                missing_market_data=0,
                stale_market_data=0,
                market_data_errors=0,
                position_errors=0,
                alerts=(),
                created_alerts=(),
            ),
            notifications_created=0,
            notifications_delivered=0,
            notification_failures=0,
        )


@pytest.mark.asyncio
async def test_runner_stops_without_waiting_for_next_interval() -> None:
    runtime = Runtime()
    runner = PositionMonitoringRunner(runtime=runtime, interval_seconds=3600)
    task = asyncio.create_task(runner.run_forever())

    await asyncio.wait_for(runtime.called.wait(), timeout=1)
    runner.stop()
    await asyncio.wait_for(task, timeout=1)

    assert runtime.calls == 1
