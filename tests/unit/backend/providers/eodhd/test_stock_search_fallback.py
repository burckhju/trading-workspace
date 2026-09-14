"""Sparse catalog ISINs require corroboration; foreign quotes cannot repair local rules."""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from tests.unit.backend.providers.eodhd.test_stock_catalog import catalog, stock

from app.features.market_data.service.errors import (
    MarketDataBudgetExhaustedError,
    MarketDataInvalidResponseError,
)

ISIN = "US0000000001"
QUERY = f"/search/{ISIN}"
EXCHANGES = [
    {"Code": "XETRA", "OperatingMIC": "XETR"},
    {"Code": "US", "OperatingMIC": "XNAS, XNYS"},
    {"Code": "PA", "OperatingMIC": "XPAR"},
]


def search(**changes):
    return dict(
        Code="LOCAL", Exchange="XETRA", ISIN=ISIN, Currency="EUR", Type="Common Stock", **changes
    )


def fixture():
    adapter, client, payloads = catalog(exchanges=EXCHANGES)
    payloads["/exchange-symbol-list/XETRA"] = [
        stock(Code="LOCAL", Exchange="XETRA", Currency="EUR", Isin=None)
    ]
    payloads[QUERY] = [search()]
    return adapter, client, payloads


async def discover(adapter):
    return await adapter.stock_catalog.discover_with_search(isin=ISIN, currency="EUR", mic="XETR")


@pytest.mark.asyncio
async def test_missing_catalog_isin_is_repaired_only_for_verified_current_venue_and_currency():
    adapter, client, _ = fixture()
    result = await discover(adapter)
    assert result.reason == "EODHD_SEARCH_CATALOG_IDENTITY_VERIFIED"
    proof = result.identity
    assert (proof.item.isin, proof.item.currency, proof.mic) == (ISIN, "EUR", "XETR")
    assert proof.item.provider_symbol == "LOCAL"
    assert proof.source == "EODHD_ISIN_SEARCH_AND_CATALOG"
    assert proof.search_endpoint == QUERY
    assert proof.search_retrieved_at == adapter._clock.utcnow()
    assert client.get_json.await_count == 3
    assert client.get_json.await_args.kwargs["params"] == {"limit": 500}
    assert await adapter._budget.usage() == 3


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes",
    [
        {"Isin": "US0000000002"},
        {"Isin": "TW0000000001"},
        {"Currency": "USD"},
        {"Type": "ETF"},
        {"Exchange": "US"},
        {"Code": "OTHER"},
    ],
)
async def test_search_cannot_override_conflicting_or_absent_catalog_symbol(changes):
    adapter, _, payloads = fixture()
    payloads["/exchange-symbol-list/XETRA"][0].update(changes)
    result = await discover(adapter)
    assert result.identity is None
    assert not any(a.identity for a in result.alternatives)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes",
    [
        {"ISIN": None},
        {"ISIN": "US0000000002"},
        {"ISIN": "TW0000000001"},
        {"Currency": "USD"},
        {"Currency": None},
        {"Type": "Index"},
        {"Type": "Warrant"},
        {"Code": "../WRONG?query"},
        {"Code": ""},
        {"Exchange": "UNKNOWN"},
    ],
)
async def test_search_requires_exact_stock_identity_and_catalog_corroboration(changes):
    adapter, _, payloads = fixture()
    payloads[QUERY][0].update(changes)
    assert (await discover(adapter)).identity is None


@pytest.mark.asyncio
async def test_us_composite_is_verified_per_subvenue_but_does_not_change_eur_rules():
    adapter, client, payloads = fixture()
    payloads[QUERY][0].update(Code="AMERICAN", Exchange="US", Currency="USD")
    payloads["/exchange-symbol-list/NASDAQ"] = [stock(Code="AMERICAN")]
    payloads["/exchange-symbol-list/NYSE"] = []
    result = await discover(adapter)
    assert result.identity is None
    verified = [a for a in result.alternatives if a.identity]
    assert len(verified) == 1
    assert (verified[0].mic, verified[0].currency, verified[0].provider_exchange_code) == (
        "XNAS",
        "USD",
        "US",
    )
    assert all(not c.args[0].startswith("/eod/") for c in client.get_json.await_args_list)


@pytest.mark.asyncio
async def test_same_currency_other_market_is_review_only():
    adapter, _, payloads = fixture()
    payloads[QUERY][0].update(Code="FRENCH", Exchange="PA")
    payloads["/exchange-symbol-list/PA"] = [stock(Code="FRENCH", Exchange="PA", Currency="EUR")]
    result = await discover(adapter)
    assert result.identity is None
    assert result.alternatives[0].identity.mic == "XPAR"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "conflict", ["search_isin", "search_currency", "search_type", "catalog", "symbol"]
)
async def test_duplicate_conflicting_identities_are_not_resolved_by_picking_good_row(conflict):
    adapter, _, payloads = fixture()
    if conflict == "catalog":
        payloads["/exchange-symbol-list/XETRA"].append(
            stock(Code="LOCAL", Exchange="XETRA", Currency="EUR", Isin="US0000000002")
        )
    elif conflict == "symbol":
        payloads[QUERY].append({**search(), "Code": "SECOND"})
        payloads["/exchange-symbol-list/XETRA"].append(
            stock(Code="SECOND", Exchange="XETRA", Currency="EUR", Isin=None)
        )
    else:
        changes = {
            "search_isin": {"ISIN": "OTHER"},
            "search_currency": {"Currency": "USD"},
            "search_type": {"Type": "ETF"},
        }[conflict]
        payloads[QUERY].append({**search(), **changes})
    assert (await discover(adapter)).identity is None


