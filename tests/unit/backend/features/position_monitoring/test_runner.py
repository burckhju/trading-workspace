import asyncio
from dataclasses import replace
from datetime import UTC, datetime

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
    snapshot = runner.status()
    assert snapshot["running"] is False and snapshot["cycle_running"] is False
    assert snapshot["last_result"]["positions_seen"] == 0
    assert snapshot["last_cycle_completed_at"] is not None
    assert snapshot["next_run_at"] is None


@pytest.mark.asyncio
async def test_status_distinguishes_in_progress_partial_result_and_failure():
    entered, release = asyncio.Event(), asyncio.Event()
    now = datetime(2026, 9, 14, 13, 0, tzinfo=UTC)
    good = await Runtime().run()

    class ControlledRuntime:
        calls = 0

        async def run(self):
            self.calls += 1
            entered.set()
            await release.wait()
            entered.clear()
            release.clear()
            if self.calls == 2:
                raise RuntimeError("secret URL/token must not enter status")
            return replace(
                good,
                cycle=replace(
                    good.cycle,
                    positions_seen=52,
                    positions_checked=50,
                    subject_errors=2,
                    rules_evaluated=100,
                ),
            )

    runtime = ControlledRuntime()
    runner = PositionMonitoringRunner(runtime=runtime, interval_seconds=0.01, now=lambda: now)
    assert runner.status()["last_result"] is None
    task = asyncio.create_task(runner.run_forever())
    try:
        await asyncio.wait_for(entered.wait(), 1)
        assert runner.status()["running"] and runner.status()["cycle_running"]
        assert runner.status()["last_cycle_completed_at"] is None
        release.set()
        await asyncio.sleep(0)
        assert runner.status()["last_result"]["positions_checked"] == 50
        assert runner.status()["last_result"]["subject_errors"] == 2
        assert runner.status()["next_run_at"] > now
        await asyncio.wait_for(entered.wait(), 1)
        release.set()
        await asyncio.sleep(0)
        snapshot = runner.status()
        assert snapshot["last_error"] == "MONITORING_CYCLE_FAILED"
        assert snapshot["last_error_at"] == now
        assert "secret" not in str(snapshot)
        assert snapshot["last_result"]["positions_checked"] == 50
        await asyncio.wait_for(entered.wait(), 1)
        release.set()
        await asyncio.sleep(0)
        assert runner.status()["last_error"] is None
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert not runner.status()["running"]
    assert not runner.status()["cycle_running"]
