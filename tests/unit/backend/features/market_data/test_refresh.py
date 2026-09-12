import asyncio
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from tests.unit.backend.providers.frankfurt_quotes.test_public import public_settings, wire
from tests.unit.backend.providers.frankfurt_quotes.test_schema import NOW
from tests.unit.backend.providers.vontobel_markets.test_adapter import _html, _identity

from app.core.config import Settings
from app.core.config.settings import MarketDataRefreshSettings, VontobelMarketsSettings
from app.core.di import ApplicationContainer
from app.features.market_data.service import refresh as module
from app.features.market_data.service.refresh import MarketDataRefreshRuntime
from app.features.market_data.service.refresh_catalog import RefreshInstrument, read_catalog
from app.features.market_data.service.types import WarrantQuoteRequest
from app.main import create_application
from app.providers.frankfurt_quotes.client import FrankfurtSnapshotClient
from app.providers.frankfurt_quotes.schema import FrankfurtSourceError
from app.providers.vontobel_markets.adapter import VontobelMarketsWarrantQuoteAdapter


def runtime(**settings):
    config = Settings(environment="test", market_data={"refresh": {"enabled": True, **settings}})
    result = MarketDataRefreshRuntime(ApplicationContainer.build(config), timer=lambda: 1000)
    result._pace = AsyncMock()
    return result


@asynccontextmanager
async def session_context(session):
    yield session


@pytest.mark.asyncio
async def test_catalog_schedule_rechecks_new_instruments_and_keeps_independent_intervals(
    monkeypatch,
):
    value = runtime()
    first = RefreshInstrument(uuid4(), "One", "DE000VH2LU21")
    second = RefreshInstrument(uuid4(), "Two", "DE000VV00123")
    stock = RefreshInstrument(uuid4(), "Stock", "US91324P1021", listing_id=uuid4())
    catalog = AsyncMock(return_value=([first], [stock]))
    monkeypatch.setattr(module, "read_catalog", catalog)
    value._warrant = AsyncMock(return_value={"reason": "quote"})
    value._underlying = AsyncMock(return_value={"reason": "eod"})
    value._configure_underlying = AsyncMock(return_value={"status": "BLOCKED"})
    await value.run_once()
    await value.run_once()
    value._warrant.assert_awaited_once_with(first)
    value._underlying.assert_awaited_once_with(stock)
    catalog.return_value = ([first, second], [stock])
    await value.run_once()
    assert value._warrant.await_count == 2
    value.timer = lambda: 1301
    await value.run_once()
    assert value._warrant.await_count == 4
    assert value._underlying.await_count == 1
    assert len(value.status()["jobs"]) == 4
    catalog.return_value = ([], [])
    await value.run_once()
    assert value.jobs == value._due == {}


@pytest.mark.asyncio
async def test_item_errors_are_isolated_and_disabled_scheduler_is_inert(monkeypatch):
    value = runtime()
    items = [RefreshInstrument(uuid4(), "One", None), RefreshInstrument(uuid4(), "Two", None)]
    monkeypatch.setattr(module, "read_catalog", AsyncMock(return_value=(items, [])))
    value._warrant = AsyncMock(side_effect=[ValueError("ISIN_REQUIRED"), {"reason": "OK"}])
    await value.run_once()
    assert [job["status"] for job in value.jobs.values()] == ["ERROR", "AVAILABLE"]
    assert next(iter(value.jobs.values()))["reason"] == "ISIN_REQUIRED"
    value.settings.enabled = False
    await value.run_once()
    assert value._warrant.await_count == 2
    value.settings.enabled = True
    monkeypatch.setattr(module, "read_catalog", AsyncMock(side_effect=RuntimeError("secret URL")))
    await value.run_once()
    assert value.status()["last_error"] == "RuntimeError"
    assert value.running is False


