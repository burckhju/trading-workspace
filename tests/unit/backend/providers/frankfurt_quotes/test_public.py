import asyncio
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import httpx
import pytest

from app.core.config.frankfurt import FrankfurtQuoteSettings
from app.features.market_data.service.errors import MarketDataMappingError
from app.features.position_monitoring.service.quote_sources import (
    MultiSourceWarrantQuoteResolver,
    NamedWarrantQuoteSource,
)
from app.providers.frankfurt_quotes.client import FrankfurtSnapshotClient
from app.providers.frankfurt_quotes.public import FrankfurtPublicPrice, assess_public_price
from app.providers.frankfurt_quotes.schema import FrankfurtSourceError
from tests.unit.backend.providers.frankfurt_quotes.test_adapter_api import context
from tests.unit.backend.providers.frankfurt_quotes.test_schema import NOW


def public_settings(**changes):
    return FrankfurtQuoteSettings(
        **{
            "enabled": True,
            "usage_approved": True,
            "contract_verified": True,
            "source_mode": "public_website",
            "source_name": "deutsche-boerse-public",
            **changes,
        }
    )


def wire(**changes):
    # The observed wire field names, with controlled test prices/timestamps.
    return {
        "isin": "DE000VH2LU21",
        "mic": "XSC",
        "currency": {"originalValue": "EUR", "translations": {"others": "Euro"}},
        "lastPrice": "0.231",
        "timestampLastPrice": (NOW - timedelta(seconds=10)).isoformat(),
        "minimumTradableUnit": 1,
        "turnoverInPieces": 1234,
        "tradingTimeStart": "08:00:00",
        "tradingTimeEnd": "22:00:00",
        **changes,
    }


def assess(**changes):
    return assess_public_price(
        FrankfurtPublicPrice.model_validate(wire(**changes)),
        isin="DE000VH2LU21",
        currency="EUR",
        now=NOW,
        retrieved_at=NOW,
        max_age_seconds=900,
    )


def test_public_last_trade_provenance_never_invents_bid_delay_status_or_wkn():
    item = assess()
    assert item.status == "INSUFFICIENT"
    assert item.reason == "FRANKFURT_POST_TRADE_ONLY"
    assert item.provider_exchange_code == "XSC"
    assert item.mic == "XFRA"
    assert item.record.last_price == Decimal("0.231")
    assert item.record.bid is item.record.ask is item.record.wkn is None
    assert item.record.bid_size is item.record.ask_size is None
    assert item.record.trading_status == "UNKNOWN"
    assert item.declared_delay_seconds is item.snapshot_generated_at is None
    assert item.age_seconds == 10
    assert item.execution_usable is False


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"isin": "US91324P1021"}, "ISIN_MISMATCH"),
        ({"currency": {"originalValue": "USD"}}, "CURRENCY_MISMATCH"),
        (
            {"timestampLastPrice": (NOW + timedelta(seconds=1)).isoformat()},
            "TIMESTAMP_INCONSISTENT",
        ),
        ({"timestampLastPrice": (NOW - timedelta(seconds=901)).isoformat()}, "LAST_TRADE_STALE"),
        ({"timestampLastPrice": None}, "LAST_TRADE_MISSING"),
        ({"lastPrice": None}, "LAST_TRADE_MISSING"),
    ],
)
def test_public_semantic_failures(changes, reason):
    item = assess(**changes)
    assert item.reason == f"FRANKFURT_{reason}"
    assert item.status != "AVAILABLE"
    if item.status == "ERROR":
        assert item.record is None


@pytest.mark.asyncio
async def test_public_transport_exact_identifier_no_credentials_and_global_rate_limit():
    calls = []
    timer = [0.0]

    async def handler(request):
        calls.append(request)
        await asyncio.sleep(0)
        assert request.url.host == "api.live.deutsche-boerse.com"
        assert request.url.path == "/v1/data/price_information/single"
        assert dict(request.url.params) == {"isin": request.url.params["isin"], "mic": "XSC"}
        assert "authorization" not in request.headers
        return httpx.Response(200, json=wire(isin=request.url.params["isin"]))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = FrankfurtSnapshotClient(
            public_settings(), client=http, clock=lambda: NOW, timer=lambda: timer[0]
        )
        results = await asyncio.gather(*(client.load_public("DE000VH2LU21") for _ in range(5)))
        assert len(calls) == 1
        assert sum(not result[2] for result in results) == 1
        with pytest.raises(FrankfurtSourceError, match="REQUEST_THROTTLED"):
            await client.load_public("DE000VH7S657")
        timer[0] = 15
        second = await client.load_public("DE000VH7S657")
        assert second[0].isin == "DE000VH7S657"
        assert len(calls) == 2
        with pytest.raises(FrankfurtSourceError, match="REQUEST_THROTTLED"):
            await client.load_public("DE000VH2LU21")
        assert len(calls) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data,reason",
    [
        ({}, "PUBLIC_EMPTY_RESPONSE"),
        ([], "SCHEMA_INVALID"),
        (wire(isin="US91324P1021"), "ISIN_MISMATCH"),
        (wire(mic="XETR"), "SCHEMA_INVALID"),
        (wire(lastPrice="NaN"), "SCHEMA_INVALID"),
        (wire(lastPrice="0"), "SCHEMA_INVALID"),
        (wire(timestampLastPrice="2026-09-11T10:00:00"), "SCHEMA_INVALID"),
    ],
)
async def test_public_bad_responses_fail_closed_and_back_off(data, reason):
    handler = AsyncMock(return_value=httpx.Response(200, json=data))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = FrankfurtSnapshotClient(public_settings(), client=http)
        for _ in range(2):
            with pytest.raises(FrankfurtSourceError, match=f"FRANKFURT_{reason}"):
                await client.load_public("DE000VH2LU21")
        assert handler.await_count == 1
        assert client.last_success_at is None


