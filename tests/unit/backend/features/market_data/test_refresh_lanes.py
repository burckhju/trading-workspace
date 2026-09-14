"""Independent lane progress, bounded concurrency, pacing and leader lifecycle."""

import asyncio
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from tests.unit.backend.features.market_data.test_refresh import runtime, session_context

from app.features.market_data.service import refresh as module
from app.features.market_data.service.refresh import MarketDataRefreshRuntime, RefreshLane
from app.features.market_data.service.refresh_catalog import RefreshInstrument
from app.features.market_data.service.refresh_runner import run_refresh_forever


@pytest.mark.asyncio
async def test_all_52_held_underlyings_start_and_refresh_again_while_first_warrant_is_blocked(
    monkeypatch,
):
    value = runtime()
    value.container = replace(value.container, eodhd=object())
    warrants = [RefreshInstrument(uuid4(), f"Warrant {i}", None, held=True) for i in range(52)]
    stocks = [
        RefreshInstrument(uuid4(), f"Stock {i}", None, listing_id=uuid4(), held=True)
        for i in range(52)
    ]
    monkeypatch.setattr(module, "read_catalog", AsyncMock(return_value=(warrants, stocks)))
    quote_started, quote_release, eod_completed = asyncio.Event(), asyncio.Event(), asyncio.Event()
    mappings, imports, calls = [], [], []

    async def quote(item):
        calls.append(item.id)
        quote_started.set()
        await quote_release.wait()
        return {"reason": "QUOTE_OBSERVATIONS_AVAILABLE"}

    async def mapping(item):
        mappings.append(item.id)
        return {"reason": "EXISTING_MAPPING_PRESERVED"}

    async def daily(item):
        imports.append(item.id)
        if item == stocks[-1]:
            eod_completed.set()
        return {"reason": "COMPLETED_EOD_IMPORTED", "execution_usable": False}

    value._warrant, value._configure_underlying, value._underlying = quote, mapping, daily
    try:
        await value.run_once(wait_for_completion=False)
        await asyncio.wait_for(quote_started.wait(), timeout=1)
        await asyncio.wait_for(eod_completed.wait(), timeout=1)
        assert len(mappings) == len(imports) == 52
        assert len(calls) == 1
        status = value.status()
        assert status["pending_jobs"] == 52
        assert status["lanes"]["UNDERLYINGS"]["pending_jobs"] == 0
        assert status["current_jobs"]["WARRANTS"] == f"WARRANT_QUOTES:{warrants[0].id}"
        assert status["current_jobs"]["UNDERLYINGS"] is None
        assert all(
            job["execution_usable"] is False
            for key, job in value.jobs.items()
            if key.startswith("UNDERLYING_EOD:")
        )
        # Polling scans must not create another worker for an already busy lane.
        await value.run_once(wait_for_completion=False)
        await value.run_once(wait_for_completion=False)
        assert len(value._lane_tasks) == 2
        assert len(calls) == 1
        # The fast lane's next due run does not wait for the other lane's full batch.
        value.timer = lambda: 4601
        eod_completed.clear()
        await value.run_once(wait_for_completion=False)
        await asyncio.wait_for(eod_completed.wait(), timeout=1)
        assert len(mappings) == len(imports) == 104
        assert len(calls) == 1
    finally:
        await value.stop()
    assert value.running is False
    assert all(job is None for job in value.status()["current_jobs"].values())


@pytest.mark.asyncio
async def test_warrant_interval_is_not_blocked_by_slow_underlying_import(monkeypatch):
    value = runtime(auto_configure=False)
    warrant = RefreshInstrument(uuid4(), "Held warrant", None, held=True)
    stock = RefreshInstrument(uuid4(), "Held stock", None, held=True)
    monkeypatch.setattr(module, "read_catalog", AsyncMock(return_value=([warrant], [stock])))
    imported, release, quoted = asyncio.Event(), asyncio.Event(), asyncio.Event()
    calls = []

    async def daily(_):
        imported.set()
        await release.wait()
        return {"reason": "EOD"}

    async def quote(_):
        calls.append(value.timer())
        quoted.set()
        return {"reason": "QUOTE"}

    value._underlying, value._warrant = daily, quote
    try:
        await value.run_once(wait_for_completion=False)
        await asyncio.wait_for(imported.wait(), timeout=1)
        await asyncio.wait_for(quoted.wait(), timeout=1)
        value.timer = lambda: 1301
        quoted.clear()
        await value.run_once(wait_for_completion=False)
        await asyncio.wait_for(quoted.wait(), timeout=1)
        assert calls == [1000, 1301]
        assert value.status()["current_jobs"]["UNDERLYINGS"].startswith("UNDERLYING_EOD:")
    finally:
        await value.stop()