@pytest.mark.asyncio
async def test_overlapping_cycles_and_cancellation_do_not_duplicate_or_hide_work(monkeypatch):
    value = runtime()
    catalog = AsyncMock(side_effect=asyncio.CancelledError)
    monkeypatch.setattr(module, "read_catalog", catalog)
    async with value._lock:
        await value.run_once()
    catalog.assert_not_awaited()
    with pytest.raises(asyncio.CancelledError):
        await value.run_once()
    assert value.running is False
    with pytest.raises(asyncio.CancelledError):
        await value._job("test", RefreshInstrument(uuid4(), "One", None), 300, catalog)
    assert value.jobs == {}


@pytest.mark.asyncio
async def test_job_keeps_last_success_metadata_but_does_not_relabel_failure():
    value = runtime()
    item = RefreshInstrument(uuid4(), "One", None)
    await value._job("x", item, 300, AsyncMock(return_value={"reason": "OK"}))
    previous = value.jobs["x"]["last_success_at"]
    value.timer = lambda: 1301
    await value._job("x", item, 300, AsyncMock(side_effect=RuntimeError("secret URL")))
    assert value.jobs["x"]["last_success_at"] == previous
    assert value.jobs["x"]["status"] == "ERROR"
    assert value.jobs["x"]["reason"] == "RuntimeError"
    assert value.jobs["x"]["next_run_at"] > value.jobs["x"]["checked_at"]


@pytest.mark.asyncio
async def test_vontobel_cache_keeps_retrieval_time_reassesses_age_and_checks_mapping_each_read():
    calls = []

    def respond(request):
        calls.append(request.url)
        return httpx.Response(200, text=_html())

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        adapter = VontobelMarketsWarrantQuoteAdapter(
            database=object(),
            settings=VontobelMarketsSettings(enabled=True),
            client=client,
            cache_seconds=300,
        )
        adapter._resolve_identity = AsyncMock(return_value=_identity())
        request = WarrantQuoteRequest(uuid4(), _identity().listing_id, uuid4(), datetime.now(UTC))
        first = await adapter.get_warrant_listing_quote(request)
        second = await adapter.get_warrant_listing_quote(request)
        assert len(calls) == 1
        assert adapter._resolve_identity.await_count == 2
        assert first.retrieved_at == second.retrieved_at
        assert second.data.observed_at == first.data.observed_at
        assert second.data.assessed_at >= first.data.assessed_at
        assert second.data.bid == Decimal("0.24")
        assert second.cache_status.value == "HIT"
        adapter._resolve_identity.side_effect = ValueError("disabled mapping")
        with pytest.raises(ValueError, match="disabled mapping"):
            await adapter.get_warrant_listing_quote(request)
        assert len(calls) == 1


@pytest.mark.asyncio
async def test_frankfurt_cache_preserves_retrieval_time_and_global_budget():
    import json

    timer = [1000.0]
    client = FrankfurtSnapshotClient(
        public_settings(), timer=lambda: timer[0], clock=lambda: NOW, cache_seconds=300
    )
    client._read = AsyncMock(return_value=json.dumps(wire()).encode())
    first = await client.load_public("DE000VH2LU21")
    timer[0] += 60
    second = await client.load_public("DE000VH2LU21")
    assert first[0] == second[0] and first[1] == second[1]
    assert second[2] is True
    client._read.assert_awaited_once()
    timer[0] += 301
    await client.load_public("DE000VH2LU21")
    assert client._read.await_count == 2
    with pytest.raises(FrankfurtSourceError, match="THROTTLED"):
        await client.load_public("DE000VV00123")
    assert client._read.await_count == 2


@pytest.mark.asyncio
async def test_no_secret_or_provider_enabling_from_scheduler_settings():
    with pytest.raises(ValidationError):
        MarketDataRefreshSettings(warrants_interval_seconds=0)
    value = runtime()
    assert value.container.eodhd is value.container.vontobel is value.container.frankfurt is None
    blocked = await value._underlying(RefreshInstrument(uuid4(), "Stock", None))
    assert blocked == {"status": "BLOCKED", "reason": "EODHD_DISABLED"}
    app = create_application(Settings(environment="test"))
    client = TestClient(app)
    assert client.get("/api/v1/market-data/refresh/status").json()["enabled"] is False
    assert client.post("/api/v1/market-data/refresh/run").status_code == 409
    app.state.market_data_refresh.settings.enabled = True
    assert client.post("/api/v1/market-data/refresh/run").status_code == 202
    assert app.state.market_data_refresh.wake.is_set()