@pytest.mark.asyncio
async def test_public_gates_and_identifier_validation_before_network():
    for change, reason in [
        ({"enabled": False}, "DISABLED"),
        ({"usage_approved": False}, "USAGE_NOT_APPROVED"),
        ({"contract_verified": False}, "CONTRACT_NOT_VERIFIED"),
        ({"source_name": "wrong"}, "SOURCE_MISMATCH"),
        ({"bearer_token": "SECRET"}, "PUBLIC_CONFIGURATION_CONFLICT"),
        ({"snapshot_url": "https://other.example/"}, "PUBLIC_CONFIGURATION_CONFLICT"),
    ]:
        client = FrankfurtSnapshotClient(public_settings(**change))
        with pytest.raises(FrankfurtSourceError, match=reason):
            await client.load_public("DE000VH2LU21")
    client = FrankfurtSnapshotClient(public_settings())
    with pytest.raises(FrankfurtSourceError, match="ISIN_REQUIRED"):
        await client.load()
    with pytest.raises(FrankfurtSourceError, match="ISIN_INVALID"):
        await client.load_public("DE000VH2LU21&mic=XETR")


@pytest.mark.asyncio
async def test_public_mapping_and_last_trade_fallback_through_existing_port():
    adapter, _database, snapshots, request, row = context()
    adapter.settings = public_settings()
    snapshots.load_public = AsyncMock(
        return_value=(FrankfurtPublicPrice.model_validate(wire()), NOW, False)
    )
    # XFRA is a listing MIC, not the website's provider instrument exchange code.
    with pytest.raises(MarketDataMappingError):
        await adapter.inspect(request)
    snapshots.load_public.assert_not_awaited()
    row[2].provider_exchange_code = "XSC"
    value = await adapter.get_warrant_listing_quote(request)
    assert value.data is None
    assert value.reason_code == "FRANKFURT_POST_TRADE_ONLY"
    snapshots.load.assert_not_awaited()
    secondary, *_rest = context()
    resolver = MultiSourceWarrantQuoteResolver(
        (
            NamedWarrantQuoteSource("FRANKFURT_QUOTES", adapter),
            NamedWarrantQuoteSource("FALLBACK", secondary),
        )
    )
    result = await resolver.resolve(request)
    assert result.selected_source == "FALLBACK"
    assert result.attempts[0].reason == "FRANKFURT_POST_TRADE_ONLY"
    assert result.attempts[0].bid_available is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode", ["FRANKFURT_REALTIME_MONITORING", "FRANKFURT_DELAYED_MONITORING", None]
)
async def test_frankfurt_fresh_bid_ask_valuation_still_never_permits_execution(mode):
    from app.features.market_data.domain.enums import MarketDataProvider
    from app.features.position_monitoring.service.product_valuation import (
        ProductPositionValuationService,
    )
    from tests.unit.backend.features.position_monitoring.test_product_valuation import (
        _context,
        _Database,
        _Provider,
        _quote_result,
        _Session,
    )

    trade, position, evaluation, listing = _context()
    value = replace(
        _quote_result(listing_id=listing.id, trading_status="OPEN", source_mode=mode),
        provider=MarketDataProvider.FRANKFURT_QUOTES,
    )
    service = ProductPositionValuationService(
        database=_Database(
            _Session(trade=trade, position=position, evaluation=evaluation, listing=listing)
        ),
        quote_provider=_Provider(value),
    )
    result = await service.for_trade(trade.id)
    assert result.status == "AVAILABLE"
    assert result.valuation_usable is result.analysis_usable is True
    assert result.market_value == Decimal("25.00")
    assert result.execution_usable is False
