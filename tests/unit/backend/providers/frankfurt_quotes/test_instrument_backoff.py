"""A missing public instrument must not stall unrelated portfolio observations."""

from datetime import timedelta
from email.utils import format_datetime
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from app.core.config.settings import Settings
from app.core.di import ApplicationContainer, get_container
from app.features.market_data.service.refresh import MarketDataRefreshRuntime
from app.features.position_monitoring.api import router
from app.providers.frankfurt_quotes.client import FrankfurtSnapshotClient
from app.providers.frankfurt_quotes.schema import FrankfurtSourceError
from tests.unit.backend.providers.frankfurt_quotes.test_adapter_api import context
from tests.unit.backend.providers.frankfurt_quotes.test_client import settings
from tests.unit.backend.providers.frankfurt_quotes.test_public import public_settings, wire
from tests.unit.backend.providers.frankfurt_quotes.test_schema import NOW

MISSING = "DE000JE7KTY8"
HELD = "DE000VH2LU21"
OTHER = "DE000VH7S657"


@pytest.mark.asyncio
async def test_public_404_has_its_own_retry_and_preserves_other_quote_provenance():
    timer, missing, calls = [0.0], [True], []

    def respond(request):
        isin = request.url.params["isin"]
        calls.append(isin)
        return (
            httpx.Response(404, text="SECRET")
            if isin == MISSING and missing[0]
            else httpx.Response(200, json=wire(isin=isin))
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        client = FrankfurtSnapshotClient(
            public_settings(),
            client=http,
            timer=lambda: timer[0],
            clock=lambda: NOW + timedelta(seconds=timer[0]),
            cache_seconds=300,
        )
        with pytest.raises(FrankfurtSourceError, match=r"^FRANKFURT_HTTP_404$"):
            await client.load_public(MISSING)
        assert client.request_delay_seconds() == 15
        assert client.instrument_backoff_count() == 1
        timer[0] = 14
        with pytest.raises(FrankfurtSourceError, match="REQUEST_THROTTLED"):
            await client.load_public(HELD)
        timer[0] = 15
        original = await client.load_public(HELD)
        assert original[0].isin == HELD and original[1] == NOW + timedelta(seconds=15)
        for moment in (30, 60, 300, 3599):
            timer[0] = moment
            before = client.request_delay_seconds()
            with pytest.raises(FrankfurtSourceError, match="HTTP_404"):
                await client.load_public(MISSING)
            assert client.request_delay_seconds() == before
        assert calls == [MISSING, HELD]
        assert client.cached_after_error("FRANKFURT_HTTP_503", MISSING) is None
        assert client.cached_after_error("FRANKFURT_REQUEST_THROTTLED", HELD) == original[:2]
        missing[0], timer[0] = False, 3600
        recovered = await client.load_public(MISSING)
        assert recovered[0].isin == MISSING
        assert recovered[1] == NOW + timedelta(seconds=3600)
        assert client.instrument_backoff_count() == 0
        assert calls == [MISSING, HELD, MISSING]


@pytest.mark.asyncio
async def test_scheduler_processes_52_instruments_without_19_extra_global_backoffs(monkeypatch):
    timer, calls = [0.0], []
    identities = [f"DE{index:010d}" for index in range(52)]
    missing = set(identities[:19])

    def respond(request):
        isin = request.url.params["isin"]
        calls.append(isin)
        return httpx.Response(404) if isin in missing else httpx.Response(200, json=wire(isin=isin))

    async def advance(seconds):
        timer[0] += seconds

    monkeypatch.setattr("app.features.market_data.service.refresh.asyncio.sleep", advance)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        client = FrankfurtSnapshotClient(public_settings(), client=http, timer=lambda: timer[0])
        pacer = SimpleNamespace(
            _next_request=0.0,
            timer=lambda: timer[0],
            settings=SimpleNamespace(request_spacing_seconds=15),
            container=SimpleNamespace(
                frankfurt=SimpleNamespace(snapshots=client, settings=client.settings)
            ),
        )
        for isin in identities:
            await MarketDataRefreshRuntime._pace(pacer)
            if isin in missing:
                with pytest.raises(FrankfurtSourceError, match="HTTP_404"):
                    await client.load_public(isin)
            else:
                value, _, _ = await client.load_public(isin)
                assert value.isin == isin
        assert calls == identities
        assert timer[0] == 51 * 15
        assert client.instrument_backoff_count() == 19
        for isin in missing:
            with pytest.raises(FrankfurtSourceError, match="HTTP_404"):
                await client.load_public(isin)
        assert len(calls) == 52


@pytest.mark.asyncio
@pytest.mark.parametrize("code", [401, 403, 429, 500, 503])
async def test_source_errors_still_block_other_instruments_and_access_clears_prices(code):
    timer, calls = [0.0], []

    def respond(request):
        isin = request.url.params["isin"]
        calls.append(isin)
        return httpx.Response(code) if isin == OTHER else httpx.Response(200, json=wire(isin=isin))

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        client = FrankfurtSnapshotClient(public_settings(), client=http, timer=lambda: timer[0])
        await client.load_public(HELD)
        timer[0] = 15
        with pytest.raises(FrankfurtSourceError, match=f"HTTP_{code}"):
            await client.load_public(OTHER)
        assert client.request_delay_seconds() == 60
        timer[0] = 74
        with pytest.raises(FrankfurtSourceError):
            await client.load_public(MISSING)
        assert len(calls) == 2
        if code in (401, 403):
            assert client.cached_after_error("FRANKFURT_REQUEST_THROTTLED", HELD) is None
        timer[0] = 75
        assert (await client.load_public(MISSING))[0].isin == MISSING


@pytest.mark.asyncio
@pytest.mark.parametrize("code", [429, 503])
@pytest.mark.parametrize(
    "header,delay",
    [
        ("120", 120),
        (format_datetime(NOW + timedelta(seconds=180), usegmt=True), 180),
        ("invalid", 60),
        ("Wed, 01 Jan 2025 00:00:00", 60),
        ("-1", 60),
        ("9" * 400, 60),
        (format_datetime(NOW - timedelta(seconds=1), usegmt=True), 60),
    ],
)
async def test_retry_after_is_respected_without_exposing_headers(code, header, delay):
    timer, calls = [0.0], []

    def respond(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(code, headers={"Retry-After": header}, text="SECRET")
        return httpx.Response(200, json=wire(isin=request.url.params["isin"]))

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        client = FrankfurtSnapshotClient(
            public_settings(), client=http, timer=lambda: timer[0], clock=lambda: NOW
        )
        with pytest.raises(FrankfurtSourceError, match=f"^FRANKFURT_HTTP_{code}$"):
            await client.load_public(HELD)
        assert client.request_delay_seconds() == delay
        timer[0] = delay - 1
        with pytest.raises(FrankfurtSourceError, match="REQUEST_THROTTLED"):
            await client.load_public(OTHER)
        assert len(calls) == 1
        timer[0] = delay
        assert (await client.load_public(OTHER))[0].isin == OTHER


@pytest.mark.asyncio
async def test_bulk_endpoint_404_retains_source_backoff():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(404))
    ) as http:
        client = FrankfurtSnapshotClient(settings(), client=http, timer=lambda: 0)
        with pytest.raises(FrankfurtSourceError, match="HTTP_404"):
            await client.load()
        assert client.request_delay_seconds() == 60
        assert client.instrument_backoff_count() == 0