@pytest.mark.asyncio
async def test_catalog_preserves_unlisted_underlyings_and_scopes_all_reads():
    workspace = uuid4()
    warrant = SimpleNamespace(id=uuid4(), display_name="Warrant", isin="DE000VH2LU21")
    stock = SimpleNamespace(id=uuid4(), name="Stock", isin=None)
    session = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                Mock(
                    all=Mock(return_value=[(warrant, SimpleNamespace(legal_name="Vontobel"), True)])
                ),
                Mock(all=Mock(return_value=[(stock, None, False)])),
            ]
        )
    )
    database = SimpleNamespace(session_context=lambda: session_context(session))
    warrants, stocks = await read_catalog(database, workspace)
    assert warrants[0].id == warrant.id and stocks[0].listing_id is None
    assert warrants[0].held is True and stocks[0].held is False
    for call in session.execute.call_args_list:
        statement = call.args[0]
        assert workspace in statement.compile().params.values()
        assert "lifecycle_status" in str(statement)


@pytest.mark.asyncio
async def test_request_spacing_uses_provider_budget(monkeypatch):
    value = runtime()
    sleeper = AsyncMock()
    monkeypatch.setattr(module.asyncio, "sleep", sleeper)
    # Exercise the real method with a deterministic monotonic clock.
    await MarketDataRefreshRuntime._pace(value)
    await MarketDataRefreshRuntime._pace(value)
    assert sleeper.await_args.args[0] == 15


@pytest.mark.asyncio
async def test_underlying_import_uses_incremental_range_and_preserves_eod_kind():
    from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider

    value = runtime()
    mapping = SimpleNamespace(
        id=uuid4(),
        status=MappingStatus.ACTIVE,
        validated_at=NOW,
        provider_symbol="UNH",
        provider_exchange_code="US",
    )
    last_day = datetime.now(UTC).date() - timedelta(days=2)
    session = SimpleNamespace(scalar=AsyncMock(side_effect=[mapping, last_day]))
    service = SimpleNamespace(
        import_daily_prices=AsyncMock(
            return_value=SimpleNamespace(
                processed=8, provider=MarketDataProvider.EODHD, retrieved_at=NOW
            )
        )
    )
    value.container = SimpleNamespace(
        eodhd=object(),
        database=SimpleNamespace(session_context=lambda: session_context(session)),
        daily_price_import_service=lambda: session_context(service),
    )
    item = RefreshInstrument(uuid4(), "Stock", "US91324P1021", listing_id=uuid4())
    result = await value._underlying(item)
    request = service.import_daily_prices.await_args.args[0]
    assert request.mapping_id == mapping.id and request.listing_id == item.listing_id
    assert request.start_date == last_day - timedelta(days=7)
    assert request.end_date == datetime.now(UTC).date() - timedelta(days=1)
    assert result["price_type"] == "EOD" and result["execution_usable"] is False
    mapping.status = MappingStatus.DISABLED
    session.scalar.side_effect = [mapping, last_day]
    result = await value._underlying(item)
    assert result["reason"] == "VALIDATED_EODHD_MAPPING_REQUIRED"
    service.import_daily_prices.assert_awaited_once()
    assert (await value._underlying(RefreshInstrument(uuid4(), "Stock", None)))[
        "status"
    ] == "BLOCKED"


@pytest.mark.asyncio
async def test_background_scheduler_releases_leader_lock_on_shutdown():
    from app.features.market_data.service.refresh_runner import run_refresh_forever

    called = asyncio.Event()

    async def run():
        called.set()

    connection = SimpleNamespace(
        scalar=AsyncMock(return_value=True), execute=AsyncMock(), commit=AsyncMock()
    )
    value = SimpleNamespace(
        workspace_id=uuid4(),
        leader=False,
        container=SimpleNamespace(
            database=SimpleNamespace(
                engine=SimpleNamespace(connect=lambda: session_context(connection))
            )
        ),
        run_once=run,
        wake=asyncio.Event(),
        last_error=None,
    )
    task = asyncio.create_task(run_refresh_forever(value))
    await asyncio.wait_for(called.wait(), timeout=1)
    assert value.leader is True
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert value.leader is False
    assert "pg_advisory_unlock" in str(connection.execute.call_args.args[0])


