"""Exercise source-specific scheduler pacing through real provider composition.

The runtime builds its real resolver, retained provider, Frankfurt adapter and
client. Only the catalog and test clock are injected; SQL uses disposable SQLite,
HTTP uses MockTransport and files live in tmp_path. This is not a PostgreSQL or
multi-process leader-lock qualification.
"""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.orm import Session
from tests.unit.backend.features.market_data.test_retained_quotes import (
    context as durable_database,  # noqa: F401
)
from tests.unit.backend.providers.frankfurt_quotes.test_client import settings
from tests.unit.backend.providers.frankfurt_quotes.test_public import public_settings, wire
from tests.unit.backend.providers.frankfurt_quotes.test_schema import NOW, payload

from app.core.config import Settings
from app.core.config.frankfurt import FrankfurtSourceMode
from app.core.di import ApplicationContainer
from app.features.market_data.domain.enums import CacheStatus, MappingStatus, MarketDataProvider
from app.features.market_data.persistence.models import WarrantProviderMappingModel
from app.features.market_data.service import refresh as module
from app.features.market_data.service.refresh import MarketDataRefreshRuntime, RefreshLane
from app.features.market_data.service.refresh_catalog import RefreshInstrument
from app.features.product.domain.models import WarrantLifecycle
from app.features.product.persistence.models import WarrantListingModel, WarrantModel
from app.providers.frankfurt_quotes.adapter import FrankfurtWarrantQuoteAdapter
from app.providers.frankfurt_quotes.client import FrankfurtSnapshotClient

FIRST = "DE000VH2LU21"
SECOND = "DE000VH7S657"


class Clock:
    def __init__(self):
        self.value = 100.0
        self.waits = []

    def timer(self):
        return self.value

    def now(self):
        return NOW + timedelta(seconds=self.value - 100)

    async def sleep(self, seconds):
        assert seconds > 0
        self.waits.append(seconds)
        self.value += seconds


def add_second_listing(context, mode):
    """Reuse the existing SQLite fixture, keeping real route/identity SQL."""
    warrant, listing = uuid4(), uuid4()
    common = dict(created_at=NOW, updated_at=NOW, version=1)
    exchange = "XSC" if mode is FrankfurtSourceMode.PUBLIC_WEBSITE else "XFRA"
    with Session(context.database.engine) as session:
        session.get(WarrantProviderMappingModel, context.mapping).provider_exchange_code = exchange
        session.add_all(
            [
                WarrantModel(
                    id=warrant,
                    workspace_id=context.request.workspace_id,
                    issuer_id=uuid4(),
                    underlying_id=uuid4(),
                    display_name="Second synthetic warrant",
                    isin=SECOND,
                    wkn="VH7S65",
                    lifecycle_status=WarrantLifecycle.ACTIVE,
                    **common,
                ),
                WarrantListingModel(
                    id=listing,
                    workspace_id=context.request.workspace_id,
                    warrant_id=warrant,
                    trading_venue_id=context.venue,
                    quotation_currency_code="EUR",
                    lifecycle_status=WarrantLifecycle.ACTIVE,
                    **common,
                ),
                WarrantProviderMappingModel(
                    id=uuid4(),
                    workspace_id=context.request.workspace_id,
                    warrant_listing_id=listing,
                    provider=MarketDataProvider.FRANKFURT_QUOTES,
                    provider_symbol=SECOND,
                    provider_exchange_code=exchange,
                    status=MappingStatus.ACTIVE,
                    validated_at=NOW,
                    **common,
                ),
            ]
        )
        session.commit()
    return (
        RefreshInstrument(context.warrant, "First", FIRST),
        RefreshInstrument(warrant, "Second", SECOND),
    )