@pytest.mark.asyncio
async def test_health_exposes_instrument_backoff_separately_from_source_cooldown():
    timer = [0.0]
    config = public_settings()
    adapter, database, _, _, _ = context()
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(404))
    ) as http:
        snapshots = FrankfurtSnapshotClient(config, client=http, timer=lambda: timer[0])
        adapter.snapshots = snapshots
        with pytest.raises(FrankfurtSourceError):
            await snapshots.load_public(MISSING)
        timer[0] = 15
        container = ApplicationContainer(
            settings=Settings(_env_file=None, market_data={"frankfurt": config}),
            database=database,
            frankfurt=adapter,
        )
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_container] = lambda: container
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://test"
        ) as api:
            response = await api.get("/api/v1/position-monitoring/quote-sources/frankfurt/health")
        assert response.status_code == 200
        result = response.json()
        assert result["instrument_backoff_count"] == 1
        assert result["instrument_retry_seconds"] == 3600
        assert result["request_cooldown_seconds"] == 0
        assert result["coverage_verified"] is result["execution_usable"] is False


@pytest.mark.parametrize("interval", [0, 59, 86401])
def test_instrument_retry_interval_is_bounded(interval):
    with pytest.raises(ValidationError):
        public_settings(instrument_retry_seconds=interval)


@pytest.mark.asyncio
async def test_negative_cache_is_bounded_and_does_not_hide_a_source_access_failure():
    timer, calls, blocked = [0.0], [], [False]

    def respond(request):
        calls.append(request)
        return httpx.Response(403 if blocked[0] else 404)

    config = public_settings(instrument_retry_seconds=86400)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        client = FrankfurtSnapshotClient(config, client=http, timer=lambda: timer[0])
        identities = [f"DE{index:010d}" for index in range(257)]
        for isin in identities:
            with pytest.raises(FrankfurtSourceError, match="HTTP_404"):
                await client.load_public(isin)
            timer[0] += 15
        assert client.instrument_backoff_count() == 256
        with pytest.raises(FrankfurtSourceError, match="HTTP_404"):
            await client.load_public(identities[-1])
        assert len(calls) == 257
        # The evicted identity is probed again at the ordinary global request rate.
        with pytest.raises(FrankfurtSourceError, match="HTTP_404"):
            await client.load_public(identities[0])
        assert len(calls) == 258
        assert client.instrument_backoff_count() == 256
        timer[0] += 15
        blocked[0] = True
        with pytest.raises(FrankfurtSourceError, match="HTTP_403"):
            await client.load_public(OTHER)
        with pytest.raises(FrankfurtSourceError, match="HTTP_403"):
            await client.load_public(identities[0])
        assert len(calls) == 259