@pytest.mark.asyncio
async def test_background_replica_does_not_run_without_leader_lock():
    from app.features.market_data.service.refresh_runner import run_refresh_forever

    checked = asyncio.Event()

    async def acquire(*args):
        checked.set()
        return False

    connection = SimpleNamespace(scalar=AsyncMock(side_effect=acquire), commit=AsyncMock())
    value = SimpleNamespace(
        workspace_id=uuid4(),
        leader=False,
        container=SimpleNamespace(
            database=SimpleNamespace(
                engine=SimpleNamespace(connect=lambda: session_context(connection))
            )
        ),
        run_once=AsyncMock(),
        wake=asyncio.Event(),
        last_error=None,
    )
    task = asyncio.create_task(run_refresh_forever(value))
    await asyncio.wait_for(checked.wait(), timeout=1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    value.run_once.assert_not_awaited()


@pytest.mark.asyncio
async def test_scheduler_observes_frankfurt_cooldown_after_response_and_failure(monkeypatch):
    value = runtime()
    value.container = SimpleNamespace(
        frankfurt=SimpleNamespace(
            settings=SimpleNamespace(refresh_interval_seconds=15),
            snapshots=SimpleNamespace(request_delay_seconds=lambda: 59.0),
        )
    )
    sleeper = AsyncMock()
    monkeypatch.setattr(module.asyncio, "sleep", sleeper)
    await MarketDataRefreshRuntime._pace(value)
    sleeper.assert_awaited_once_with(59.0)


@pytest.mark.asyncio
async def test_open_positions_are_first_and_entire_queue_is_visible_before_network(monkeypatch):
    value = runtime()
    catalog_only = RefreshInstrument(uuid4(), "Catalog", "DE000HM4EB12")
    held = RefreshInstrument(uuid4(), "Held", "DE000VH2LU21", held=True)
    stock = RefreshInstrument(uuid4(), "Held stock", None, held=True)
    monkeypatch.setattr(
        module, "read_catalog", AsyncMock(return_value=([catalog_only, held], [stock]))
    )
    started, release = asyncio.Event(), asyncio.Event()
    order = []

    async def quote(item):
        order.append(item.name)
        if item.held:
            started.set()
            await release.wait()
        return {"reason": "OK"}

    async def daily(item):
        order.append(item.name)
        return {"status": "BLOCKED", "reason": "EODHD_DISABLED"}

    value._warrant = quote
    value._underlying = daily
    task = asyncio.create_task(value.run_once())
    try:
        await asyncio.wait_for(started.wait(), timeout=1)
        status = value.status()
        assert status["pending_jobs"] == 3
        assert status["current_job"] == f"WARRANT_QUOTES:{held.id}"
        assert [j["name"] for j in status["jobs"]] == ["Held", "Held stock", "Catalog"]
        assert all(j["checked_at"] is None and j["next_run_at"] is None for j in status["jobs"])
    finally:
        release.set()
        await task
    assert order == ["Held", "Held stock", "Catalog"]
    assert value.status()["pending_jobs"] == 0 and value.current_job is None


@pytest.mark.asyncio
async def test_discovery_reports_safe_frankfurt_reason_instead_of_opaque_exception():
    value = runtime()
    await value._job(
        "mapping",
        RefreshInstrument(uuid4(), "Invalid identifier", "DE000PK72H6"),
        3600,
        AsyncMock(side_effect=FrankfurtSourceError("FRANKFURT_ISIN_INVALID")),
    )
    assert value.jobs["mapping"]["reason"] == "FRANKFURT_ISIN_INVALID"
    assert value.jobs["mapping"]["status"] == "ERROR"
    assert value.current_job is None
