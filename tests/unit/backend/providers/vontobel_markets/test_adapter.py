import json
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID

import httpx
import pytest

from app.core.config.settings import VontobelMarketsSettings
from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.service.errors import (
    MarketDataConfigurationError,
    MarketDataInvalidResponseError,
)
from app.features.market_data.service.types import WarrantQuoteRequest
from app.providers.vontobel_markets.adapter import (
    VontobelMarketsWarrantQuoteAdapter,
    _Identity,
)

LISTING_ID = UUID("00000000-0000-4000-8000-000000000123")


def _adapter() -> VontobelMarketsWarrantQuoteAdapter:
    return VontobelMarketsWarrantQuoteAdapter(
        database=object(),  # type: ignore[arg-type]
        settings=VontobelMarketsSettings(enabled=True),
    )


def _identity() -> _Identity:
    return _Identity(
        listing_id=LISTING_ID,
        isin="DE000VH2LU21",
        wkn="VH2LU2",
        currency="EUR",
        provider_symbol="DE000VH2LU21",
        provider_exchange_code="ISSUER",
    )


def _html(*, isin: str = "DE000VH2LU21", bid: object = 0.24, ask: object = 0.25) -> str:
    data = {
        "props": {
            "pageProps": {
                "data": {
                    "additionalData": {
                        "data": {
                            "isin": isin,
                            "identifiers": [
                                {"type": 0, "value": isin},
                                {"type": 2, "value": "VH2LU2"},
                            ],
                            "price": {
                                "bid": bid,
                                "ask": ask,
                                "latestTimestamp": "2026-09-11T19:59:13+00:00",
                                "currency": "EUR",
                            },
                            "tradingHours": {"isOpen": False},
                        }
                    }
                }
            }
        }
    }
    payload = json.dumps(data)
    return f'<html><script id="__NEXT_DATA__" type="application/json">{payload}</script></html>'


def test_parses_exact_official_issuer_quote_with_provenance() -> None:
    quote = _adapter()._parse(_html(), _identity())

    assert quote is not None
    assert quote.warrant_listing_id == LISTING_ID
    assert quote.bid == Decimal("0.24")
    assert quote.ask == Decimal("0.25")
    assert quote.observed_at == datetime(2026, 9, 11, 19, 59, 13, tzinfo=UTC)
    assert quote.provider_symbol == "DE000VH2LU21"
    assert quote.provider_exchange_code == "ISSUER"
    assert quote.isin == "DE000VH2LU21"
    assert quote.wkn == "VH2LU2"
    assert quote.source_mode == "OFFICIAL_ISSUER_INDICATION"
    assert quote.trading_status == "CLOSED"


def test_rejects_payload_for_another_isin() -> None:
    with pytest.raises(MarketDataInvalidResponseError, match="ISIN does not match"):
        _adapter()._parse(_html(isin="DE000OTHER00"), _identity())


@pytest.mark.parametrize(("bid", "ask"), [(0, 0.25), (0.24, -1), ("bad", 0.25)])
def test_rejects_semantically_invalid_quote_sides(bid: object, ask: object) -> None:
    with pytest.raises(MarketDataInvalidResponseError):
        _adapter()._parse(_html(bid=bid, ask=ask), _identity())


def test_rejects_unknown_structured_schema() -> None:
    html = '<script id="__NEXT_DATA__" type="application/json">{"props": {}}</script>'

    with pytest.raises(MarketDataInvalidResponseError, match="unknown schema"):
        _adapter()._parse(html, _identity())


def test_rejects_missing_payload_and_identity_fields() -> None:
    with pytest.raises(MarketDataInvalidResponseError, match="no structured"):
        _adapter()._parse("<html></html>", _identity())

    with pytest.raises(MarketDataInvalidResponseError, match="identifiers"):
        payload = _html().replace('"value": "VH2LU2"', '"value": "OTHER"')
        _adapter()._parse(payload, _identity())


def test_returns_none_without_any_quote_side() -> None:
    assert _adapter()._parse(_html(bid=None, ask=None), _identity()) is None


@pytest.mark.asyncio
async def test_get_quote_calls_exact_official_url_and_preserves_provider() -> None:
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        return httpx.Response(200, text=_html(), request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    adapter = VontobelMarketsWarrantQuoteAdapter(
        database=object(),  # type: ignore[arg-type]
        settings=VontobelMarketsSettings(enabled=True),
        client=client,
    )
    adapter._resolve_identity = AsyncMock(return_value=_identity())  # type: ignore[method-assign]
    request = WarrantQuoteRequest(
        workspace_id=UUID("00000000-0000-4000-8000-000000000001"),
        warrant_listing_id=LISTING_ID,
        correlation_id=UUID("00000000-0000-4000-8000-000000000002"),
        as_of=datetime.now(UTC),
    )

    result = await adapter.get_warrant_listing_quote(request)
    await client.aclose()

    assert requested_urls == [
        "https://markets.vontobel.com/de-de/produkte/hebel/optionsscheine/DE000VH2LU21"
    ]
    assert result.provider is MarketDataProvider.VONTOBEL_MARKETS
    assert result.data is not None
    assert "official_product_page_structured_payload" in result.warnings[1]


@pytest.mark.asyncio
async def test_disabled_provider_fails_closed() -> None:
    adapter = VontobelMarketsWarrantQuoteAdapter(
        database=object(),  # type: ignore[arg-type]
        settings=VontobelMarketsSettings(enabled=False),
    )
    request = WarrantQuoteRequest(
        workspace_id=UUID("00000000-0000-4000-8000-000000000001"),
        warrant_listing_id=LISTING_ID,
        correlation_id=UUID("00000000-0000-4000-8000-000000000002"),
        as_of=datetime.now(UTC),
    )

    with pytest.raises(MarketDataConfigurationError, match="disabled"):
        await adapter.get_warrant_listing_quote(request)