@pytest.mark.asyncio
async def test_frankfurt_cooldown_and_request_slots_do_not_delay_eodhd(monkeypatch):
    value = runtime()
    value.container = SimpleNamespace(
        frankfurt=SimpleNamespace(
            settings=SimpleNamespace(refresh_interval_seconds=15),
            snapshots=SimpleNamespace(request_delay_seconds=lambda: 900),
        )
    )
    sleeper = AsyncMock()
    monkeypatch.setattr(module.asyncio, "sleep", sleeper)
    await MarketDataRefreshRuntime._pace_underlying(value)
    sleeper.assert_not_awaited()
    await MarketDataRefreshRuntime._pace(value)
    sleeper.assert_awaited_once_with(900)
    await MarketDataRefreshRuntime._pace_underlying(value)
    assert [call.args[0] for call in sleeper.await_args_list] == [900, 15]
    assert value._next_underlying_request == value._next_request == 1015


@pytest.mark.asyncio
async def test_both_current_jobs_remain_visible_when_one_lane_finishes(monkeypatch):
    value = runtime(auto_configure=False)
    items = [RefreshInstrument(uuid4(), "Warrant", None), RefreshInstrument(uuid4(), "Stock", None)]
    monkeypatch.setattr(module, "read_catalog", AsyncMock(return_value=([items[0]], [items[1]])))
    starts = [asyncio.Event(), asyncio.Event()]
    releases = [asyncio.Event(), asyncio.Event()]

    async def operation(index, _):
        starts[index].set()
        await releases[index].wait()
        return {"reason": "OK"}

    value._warrant = lambda item: operation(0, item)
    value._underlying = lambda item: operation(1, item)
    try:
        await value.run_once(wait_for_completion=False)
        await asyncio.wait_for(asyncio.gather(*(start.wait() for start in starts)), timeout=1)
        assert len([key for key in value.status()["current_jobs"].values() if key]) == 2
        releases[0].set()
        await value._lane_tasks[RefreshLane.WARRANTS]
        assert value.running is True
        assert value.current_job.startswith("UNDERLYING_EOD:")
        assert value.status()["current_jobs"]["WARRANTS"] is None
    finally:
        await value.stop()


@pytest.mark.asyncio
async def test_rescan_removes_inflight_and_queued_retired_jobs_without_resurrection(monkeypatch):
    value = runtime(auto_configure=False)
    items = [RefreshInstrument(uuid4(), "First", None), RefreshInstrument(uuid4(), "Queued", None)]
    catalog = AsyncMock(return_value=(items, []))
    monkeypatch.setattr(module, "read_catalog", catalog)
    started, release = asyncio.Event(), asyncio.Event()
    calls = []

    async def quote(item):
        calls.append(item.id)
        started.set()
        await release.wait()
        return {"reason": "OK"}

    value._warrant = quote
    try:
        await value.run_once(wait_for_completion=False)
        await asyncio.wait_for(started.wait(), timeout=1)
        catalog.return_value = ([], [])
        await value.run_once(wait_for_completion=False)
        release.set()
        await value._lane_tasks[RefreshLane.WARRANTS]
        assert calls == [items[0].id]
        assert value.jobs == value._due == {}
    finally:
        await value.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["disabled", "cancelled", "catalog_error"])