@asynccontextmanager
async def source_runtime(context, tmp_path, monkeypatch, mode, *, http_failures=None):
    clock = Clock()
    data = payload()
    data["records"].append({**data["records"][0], "isin": SECOND, "wkn": "VH7S65"})
    path = tmp_path / "synthetic-quotes.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    config = (
        public_settings()
        if mode is FrankfurtSourceMode.PUBLIC_WEBSITE
        else settings(
            source_mode=mode,
            local_file=str(path) if mode is FrankfurtSourceMode.LOCAL_FILE else None,
        )
    )
    calls = []

    def respond(request):
        assert mode is not FrankfurtSourceMode.LOCAL_FILE, "Local files must not use HTTP"
        calls.append((clock.value, request))
        if http_failures and len(calls) in http_failures:
            return http_failures[len(calls)]
        body = (
            wire(isin=request.url.params["isin"])
            if mode is FrankfurtSourceMode.PUBLIC_WEBSITE
            else data
        )
        return httpx.Response(200, json=body)

    async def reject_real_http(*_args, **_kwargs):
        raise AssertionError("Unmocked HTTP transport is forbidden")

    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", reject_real_http)
    monkeypatch.setattr(module.asyncio, "sleep", clock.sleep)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond), trust_env=False) as http:
        client = FrankfurtSnapshotClient(
            config, client=http, timer=clock.timer, clock=clock.now, cache_seconds=300
        )
        file_reads = Mock(wraps=client._read_file)
        monkeypatch.setattr(client, "_read_file", file_reads)
        adapter = FrankfurtWarrantQuoteAdapter(
            database=context.database, settings=config, snapshots=client, clock=clock.now
        )
        container = ApplicationContainer(
            settings=Settings(
                _env_file=None,
                environment="test",
                market_data={
                    "frankfurt": config,
                    "refresh": {
                        "enabled": True,
                        "workspace_id": context.request.workspace_id,
                        "auto_configure": False,
                        "request_spacing_seconds": 15,
                        "warrants_interval_seconds": 300,
                    },
                },
            ),
            database=context.database,
            frankfurt=adapter,
        )
        runtime = MarketDataRefreshRuntime(container, timer=clock.timer)
        # Wrap real calls to count independently from sleep and transport work.
        pace = AsyncMock(wraps=runtime._pace)
        monkeypatch.setattr(runtime, "_pace", pace)
        resolve = runtime._resolver.resolve_selected
        resolutions = []

        async def counted_resolve(provider, request):
            result = await resolve(provider, request)
            resolutions.append((clock.value, provider, result))
            return result

        resolver = AsyncMock(side_effect=counted_resolve)
        monkeypatch.setattr(runtime._resolver, "resolve_selected", resolver)
        items = add_second_listing(context, mode)
        try:
            yield SimpleNamespace(
                runtime=runtime,
                client=client,
                clock=clock,
                calls=calls,
                file_reads=file_reads,
                path=path,
                pace=pace,
                resolver=resolver,
                resolutions=resolutions,
                items=items,
            )
        finally:
            await runtime.stop()
            context.database.engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", list(FrankfurtSourceMode))
async def test_only_public_quotes_use_scheduler_pacing_for_selected_routes(
    durable_database, tmp_path, monkeypatch, mode  # noqa: F811
):
    async with source_runtime(durable_database, tmp_path, monkeypatch, mode) as c:
        public = mode is FrankfurtSourceMode.PUBLIC_WEBSITE
        scheduler_deadline = c.runtime._next_request
        first = await c.runtime._warrant(c.items[0])
        assert first["status"] == "AVAILABLE"
        assert c.clock.value == 100 and c.clock.waits == []
        assert c.client.request_delay_seconds() == 15
        c.clock.value = 101
        second = await c.runtime._warrant(c.items[1])
        assert second["status"] == "AVAILABLE"
        assert c.clock.value == (115 if public else 101)
        assert c.clock.waits == ([14] if public else [])
        assert c.pace.await_count == (2 if public else 0)
        assert c.resolver.await_count == 2
        assert [entry[:2] for entry in c.resolutions] == [
            (100, "FRANKFURT_QUOTES"),
            (115 if public else 101, "FRANKFURT_QUOTES"),
        ]
        assert len(c.calls) == (2 if public else int(mode is FrankfurtSourceMode.HTTPS_JSON))
        assert c.file_reads.call_count == int(mode is FrankfurtSourceMode.LOCAL_FILE)
        quotes = [entry[2].result for entry in c.resolutions]
        assert all(quote is not None and quote.data is not None for quote in quotes)
        assert quotes[0].cache_status is CacheStatus.MISS
        assert quotes[1].cache_status is (CacheStatus.MISS if public else CacheStatus.HIT)
        assert quotes[0].retrieved_at == NOW
        assert quotes[1].retrieved_at == NOW + timedelta(seconds=15 if public else 0)
        assert [quote.data.isin for quote in quotes] == [FIRST, SECOND]
        assert all(
            quote.data.observed_at == NOW - timedelta(seconds=10 if public else 0)
            for quote in quotes
        )
        assert all(
            quote.data.currency == "EUR" and quote.data.refresh_error is None for quote in quotes
        )
        assert quotes[1].data.assessed_at == NOW + timedelta(seconds=15 if public else 1)
        assert c.runtime._next_request == (130 if public else scheduler_deadline)
        assert c.client.request_delay_seconds() == (15 if public else 14)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", [FrankfurtSourceMode.HTTPS_JSON, FrankfurtSourceMode.LOCAL_FILE])
