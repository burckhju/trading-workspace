"""Official catalog identity, US venue specificity, caching and quota regressions."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from tests.unit.backend.providers.eodhd.test_adapter import make_adapter

from app.features.market_data.service.errors import (
    MarketDataBudgetExhaustedError,
    MarketDataInvalidResponseError,
)

EXCHANGES = [
    {"Code": "US", "OperatingMIC": "XNAS, XNYS, OTCM, XCBO"},
    {"Code": "PA", "OperatingMIC": "XPAR"},
    {"Code": "SW", "OperatingMIC": "XSWX"},
]


def stock(**changes):
    return {
        "Code": "EXAMPLE",
        "Exchange": "NASDAQ",
        "Isin": "US0000000001",
        "Currency": "USD",
        "Type": "Common Stock",
        **changes,
    }


def catalog(rows=None, exchanges=None):
    adapter, client, _mapping = make_adapter()
    payloads = {
        "/exchanges-list/": EXCHANGES if exchanges is None else exchanges,
        "/exchange-symbol-list/NASDAQ": [stock()] if rows is None else rows,
    }
    client.get_json = AsyncMock(side_effect=lambda path, **_: payloads[path])
    return adapter, client, payloads


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mic,label,code,currency",
    [
        ("XNAS", "NASDAQ", "US", "USD"),
        ("XNYS", "NYSE", "US", "USD"),
        ("XPAR", "PA", "PA", "EUR"),
        ("XSWX", "SW", "SW", "CHF"),
    ],
)
async def test_bootstrap_exact_stock_without_prior_workspace_mappings(mic, label, code, currency):
    adapter, client, payloads = catalog()
    payloads[f"/exchange-symbol-list/{label}"] = [stock(Exchange=label, Currency=currency)]
    found = await adapter.stock_catalog.discover(isin="US0000000001", currency=currency, mic=mic)
    assert found.reason == "EODHD_CATALOG_IDENTITY_VERIFIED"
    assert found.identity.item.provider_exchange_code == code
    assert found.identity.item.provider_symbol == "EXAMPLE"
    assert found.identity.mic == mic
    assert found.identity.item.isin == "US0000000001"
    assert client.get_json.await_count == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"Isin": None}, "EODHD_ISIN_NOT_FOUND_ON_VENUE"),
        ({"Isin": "TW0000000001"}, "EODHD_ISIN_NOT_FOUND_ON_VENUE"),
        ({"Isin": "US0000000002"}, "EODHD_ISIN_NOT_FOUND_ON_VENUE"),
        ({"Currency": "EUR"}, "EODHD_LISTING_CURRENCY_MISMATCH"),
        ({"Type": "INDEX"}, "EODHD_STOCK_TYPE_REQUIRED"),
        ({"Type": "Warrant"}, "EODHD_STOCK_TYPE_REQUIRED"),
        ({"Exchange": "NYSE"}, "EODHD_INSTRUMENT_VENUE_MISMATCH"),
        ({"Exchange": "US"}, "EODHD_INSTRUMENT_VENUE_MISMATCH"),
        ({"Code": " "}, "EODHD_INSTRUMENT_VENUE_MISMATCH"),
        ({"Code": "../WRONG?query"}, "EODHD_PROVIDER_SYMBOL_UNSUPPORTED"),
    ],
)
async def test_never_substitute_currency_other_venue_adr_ordinary_share_or_instrument(
    changes, reason
):
    adapter, _, _ = catalog([stock(**changes)])
    found = await adapter.stock_catalog.discover(isin="US0000000001", currency="USD", mic="XNAS")
    assert found.identity is None and found.reason == reason


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "rows,reason",
    [
        ([], "EODHD_ISIN_NOT_FOUND_ON_VENUE"),
        ([stock(), stock(Code="OTHER")], "EODHD_STOCK_IDENTITY_AMBIGUOUS"),
        ([stock(), stock(Exchange="NYSE")], "EODHD_INSTRUMENT_VENUE_MISMATCH"),
        ([stock(), stock(Isin="US0000000002")], "EODHD_STOCK_IDENTITY_AMBIGUOUS"),
        ([stock(), stock(Currency="EUR")], "EODHD_STOCK_IDENTITY_AMBIGUOUS"),
    ],
)
async def test_empty_ambiguous_or_conflicting_rows_are_not_approved(rows, reason):
    adapter, _, _ = catalog(rows)
    result = await adapter.stock_catalog.discover(isin="US0000000001", currency="USD", mic="XNAS")
    assert result.reason == reason and result.identity is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exchanges,mic,reason",
    [
        (EXCHANGES, "XETR", "EODHD_VENUE_NOT_IN_CATALOG"),
        (EXCHANGES, "XNMS", "EODHD_VENUE_NOT_IN_CATALOG"),
        (EXCHANGES, "OTCM", "EODHD_VENUE_DETAIL_UNSUPPORTED"),
        (
            [{"Code": "OTHER", "OperatingMIC": "XPAR,XSWX"}],
            "XPAR",
            "EODHD_VENUE_DETAIL_UNSUPPORTED",
        ),
        (
            [*EXCHANGES, {"Code": "OTHER", "OperatingMIC": "XNAS"}],
            "XNAS",
            "EODHD_VENUE_CATALOG_AMBIGUOUS",
        ),
        ([{"Code": "INDX", "OperatingMIC": None}], "XNAS", "EODHD_VENUE_NOT_IN_CATALOG"),
    ],
)
async def test_unsupported_or_ambiguous_venue_does_not_fetch_symbols(exchanges, mic, reason):
    adapter, client, _ = catalog(exchanges=exchanges)
    result = await adapter.stock_catalog.discover(isin="US0000000001", currency="USD", mic=mic)
    assert result.reason == reason and result.identity is None
    assert client.get_json.await_count == 1


@pytest.mark.asyncio
async def test_catalogs_single_flight_and_ttl_share_adapter_budget():
    adapter, client, _ = catalog()
    calls = [
        adapter.stock_catalog.discover(isin="US0000000001", currency="USD", mic="XNAS")
        for _ in range(4)
    ]
    results = await asyncio.gather(*calls)
    assert all(r.identity == results[0].identity for r in results)
    assert client.get_json.await_count == 2
    adapter._clock.mono += 24 * 3600
    await adapter.stock_catalog.discover(isin="US0000000001", currency="USD", mic="XNAS")
    assert client.get_json.await_count == 4
    assert await adapter._budget.usage() == 4
    # Both catalogs use the configured shared budget before any transport call.
    adapter._clock.mono += 24 * 3600
    await adapter._budget.synchronize_usage(100, usage_day=adapter._clock.utcnow().date())
    with pytest.raises(MarketDataBudgetExhaustedError):
        await adapter.stock_catalog.discover(isin="US0000000001", currency="USD", mic="XNAS")
    assert client.get_json.await_count == 4


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [{}, [], [{"Code": "US", "OperatingMIC": []}], [{"Code": "../US"}]])
async def test_invalid_exchange_catalog_not_cached(bad):
    adapter, client, payloads = catalog(exchanges=bad)
    with pytest.raises(MarketDataInvalidResponseError):
        await adapter.stock_catalog.discover(isin="US0000000001", currency="USD", mic="XNAS")
    payloads["/exchanges-list/"] = EXCHANGES
    assert (
        await adapter.stock_catalog.discover(isin="US0000000001", currency="USD", mic="XNAS")
    ).identity
    assert client.get_json.await_count == 3


@pytest.mark.asyncio
async def test_invalid_ticker_payload_fails_closed_and_can_recover():
    adapter, _, payloads = catalog()
    payloads["/exchange-symbol-list/NASDAQ"] = {}
    with pytest.raises(MarketDataInvalidResponseError):
        await adapter.stock_catalog.discover(isin="US0000000001", currency="USD", mic="XNAS")
    payloads["/exchange-symbol-list/NASDAQ"] = [stock()]
    assert (
        await adapter.stock_catalog.discover(isin="US0000000001", currency="USD", mic="XNAS")
    ).identity
