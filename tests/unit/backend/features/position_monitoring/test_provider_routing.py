"""Exercise actual provider eligibility before transport, including alternate venues."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from tests.unit.backend.features.position_monitoring.test_cross_listing_product_valuation import (
    _Database,
    _Session,
)
from tests.unit.backend.providers.frankfurt_quotes.test_public import public_settings, wire
from tests.unit.backend.providers.frankfurt_quotes.test_schema import NOW
from tests.unit.backend.providers.stuttgart_delayed.test_stuttgart_delayed_adapter import _settings
from tests.unit.backend.providers.vontobel_markets.test_adapter import _html

from app.core.config.settings import VontobelMarketsSettings
from app.features.market_data.service.errors import MarketDataNotFoundError
from app.features.market_data.service.types import WarrantQuoteRequest
from app.features.position_monitoring.service.product_valuation import (
    ProductPositionValuationService,
)
from app.features.position_monitoring.service.quote_sources import (
    MultiSourceWarrantQuoteResolver,
    NamedWarrantQuoteSource,
)
from app.providers.frankfurt_quotes.adapter import FrankfurtWarrantQuoteAdapter
from app.providers.frankfurt_quotes.public import FrankfurtPublicPrice
from app.providers.stuttgart_delayed.adapter import StuttgartDelayedWarrantQuoteAdapter
from app.providers.vontobel_markets.adapter import VontobelMarketsWarrantQuoteAdapter


class RowsDatabase:
    def __init__(self, rows):
        self.rows = rows
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        params = statement.compile().params.values()
        row = next((row for key, row in self.rows.items() if key in params), None)
        return SimpleNamespace(one_or_none=lambda: row)

    @asynccontextmanager
    async def session_context(self):
        yield self


def listing():
    return SimpleNamespace(
        id=uuid4(), warrant_id=uuid4(), symbol=None, quotation_currency_code="EUR"
    )


def warrant(**changes):
    return SimpleNamespace(**{"isin": "DE000VH2LU21", "wkn": "VH2LU2", **changes})


def request(row):
    return WarrantQuoteRequest(uuid4(), row.id, uuid4(), NOW)


@pytest.mark.asyncio
async def test_absent_vontobel_mapping_is_skipped_without_http():
    row = listing()
    database = RowsDatabase({})
    http = SimpleNamespace(get=AsyncMock())
    adapter = VontobelMarketsWarrantQuoteAdapter(
        database=database, settings=VontobelMarketsSettings(enabled=True), client=http
    )
    with pytest.raises(MarketDataNotFoundError, match="VONTOBEL_ACTIVE_MAPPING_NOT_FOUND"):
        await adapter.get_warrant_listing_quote(request(row))
    resolver = MultiSourceWarrantQuoteResolver(
        (NamedWarrantQuoteSource("VONTOBEL_MARKETS", adapter),)
    )
    result = await resolver.resolve(request(row))
    assert result.result is None and result.attempts == ()
    http.get.assert_not_awaited()
    query = str(database.statements[0])
    for clause in (
        "warrant_listings.workspace_id",
        "warrant_provider_mappings.workspace_id",
        "warrant_provider_mappings.status",
        "warrant_listings.lifecycle_status",
    ):
        assert clause in query


@pytest.mark.asyncio
@pytest.mark.parametrize("mic", ["XFRA", "XETR", "MUND"])
async def test_other_venues_are_skipped_before_stuttgart_identifier_checks_or_feed_io(mic):
    row = listing()
    adapter = StuttgartDelayedWarrantQuoteAdapter(
        database=RowsDatabase({row.id: (row, warrant(isin=None), SimpleNamespace(mic=mic))}),
        settings=_settings(),
    )
    adapter._load_latest_payload = AsyncMock()
    with pytest.raises(MarketDataNotFoundError, match="STUTTGART_LISTING_VENUE_NOT_SUPPORTED"):
        await adapter.get_warrant_listing_quote(request(row))
    result = await MultiSourceWarrantQuoteResolver(
        (NamedWarrantQuoteSource("BOERSE_STUTTGART_DELAYED", adapter, delayed=True),)
    ).resolve(request(row))
    assert result.result is None and result.attempts == ()
    adapter._load_latest_payload.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mapping",
    [
        {"provider_symbol": "UNH", "provider_exchange_code": "ISSUER"},
        {"provider_symbol": "DE000VH2LU21", "provider_exchange_code": "XFRA"},
    ],
)
async def test_existing_inconsistent_vontobel_mapping_stays_visible_as_error(mapping):
    row = listing()
    http = SimpleNamespace(get=AsyncMock())
    adapter = VontobelMarketsWarrantQuoteAdapter(
        database=RowsDatabase({row.id: (row, warrant(), SimpleNamespace(**mapping))}),
        settings=VontobelMarketsSettings(enabled=True),
        client=http,
    )
    result = await MultiSourceWarrantQuoteResolver(
        (NamedWarrantQuoteSource("VONTOBEL_MARKETS", adapter),)
    ).resolve(request(row))
    assert result.result is None
    assert result.attempts[0].status == "ERROR"
    assert result.attempts[0].reason == "MarketDataMappingError"
    http.get.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("unresolved", [False, True])
async def test_invalid_xstu_identity_stays_visible_as_error(unresolved):
    row = listing()
    adapter = StuttgartDelayedWarrantQuoteAdapter(
        database=RowsDatabase(
            {}
            if unresolved
            else {
                row.id: (row, warrant(isin=None), SimpleNamespace(mic="XSTU")),
            }
        ),
        settings=_settings(),
    )
    adapter._load_latest_payload = AsyncMock()
    result = await MultiSourceWarrantQuoteResolver(
        (NamedWarrantQuoteSource("BOERSE_STUTTGART_DELAYED", adapter, delayed=True),)
    ).resolve(request(row))
    assert result.result is None
    assert result.attempts[0].status == "ERROR"
    assert result.attempts[0].reason == "MarketDataMappingError"
    adapter._load_latest_payload.assert_not_awaited()


@pytest.mark.asyncio
async def test_real_adapters_preserve_bid_and_frankfurt_alternative_without_routing_noise():
    historical, xstu, xfra = listing(), listing(), listing()
    xstu.warrant_id = xfra.warrant_id = historical.warrant_id
    product = warrant()
    issuer_mapping = SimpleNamespace(provider_symbol=product.isin, provider_exchange_code="ISSUER")
    frankfurt_mapping = SimpleNamespace(
        provider_symbol=product.isin, provider_exchange_code="XSC", validated_at=NOW
    )
    frankfurt_load = AsyncMock(
        return_value=(FrankfurtPublicPrice.model_validate(wire()), NOW, False)
    )
    frankfurt = FrankfurtWarrantQuoteAdapter(
        database=RowsDatabase(
            {xfra.id: (xfra, product, frankfurt_mapping, SimpleNamespace(mic="XFRA"))}
        ),
        settings=public_settings(),
        snapshots=SimpleNamespace(load_public=frankfurt_load),
        clock=lambda: NOW,
    )
    stuttgart = StuttgartDelayedWarrantQuoteAdapter(
        database=RowsDatabase(
            {
                xstu.id: (xstu, product, SimpleNamespace(mic="XSTU")),
                xfra.id: (xfra, product, SimpleNamespace(mic="XFRA")),
            }
        ),
        settings=_settings(),
    )
    stuttgart._load_latest_payload = AsyncMock(return_value=[])
    old_time = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    html = _html().replace("2026-09-11T19:59:13+00:00", old_time)
    handler = AsyncMock(return_value=httpx.Response(200, text=html))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        vontobel = VontobelMarketsWarrantQuoteAdapter(
            database=RowsDatabase({xstu.id: (xstu, product, issuer_mapping)}),
            settings=VontobelMarketsSettings(enabled=True),
            client=http,
        )
        trade = SimpleNamespace(id=uuid4(), workspace_id=uuid4(), product_evaluation_id=uuid4())
        position = SimpleNamespace(id=uuid4(), open_quantity=2000, cost_basis=Decimal("1020"))
        evaluation = SimpleNamespace(warrant_listing_id=historical.id)
        result = await ProductPositionValuationService(
            database=_Database(
                _Session(
                    trade=trade,
                    position=position,
                    evaluation=evaluation,
                    listing=historical,
                    siblings=[xstu, xfra],
                )
            ),
            quote_resolver=MultiSourceWarrantQuoteResolver(
                (
                    NamedWarrantQuoteSource("FRANKFURT_QUOTES", frankfurt),
                    NamedWarrantQuoteSource("VONTOBEL_MARKETS", vontobel),
                    NamedWarrantQuoteSource("BOERSE_STUTTGART_DELAYED", stuttgart, delayed=True),
                )
            ),
        ).for_trade(trade.id)
    assert result.selected_source == "VONTOBEL_MARKETS"
    assert result.analysis_market_value == Decimal("480")
    assert result.analysis_unrealized_gross_pnl == Decimal("-540")
    assert result.execution_usable is False
    assert result.provenance_listing_id == historical.id
    assert result.quote_listing_id == xstu.id
    assert [(a.source, a.status, a.warrant_listing_id) for a in result.source_attempts] == [
        ("VONTOBEL_MARKETS", "AVAILABLE", xstu.id),
        ("BOERSE_STUTTGART_DELAYED", "MISSING", xstu.id),
        ("FRANKFURT_QUOTES", "AVAILABLE", xfra.id),
    ]
    assert result.source_attempts[1].reason == "NO_QUOTE_RETURNED"
    assert result.source_attempts[2].reference_price == Decimal("0.231")
    assert result.source_attempts[2].reference_price_type == "LAST_TRADE"
    assert result.source_attempts[2].observed_at == NOW - timedelta(seconds=10)
    handler.assert_awaited_once()
    frankfurt_load.assert_awaited_once_with(product.isin)
    stuttgart._load_latest_payload.assert_awaited_once()