async def test_shared_snapshot_expiry_keeps_client_budget_without_scheduler_pause(
    durable_database, tmp_path, monkeypatch, mode  # noqa: F811
):
    async with source_runtime(durable_database, tmp_path, monkeypatch, mode) as c:
        scheduler_deadline = c.runtime._next_request
        for current, index, reads, hit, retrieved_seconds, delay in (
            (100, 0, 1, False, 0, 15),
            (399.999, 1, 1, True, 0, 0),
            (400, 0, 2, False, 300, 15),
            (401, 1, 2, True, 300, 14),
        ):
            c.clock.value = current
            result = await c.runtime._warrant(c.items[index])
            assert result["status"] == "AVAILABLE" and c.clock.value == current
            assert len(c.calls) == (reads if mode is FrankfurtSourceMode.HTTPS_JSON else 0)
            assert c.file_reads.call_count == (
                reads if mode is FrankfurtSourceMode.LOCAL_FILE else 0
            )
            quote = c.resolutions[-1][2].result
            assert quote is not None and quote.data is not None
            assert quote.cache_status is (CacheStatus.HIT if hit else CacheStatus.MISS)
            assert quote.retrieved_at == NOW + timedelta(seconds=retrieved_seconds)
            assert quote.data.observed_at == NOW
            assert quote.data.assessed_at == c.clock.now()
            assert quote.data.isin == (FIRST, SECOND)[index]
            assert quote.data.refresh_error is None and not quote.data.retained
            assert c.client.last_success_at == quote.retrieved_at
            assert c.client.request_delay_seconds() == delay
            assert c.runtime._next_request == scheduler_deadline
        assert c.pace.await_count == 0 and c.clock.waits == []
        assert c.resolver.await_count == 4


@pytest.mark.asyncio
async def test_https_retry_after_preserves_original_quotes_and_regular_job_due_times(
    durable_database, tmp_path, monkeypatch  # noqa: F811
):
    async with source_runtime(
        durable_database,
        tmp_path,
        monkeypatch,
        FrankfurtSourceMode.HTTPS_JSON,
        http_failures={2: httpx.Response(429, headers={"Retry-After": "120"})},
    ) as c:
        scheduler_deadline = c.runtime._next_request
        keys = [f"WARRANT_QUOTES:{item.id}" for item in c.items]

        async def run_job(index, current):
            c.clock.value = current
            item = c.items[index]
            await c.runtime._job(keys[index], item, 300, lambda: c.runtime._warrant(item))
            assert c.clock.value == current

        for index in range(2):
            await run_job(index, 100 + index)
        assert [c.runtime._due[key] for key in keys] == [400, 401]
        assert len(c.calls) == 1 and c.resolver.await_count == 2

        for index, current in enumerate((400, 401)):
            await run_job(index, current)
            quote = c.runtime.jobs[keys[index]]["quotes"][0]
            assert quote["retrieved_at"] == quote["observed_at"] == NOW
            assert quote["refresh_error"] == "FRANKFURT_HTTP_429" and quote["retained"]
            assert c.client.last_success_at == NOW
            assert c.client.request_delay_seconds() == 520 - current
            assert len(c.calls) == 2
            assert c.runtime._due[keys[index]] == current + 300
        assert [c.runtime._due[key] for key in keys] == [700, 701]

        # The client cooldown ending does not introduce an earlier scheduled retry.
        for current in (519, 520, 699):
            for index in range(2):
                await run_job(index, current)
            assert c.client.request_delay_seconds() == max(0, 520 - current)
            assert c.client.last_success_at == NOW
            assert len(c.calls) == 2 and c.resolver.await_count == 4
            assert [c.runtime._due[key] for key in keys] == [700, 701]

        for index, current in enumerate((700, 701)):
            await run_job(index, current)
            quote = c.resolutions[-1][2].result
            assert quote is not None and quote.data is not None
            assert quote.cache_status is (CacheStatus.MISS if index == 0 else CacheStatus.HIT)
            assert quote.retrieved_at == NOW + timedelta(seconds=600)
            assert quote.data.observed_at == NOW
            assert quote.data.refresh_error is None and not quote.data.retained
            assert c.client.request_delay_seconds() == 15 - index
        assert [current for current, _ in c.calls] == [100, 400, 700]
        assert c.file_reads.call_count == 0 and c.resolver.await_count == 6
        assert c.client.last_success_at == NOW + timedelta(seconds=600)
        assert c.client.last_error is None
        assert [c.runtime._due[key] for key in keys] == [1000, 1001]
        assert c.runtime._next_request == scheduler_deadline
        assert c.pace.await_count == 0 and c.clock.waits == []


