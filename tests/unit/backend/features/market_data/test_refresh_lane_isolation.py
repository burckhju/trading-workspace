import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.config.frankfurt import FrankfurtSourceMode
from app.core.di import ApplicationContainer
from app.features.market_data.service import refresh as module
from app.features.market_data.service.refresh import (
    MarketDataRefreshRuntime,
    RefreshLane,
    _job_lane,
)
from app.features.market_data.service.refresh_catalog import RefreshInstrument


def runtime() -> MarketDataRefreshRuntime:
    settings = Settings(environment="test", market_data={"refresh": {"enabled": True}})
    result = MarketDataRefreshRuntime(ApplicationContainer.build(settings), timer=lambda: 1000)
    result._pace = AsyncMock()
    result._pace_underlying = AsyncMock()
    return result


@asynccontextmanager
async def session_context(session):
    yield session


def test_mapping_discovery_has_separate_lane_from_warrant_quotes() -> None:
    assert _job_lane("WARRANT_QUOTES:1") is RefreshLane.WARRANTS
    assert _job_lane("FRANKFURT_MAPPING:1") is RefreshLane.WARRANT_DISCOVERY
    assert _job_lane("VONTOBEL_MAPPING:1") is RefreshLane.WARRANT_DISCOVERY
    assert _job_lane("EODHD_MAPPING:1:2") is RefreshLane.UNDERLYINGS
    assert _job_lane("UNDERLYING_EOD:1:2") is RefreshLane.UNDERLYINGS


@pytest.mark.asyncio
async def test_slow_discovery_does_not_block_warrant_quote_lane(monkeypatch) -> None:
    value = runtime()
    item = RefreshInstrument(uuid4(), "Held", "DE000TEST123", held=True)
    monkeypatch.setattr(module, "read_catalog", AsyncMock(return_value=([item], [])))
    value.container = SimpleNamespace(
        database=object(),
        frankfurt=SimpleNamespace(
            settings=SimpleNamespace(source_mode=FrankfurtSourceMode.PUBLIC_WEBSITE)
        ),
        vontobel=None,
    )
    discovery_started = asyncio.Event()
    release_discovery = asyncio.Event()
    quote_finished = asyncio.Event()

    async def discover(_item):
        discovery_started.set()
        await release_discovery.wait()
        return {"reason": "FRANKFURT_IDENTITY_VERIFIED"}

    async def quote(_item):
        quote_finished.set()
        return {"reason": "QUOTE_OBSERVATIONS_AVAILABLE"}

    value._configure_frankfurt = discover
    value._warrant = quote

    await value.run_once(wait_for_completion=False)
    try:
        await asyncio.wait_for(discovery_started.wait(), timeout=1)
        await asyncio.wait_for(quote_finished.wait(), timeout=1)

        status = value.status()
        quote_job = status["jobs"][1]
        assert quote_job["job"] == f"WARRANT_QUOTES:{item.id}"
        assert quote_job["status"] == "AVAILABLE"
        assert quote_job["lane"] == RefreshLane.WARRANTS.value
        assert status["lanes"][RefreshLane.WARRANT_DISCOVERY.value]["running"] is True
    finally:
        release_discovery.set()
        await value.stop()


@pytest.mark.asyncio
async def test_same_cycle_discovery_retries_quote_that_missed_before_mapping(monkeypatch) -> None:
    value = runtime()
    item = RefreshInstrument(uuid4(), "Unrouted", "DE000TEST456")
    monkeypatch.setattr(module, "read_catalog", AsyncMock(return_value=([item], [])))
    value.container = SimpleNamespace(
        database=object(),
        frankfurt=SimpleNamespace(
            settings=SimpleNamespace(source_mode=FrankfurtSourceMode.PUBLIC_WEBSITE)
        ),
        vontobel=None,
    )
    first_quote_finished = asyncio.Event()
    quote_calls = 0

    async def discover(_item):
        await first_quote_finished.wait()
        return {"reason": "FRANKFURT_IDENTITY_VERIFIED"}

    async def quote(_item):
        nonlocal quote_calls
        quote_calls += 1
        if quote_calls == 1:
            first_quote_finished.set()
            return {
                "status": "MISSING",
                "reason": "NO_USABLE_WARRANT_QUOTE",
                "active_listing_count": 0,
            }
        return {"status": "AVAILABLE", "reason": "QUOTE_OBSERVATIONS_AVAILABLE"}

    value._configure_frankfurt = discover
    value._warrant = quote

    await value.run_once()

    quote_job = value.jobs[f"WARRANT_QUOTES:{item.id}"]
    assert quote_calls == 2
    assert quote_job["status"] == "AVAILABLE"
    assert quote_job["reason"] == "QUOTE_OBSERVATIONS_AVAILABLE"


@pytest.mark.asyncio
async def test_warrant_paces_only_public_frankfurt_listings() -> None:
    value = runtime()
    xf_listing = SimpleNamespace(id=uuid4(), quotation_currency_code="EUR")
    other_listing = SimpleNamespace(id=uuid4(), quotation_currency_code="EUR")
    session = SimpleNamespace(
        execute=AsyncMock(
            return_value=SimpleNamespace(
                all=Mock(return_value=[(xf_listing, "XFRA"), (other_listing, "XSTU")])
            )
        ),
        scalars=AsyncMock(return_value=[]),
    )
    value.container = SimpleNamespace(
        database=SimpleNamespace(session_context=lambda: session_context(session)),
        frankfurt=SimpleNamespace(
            settings=SimpleNamespace(source_mode=FrankfurtSourceMode.PUBLIC_WEBSITE)
        ),
        vontobel=None,
    )
    value._resolver = SimpleNamespace(
        resolve=AsyncMock(return_value=SimpleNamespace(attempts=(), result=None))
    )

    result = await value._warrant(RefreshInstrument(uuid4(), "Warrant", "DE000TEST123"))

    value._pace.assert_awaited_once()
    assert value._resolver.resolve.await_count == 2
    assert result["active_listing_count"] == 2
