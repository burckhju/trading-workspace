"""Previously retrieved data survives transient outages only as disclosed analysis."""

import importlib
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import httpx
import pytest
from fastapi import FastAPI

from app.core.di import get_container
from app.features.market_data.service.errors import MarketDataInvalidResponseError
from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuationService,
)
from app.features.position_monitoring.service.quote_sources import (
    MultiSourceWarrantQuoteResolver,
    NamedWarrantQuoteSource,
)
from app.providers.frankfurt_quotes.client import FrankfurtSnapshotClient
from app.providers.frankfurt_quotes.schema import FrankfurtSourceError
from tests.unit.backend.features.position_monitoring.test_product_valuation import (
    _context,
    _Database,
    _Provider,
    _quote_result,
    _Session,
)
from tests.unit.backend.providers.frankfurt_quotes.test_adapter_api import context
from tests.unit.backend.providers.frankfurt_quotes.test_client import settings
from tests.unit.backend.providers.frankfurt_quotes.test_public import public_settings, wire
from tests.unit.backend.providers.frankfurt_quotes.test_schema import NOW, payload

monitoring_api = importlib.import_module("app.features.position_monitoring.api.router")


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["LAST_TRADE", "PREVIOUS_CLOSE", "BID_ASK"])
async def test_outage_preserves_indicative_api_provenance_and_recovers(monkeypatch, kind):
    timer = [0.0]
    failures = [False]
    calls = []
    data = payload() if kind == "BID_ASK" else wire()
    if kind == "PREVIOUS_CLOSE":
        data.update(lastPrice=None, closingPricePrevTradingDay="0.231")

    def handler(request):
        calls.append(request)
        return httpx.Response(503, text="SECRET") if failures[0] else httpx.Response(200, json=data)

    adapter, _, _, request, row = context()
    config = settings() if kind == "BID_ASK" else public_settings()
    row[2].provider_exchange_code = "XFRA" if kind == "BID_ASK" else "XSC"
    adapter.settings = config

    def clock():
        return NOW + timedelta(seconds=timer[0])

    adapter._clock = clock
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as upstream:
        client = FrankfurtSnapshotClient(
            config, client=upstream, clock=clock, timer=lambda: timer[0]
        )
        adapter.snapshots = client
        trade, position, evaluation, listing = _context()
        listing.id = evaluation.warrant_listing_id = row[0].id
        position.open_quantity, position.cost_basis = 2000, Decimal("1020")

        def make_service(**_):
            return ProductPositionValuationService(
                database=_Database(
                    _Session(trade=trade, position=position, evaluation=evaluation, listing=listing)
                ),
                quote_resolver=MultiSourceWarrantQuoteResolver(
                    (NamedWarrantQuoteSource("FRANKFURT_QUOTES", adapter),)
                ),
            )

        monkeypatch.setattr(monitoring_api, "ProductPositionValuationService", make_service)
        monkeypatch.setattr(monitoring_api, "build_warrant_quote_resolver", lambda _: None)
        app = FastAPI()
        app.include_router(monitoring_api.router)
        app.dependency_overrides[get_container] = lambda: type(
            "Container", (), {"database": None}
        )()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as api:
            url = f"/api/v1/position-monitoring/trades/{trade.id}/product-valuation"
            original = (await api.get(url)).json()
            assert original["analysis_usable"] is True
            failures[0], timer[0] = True, 30.0
            for moment in (30.0, 45.0):
                timer[0] = moment
                response = await api.get(url)
                assert response.status_code == 200, response.text
                value = response.json()
                assert value["status"] == "INDICATIVE"
                assert value["reason"] == "LAST_SUCCESSFUL_QUOTE_REFRESH_FAILED"
                assert value["quote_refresh_error"] == "FRANKFURT_HTTP_503"
                assert value["analysis_warning"] == "QUOTE_REFRESH_FAILED_INDICATIVE_ANALYSIS_ONLY"
                assert value["analysis_usable"] is value["monitoring_usable"] is True
                assert value["valuation_usable"] is value["execution_usable"] is False
                assert value["market_value"] is value["unrealized_gross_pnl"] is None
                for key in (
                    "analysis_market_value",
                    "analysis_unrealized_gross_pnl",
                    "reference_price_type",
                    "reference_price",
                    "bid",
                    "ask",
                    "provider_identity",
                    "quote_venue_mic",
                    "provider_exchange_code",
                    "quote_observed_at",
                    "quote_retrieved_at",
                ):
                    assert value[key] == original[key], key
                expected_age = (
                    None
                    if kind == "PREVIOUS_CLOSE"
                    else original["quote_age_seconds"] + int(moment)
                )
                assert value["quote_age_seconds"] == expected_age
                assert value["quote_assessed_at"] == clock().isoformat().replace("+00:00", "Z")
                assert value["source_attempts"][0]["refresh_error"] == "FRANKFURT_HTTP_503"
                assert (
                    value["source_attempts"][0]["reason"] == "LAST_SUCCESSFUL_QUOTE_REFRESH_FAILED"
                )
                assert "SECRET" not in response.text
            assert len(calls) == 2  # Backoff and historical reads do not perform requests.
            assert client.last_success_at == NOW
            observation, hit = await adapter.inspect(request)
            assert hit and observation.analysis_usable
            assert observation.status != "AVAILABLE"
            assert observation.refresh_error == "FRANKFURT_HTTP_503"
            # Setup/coverage probes cannot mistake historical reuse for new verification.
            with pytest.raises(FrankfurtSourceError, match="HTTP_503"):
                if kind == "BID_ASK":
                    await client.load()
                else:
                    await client.load_public("DE000VH2LU21")
            failures[0], timer[0] = False, 90.0
            recovered = (await api.get(url)).json()
            assert recovered["quote_refresh_error"] is None
            assert recovered["quote_observed_at"] == original["quote_observed_at"]
            assert recovered["quote_retrieved_at"] != original["quote_retrieved_at"]
            assert recovered["execution_usable"] is False
            assert recovered["status"] == ("AVAILABLE" if kind == "BID_ASK" else "INDICATIVE")
            assert client.last_error is None
            assert len(calls) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code,body",
    [
        (401, {}),
        (403, {}),
        (404, {}),
        (200, {}),
        (200, []),
        (200, wire(isin="US91324P1021")),
        (200, wire(mic="XETR")),
        (200, wire(lastPrice="NaN")),
    ],
)
async def test_access_identity_and_schema_failures_never_resurrect_old_success(code, body):
    timer = [0.0]
    calls = []

    def handler(request):
        calls.append(request)
        return (
            httpx.Response(200, json=wire()) if len(calls) == 1 else httpx.Response(code, json=body)
        )

    adapter, _, _, request, row = context()
    row[2].provider_exchange_code = "XSC"
    adapter.settings = public_settings()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as upstream:
        client = FrankfurtSnapshotClient(
            public_settings(), client=upstream, clock=lambda: NOW, timer=lambda: timer[0]
        )
        adapter.snapshots = client
        assert (await adapter.get_warrant_listing_quote(request)).data is not None
        timer[0] = 30
        for _ in range(2):
            with pytest.raises(MarketDataInvalidResponseError):
                await adapter.get_warrant_listing_quote(request)
        assert client.cached_after_error("FRANKFURT_HTTP_503", "DE000VH2LU21") is None
        assert len(calls) == 2