@pytest.mark.asyncio
async def test_local_file_error_backoff_keeps_original_quotes_without_scheduler_pause(
    durable_database, tmp_path, monkeypatch  # noqa: F811
):
    async with source_runtime(
        durable_database, tmp_path, monkeypatch, FrankfurtSourceMode.LOCAL_FILE
    ) as c:
        scheduler_deadline = c.runtime._next_request
        original_file = c.path.read_text(encoding="utf-8")
        for index in range(2):
            c.clock.value = 100 + index
            assert (await c.runtime._warrant(c.items[index]))["status"] == "AVAILABLE"
        assert c.file_reads.call_count == 1
        c.path.unlink()

        for current, index in ((400, 0), (401, 1), (459.999, 0)):
            c.clock.value = current
            result = await c.runtime._warrant(c.items[index])
            quote = result["quotes"][0]
            assert quote["retrieved_at"] == quote["observed_at"] == NOW
            assert quote["refresh_error"] == "FRANKFURT_LOCAL_FILE_UNAVAILABLE"
            assert quote["retained"]
            assert c.client.last_success_at == NOW
            assert c.client.request_delay_seconds() == pytest.approx(460 - current)
            assert c.file_reads.call_count == 2 and c.clock.value == current
            if current == 400:
                c.path.write_text(original_file, encoding="utf-8")

        for index, current in enumerate((460, 461)):
            c.clock.value = current
            await c.runtime._warrant(c.items[index])
            quote = c.resolutions[-1][2].result
            assert quote is not None and quote.data is not None
            assert quote.cache_status is (CacheStatus.MISS if index == 0 else CacheStatus.HIT)
            assert quote.retrieved_at == NOW + timedelta(seconds=360)
            assert quote.data.observed_at == NOW
            assert quote.data.refresh_error is None and not quote.data.retained
            assert c.client.request_delay_seconds() == 15 - index
            assert c.file_reads.call_count == 3 and c.clock.value == current
        assert c.client.last_success_at == NOW + timedelta(seconds=360)
        assert c.client.last_error is None
        assert c.calls == [] and c.resolver.await_count == 7
        assert c.runtime._next_request == scheduler_deadline
        assert c.pace.await_count == 0 and c.clock.waits == []