@pytest.mark.asyncio
async def test_invalid_candidate_cannot_hide_alongside_good_candidate_at_current_market():
    adapter, _, payloads = fixture()
    payloads[QUERY].append({**search(), "Code": "WRONG", "Type": "Index"})
    assert (await discover(adapter)).identity is None


@pytest.mark.asyncio
async def test_verified_current_listing_never_requests_other_market_catalogs():
    adapter, client, payloads = fixture()
    payloads[QUERY].extend({**search(), "Exchange": f"OTHER{i}"} for i in range(20))
    result = await discover(adapter)
    assert result.identity is not None
    assert client.get_json.await_count == 3


@pytest.mark.asyncio
async def test_search_single_flight_cache_expiry_and_empty_results_share_quota():
    adapter, client, payloads = fixture()
    payloads[QUERY] = []
    results = await asyncio.gather(*(discover(adapter) for _ in range(5)))
    assert all(r.search_reason == "EODHD_SEARCH_ISIN_NOT_FOUND" for r in results)
    assert client.get_json.await_count == 3
    adapter._clock.mono += 86400
    adapter._clock.now += timedelta(days=1)
    payloads[QUERY] = [search()]
    assert (await discover(adapter)).identity
    assert client.get_json.await_count == 6
    adapter._clock.mono += 86400
    await adapter._budget.synchronize_usage(100, usage_day=adapter._clock.utcnow().date())
    with pytest.raises(MarketDataBudgetExhaustedError):
        await discover(adapter)
    assert client.get_json.await_count == 6


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [{}, [{"Code": "MISSING_EXCHANGE"}]])
async def test_invalid_search_not_cached_or_used(bad):
    adapter, client, payloads = fixture()
    payloads[QUERY] = bad
    with pytest.raises(MarketDataInvalidResponseError):
        await discover(adapter)
    payloads[QUERY] = [search()]
    assert (await discover(adapter)).identity
    assert client.get_json.await_count == 4


@pytest.mark.asyncio
async def test_truncation_cannot_make_current_listing_look_unambiguous():
    adapter, client, payloads = fixture()
    payloads[QUERY] = [search()] * 500
    result = await discover(adapter)
    assert result.identity is None and result.search_reason == "EODHD_SEARCH_RESULT_LIMIT_REACHED"
    assert client.get_json.await_count == 3
    payloads[QUERY] = [{**search(), "Code": f"LOCAL{i}"} for i in range(13)]
    adapter._clock.mono += 86400
    result = await discover(adapter)
    assert (
        result.identity is None and result.search_reason == "EODHD_SEARCH_CANDIDATE_LIMIT_REACHED"
    )


@pytest.mark.asyncio
async def test_alternative_fanout_is_bounded_and_explicitly_partial():
    adapter, _, payloads = fixture()
    payloads[QUERY] = [{**search(), "Exchange": f"OTHER{i}"} for i in range(13)]
    result = await discover(adapter)
    assert result.identity is None
    assert result.search_reason == "EODHD_SEARCH_ALTERNATIVES_TRUNCATED"
    assert len(result.alternatives) == 12


@pytest.mark.asyncio
async def test_search_cache_has_bounded_instrument_count(monkeypatch):
    adapter, client, payloads = fixture()
    monkeypatch.setattr(type(adapter._rate_limiter), "acquire", AsyncMock())
    monkeypatch.setattr(type(adapter._budget), "consume", AsyncMock())
    client.get_json = AsyncMock(
        side_effect=lambda path, **_: [] if path.startswith("/search/") else payloads[path]
    )
    for number in range(257):
        await adapter.stock_catalog.discover_with_search(
            isin=f"US{number:010d}", currency="EUR", mic="XETR"
        )
    assert len(adapter.stock_catalog._search_keys) == 256
    assert len(adapter.stock_catalog._searches._entries) == 256
    assert not (await adapter.stock_catalog._searches.get("/search/US0000000000")).hit


@pytest.mark.asyncio
@pytest.mark.parametrize("changes", [{"Isin": ISIN}, {"Isin": ISIN, "Currency": "USD"}])
async def test_existing_catalog_match_or_currency_conflict_does_not_trigger_search(changes):
    adapter, client, payloads = fixture()
    payloads["/exchange-symbol-list/XETRA"][0].update(changes)
    await discover(adapter)
    assert client.get_json.await_count == 2