async def test_dispatch_failure_or_disable_joins_existing_workers(monkeypatch, failure):
    value = runtime(auto_configure=False)
    item = RefreshInstrument(uuid4(), "Held", None)
    catalog = AsyncMock(return_value=([item], []))
    monkeypatch.setattr(module, "read_catalog", catalog)
    started, stopped = asyncio.Event(), asyncio.Event()

    async def quote(_):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()

    value._warrant = quote
    await value.run_once(wait_for_completion=False)
    await asyncio.wait_for(started.wait(), timeout=1)
    if failure == "disabled":
        value.settings.enabled = False
    elif failure == "cancelled":
        catalog.side_effect = asyncio.CancelledError
    else:
        catalog.side_effect = RuntimeError("private URL")
    try:
        if failure == "cancelled":
            with pytest.raises(asyncio.CancelledError):
                await value.run_once(wait_for_completion=False)
        else:
            await value.run_once(wait_for_completion=False)
        assert stopped.is_set() and not value.running
        assert value._lane_tasks == {}
        if failure == "catalog_error":
            assert value.last_error == "RuntimeError"
    finally:
        await value.stop()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["shutdown", "heartbeat"])
async def test_leader_stops_both_workers_before_unlock_and_probes_during_active_jobs(
    monkeypatch, failure
):
    value = runtime(auto_configure=False)
    item = RefreshInstrument(uuid4(), "Held", None)
    monkeypatch.setattr(module, "read_catalog", AsyncMock(return_value=([item], [item])))
    started = {lane: asyncio.Event() for lane in RefreshLane}
    stopped = {lane: asyncio.Event() for lane in RefreshLane}
    unlocked = asyncio.Event()
    probes = []

    async def work(lane, _):
        started[lane].set()
        try:
            await asyncio.Event().wait()
        finally:
            stopped[lane].set()

    value._warrant = lambda item: work(RefreshLane.WARRANTS, item)
    value._underlying = lambda item: work(RefreshLane.UNDERLYINGS, item)

    async def execute(query, *args):
        if str(query) == "SELECT 1":
            probes.append(query)
            if failure == "heartbeat" and len(probes) == 2:
                raise RuntimeError("private DB URL")
        if "pg_advisory_unlock" in str(query):
            assert all(event.is_set() for event in stopped.values())
            assert value._lane_tasks == {}
            unlocked.set()

    connection = SimpleNamespace(
        scalar=AsyncMock(return_value=True), execute=execute, commit=AsyncMock()
    )
    value.container = SimpleNamespace(
        frankfurt=None,
        vontobel=None,
        eodhd=None,
        database=SimpleNamespace(
            engine=SimpleNamespace(connect=lambda: session_context(connection))
        ),
    )
    task = asyncio.create_task(run_refresh_forever(value))
    try:
        await asyncio.wait_for(asyncio.gather(*(e.wait() for e in started.values())), timeout=1)
        assert value.leader is True
        if failure == "heartbeat":
            value.wake.set()
            await asyncio.wait_for(unlocked.wait(), timeout=1)
            assert value.last_error == "RuntimeError"
            assert len(probes) == 2
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert unlocked.is_set()
        assert value.leader is False and value.running is False
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await value.stop()


@pytest.mark.asyncio
async def test_unexpected_lane_failure_is_observed_without_stopping_other_lane(monkeypatch):
    value = runtime(auto_configure=False)
    item = RefreshInstrument(uuid4(), "Held", None)
    monkeypatch.setattr(module, "read_catalog", AsyncMock(return_value=([item], [item])))
    real_job = value._job

    async def job(key, *args, **kwargs):
        if key.startswith("WARRANT_QUOTES:"):
            raise RuntimeError("private URL")
        await real_job(key, *args, **kwargs)

    value._job = job
    value._underlying = AsyncMock(return_value={"reason": "OK"})
    await value.run_once()
    assert value.status()["last_error"] == "RuntimeError"
    assert value.status()["lanes"]["WARRANTS"]["last_error"] == "RuntimeError"
    assert value.status()["lanes"]["UNDERLYINGS"]["pending_jobs"] == 0
    value._job = real_job
    value._warrant = AsyncMock(return_value={"reason": "OK"})
    await value.run_once()
    assert value.status()["last_error"] is None