@pytest.mark.asyncio
@pytest.mark.parametrize("consumer", ["discovery", "quote"])
async def test_slot_consumed_after_pacing_is_bounded_and_never_reported_as_success(
    durable_database, tmp_path, monkeypatch, consumer  # noqa: F811
):
    async with source_runtime(
        durable_database, tmp_path, monkeypatch, FrankfurtSourceMode.PUBLIC_WEBSITE
    ) as c:
        paced, consumed = asyncio.Event(), asyncio.Event()

        async def pace_then_compete():
            await c.pace()
            paced.set()
            await consumed.wait()

        monkeypatch.setattr(c.runtime, "_pace", pace_then_compete)
        item = c.items[1]
        discovery = consumer == "discovery"
        key = f"{'FRANKFURT_MAPPING' if discovery else 'WARRANT_QUOTES'}:{item.id}"
        operation = c.runtime._configure_frankfurt if discovery else c.runtime._warrant
        interval = 3600 if discovery else 300
        task = asyncio.create_task(c.runtime._job(key, item, interval, lambda: operation(item)))
        try:
            await asyncio.wait_for(paced.wait(), timeout=1)
            await c.client.load_public(FIRST)  # Controlled interactive reader wins the slot.
            consumed.set()
            await asyncio.wait_for(task, timeout=1)
            job = c.runtime.jobs[key]
            assert job["last_success_at"] is None
            assert len(c.calls) == 1 and c.calls[0][1].url.params["isin"] == FIRST
            assert c.pace.await_count == 1 and c.clock.waits == []
            assert c.client.request_delay_seconds() == 15
            if discovery:
                assert job["status"] == "DEFERRED"
                assert job["reason"] == "FRANKFURT_REQUEST_THROTTLED"
                assert job["retry_after_seconds"] == 15
                assert c.runtime._due[key] == 115
                assert job["next_run_at"] - job["checked_at"] == timedelta(seconds=15)
                assert c.resolver.await_count == 0
            else:
                assert job["status"] == "MISSING" and job["quotes"] == []
                assert job["source_attempts"][0]["status"] == "ERROR"
                assert job["source_attempts"][0]["reason"] == "FRANKFURT_REQUEST_THROTTLED"
                assert c.runtime._due[key] == 400  # Existing quote job interval remains intact.
                assert c.resolver.await_count == 1
            c.clock.value = 114
            await c.runtime._job(key, item, interval, lambda: operation(item))
            assert len(c.calls) == c.pace.await_count == 1
            assert c.client.request_delay_seconds() == 1
        finally:
            consumed.set()
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)


@pytest.mark.asyncio
async def test_stop_joins_worker_waiting_in_real_pacing_and_requires_explicit_restart(
    durable_database, tmp_path, monkeypatch  # noqa: F811
):
    real_sleep = asyncio.sleep
    async with source_runtime(
        durable_database, tmp_path, monkeypatch, FrankfurtSourceMode.PUBLIC_WEBSITE
    ) as c:
        waiting, release, cancelled = asyncio.Event(), asyncio.Event(), asyncio.Event()

        async def blocking_sleep(seconds):
            assert seconds == 15
            c.clock.waits.append(seconds)
            waiting.set()
            try:
                await release.wait()
                c.clock.value += seconds
            finally:
                cancelled.set()

        monkeypatch.setattr(module.asyncio, "sleep", blocking_sleep)
        monkeypatch.setattr(module, "read_catalog", AsyncMock(return_value=([c.items[0]], [])))
        c.runtime._next_request = 115
        await c.runtime.run_once(wait_for_completion=False)
        await asyncio.wait_for(waiting.wait(), timeout=1)
        worker = c.runtime._lane_tasks[RefreshLane.WARRANTS]
        await c.runtime.stop()
        assert worker.cancelled() and cancelled.is_set()
        assert c.runtime._lane_tasks == {} and not c.runtime.running
        assert all(value is None for value in c.runtime._current_jobs.values())
        assert not c.client._lock.locked()
        assert c.clock.value == 100 and c.runtime._next_request == 115
        assert c.resolver.await_count == 0 and c.calls == []
        release.set()
        await real_sleep(0)
        assert c.runtime._lane_tasks == {} and c.calls == []
        # A later explicitly requested run can resume, using the same runtime/client.
        c.clock.value = 115
        monkeypatch.setattr(module.asyncio, "sleep", c.clock.sleep)
        await c.runtime.run_once()
        assert c.runtime.jobs[f"WARRANT_QUOTES:{c.items[0].id}"]["status"] == "AVAILABLE"
        assert len(c.calls) == c.resolver.await_count == 1
        assert c.clock.waits == [15] and not c.runtime.running