@pytest.mark.asyncio
async def test_portfolio_throttling_reuses_only_the_exact_previously_loaded_instrument():
    timer = [0.0]
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=wire(isin=request.url.params["isin"]))

    adapter, _, _, request, row = context()
    row[2].provider_exchange_code = "XSC"
    adapter.settings = public_settings()
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as upstream:
        client = FrankfurtSnapshotClient(
            public_settings(), client=upstream, clock=lambda: NOW, timer=lambda: timer[0]
        )
        adapter.snapshots = client
        original = await adapter.get_warrant_listing_quote(request)
        timer[0] = 15
        await client.load_public("DE000VH7S657")
        reused = await adapter.get_warrant_listing_quote(request)
        assert reused.data.provider_symbol == "DE000VH2LU21"
        assert reused.data.reference_price == original.data.reference_price
        assert reused.data.refresh_error == "FRANKFURT_REQUEST_THROTTLED"
        assert reused.retrieved_at == original.retrieved_at
        assert client.cached_after_error("FRANKFURT_REQUEST_THROTTLED", "DE000VX12345") is None
        assert len(calls) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes",
    [
        {"currency": {"originalValue": "USD"}},
        {"timestampLastPrice": (NOW + timedelta(seconds=1)).isoformat()},
        {"lastPrice": None},
    ],
)
async def test_cached_payload_still_requires_semantic_validation(changes):
    timer = [0.0]
    adapter, _, _, request, row = context()
    row[2].provider_exchange_code = "XSC"
    adapter.settings = public_settings()
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: (
                httpx.Response(200, json=wire(**changes)) if timer[0] == 0 else httpx.Response(503)
            )
        )
    ) as upstream:
        adapter.snapshots = FrankfurtSnapshotClient(
            public_settings(), client=upstream, clock=lambda: NOW, timer=lambda: timer[0]
        )
        assert (await adapter.get_warrant_listing_quote(request)).data is None
        timer[0] = 30
        assert (await adapter.get_warrant_listing_quote(request)).data is None


@pytest.mark.asyncio
async def test_refresh_failed_bid_does_not_preempt_a_healthy_current_bid():
    listing_id = _context()[3].id
    failed = _quote_result(listing_id=listing_id)
    failed = replace(failed, data=replace(failed.data, refresh_error="FRANKFURT_HTTP_503"))
    good = _quote_result(listing_id=listing_id)
    _, _, _, request, _ = context()
    request = replace(request, warrant_listing_id=listing_id)
    result = await MultiSourceWarrantQuoteResolver(
        (
            NamedWarrantQuoteSource("CACHED", _Provider(failed)),
            NamedWarrantQuoteSource("HEALTHY", _Provider(good)),
        )
    ).resolve(request)
    assert result.selected_source == "HEALTHY"
    assert result.attempts[0].refresh_error == "FRANKFURT_HTTP_503"
