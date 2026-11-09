"""ETF setup requires corroborated identities, exact venues and shared provider limits."""

import asyncio
from datetime import date
from unittest.mock import AsyncMock

import pytest
from tests.unit.backend.providers.eodhd.test_adapter import make_adapter
from tests.unit.backend.providers.eodhd.test_stock_catalog import EXCHANGES

from app.features.market_data.service.errors import (
    MarketDataBudgetExhaustedError,
    MarketDataInvalidResponseError,
)

IDENTITY = {
    "isin": "US0000000001",
    "currency": "USD",
    "mic": "ARCX",
    "listing_ticker": "EXAMPLE",
    "listing_source_url": "https://issuer.example/etf",
    "listing_reviewed_on": date(2026, 8, 1),
    "venue_source_url": "https://exchange.example/listing",
}


def etf(**changes):
    return {
        "Code": "EXAMPLE",
        "Exchange": "NYSE ARCA",
        "Isin": IDENTITY["isin"],
        "Currency": "USD",
        "Type": "ETF",
        **changes,
    }


def catalog(rows=None, search=None):
    adapter, client, _ = make_adapter()
    payloads = {
        "/exchanges-list/": EXCHANGES,
        "/exchange-symbol-list/US": [etf()] if rows is None else rows,
        f"/search/{IDENTITY['isin']}": [] if search is None else search,
    }
    client.get_json = AsyncMock(side_effect=lambda path, **_: payloads[path])
    return adapter, client, payloads


@pytest.mark.asyncio
@pytest.mark.parametrize("mic,venue", [("ARCX", "NYSE ARCA"), ("XNMS", "NASDAQ")])
async def test_exact_etf_combines_live_provider_and_reviewed_segment_evidence(mic, venue):
    adapter, client, _ = catalog([etf(Exchange=venue)])
    proof = await adapter.etf_catalog.verify(**{**IDENTITY, "mic": mic})
    assert proof.item.provider_symbol == "EXAMPLE"
    assert proof.item.provider_exchange_code == "US"
    assert proof.item.isin == IDENTITY["isin"]
    assert proof.mic == mic and proof.provider_venue == venue
    assert proof.venue_source_url == IDENTITY["venue_source_url"]
    assert client.get_json.call_args_list[1].kwargs["params"] == {"type": "etf"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "rows",
    [
        [etf(Currency="EUR")],
        [etf(Type="FUND")],
        [etf(Type="ETC")],
        [etf(Exchange="NASDAQ")],
        [etf(Exchange="US")],
        [etf(), etf(Currency="EUR")],
        [etf(), etf(Isin="US0000000002")],
        [etf(), etf(Code="OTHER")],
        [etf(Code="../bad?token")],
        [etf(Code="OTHER")],
    ],
)
async def test_never_substitutes_fund_currency_venue_or_conflicting_identity(rows):
    adapter, _, _ = catalog(rows)
    with pytest.raises(ValueError, match="EODHD_"):
        await adapter.etf_catalog.verify(**IDENTITY)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes",
    [
        {"mic": "XNAS"},
        {"listing_source_url": "http://issuer.example/etf"},
        {"venue_source_url": ""},
        {"listing_reviewed_on": date(2027, 1, 1)},
    ],
)
async def test_missing_reviewed_segment_evidence_never_calls_provider(changes):
    adapter, client, _ = catalog()
    with pytest.raises(ValueError, match="ETF_REVIEWED_LISTING_EVIDENCE_REQUIRED"):
        await adapter.etf_catalog.verify(**{**IDENTITY, **changes})
    client.get_json.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "catalog_isin,search_isin,ok",
    [
        (None, "US0000000001", True),
        ("", "US0000000001", True),
        ("US0000000002", "US0000000001", False),
        (None, None, False),
        (None, "US0000000002", False),
    ],
)
async def test_only_exact_isin_search_fills_missing_catalog_isin(catalog_isin, search_isin, ok):
    search = [
        {
            "Code": "EXAMPLE",
            "Exchange": "US",
            "ISIN": search_isin,
            "Currency": "USD",
            "Type": "ETF",
        }
    ]
    adapter, _, _ = catalog([etf(Isin=catalog_isin)], search)
    if ok:
        proof = await adapter.etf_catalog.verify(**IDENTITY)
        assert proof.search_endpoint == f"/search/{IDENTITY['isin']}"
        assert proof.search_retrieved_at is not None
    else:
        with pytest.raises(ValueError):
            await adapter.etf_catalog.verify(**IDENTITY)


@pytest.mark.asyncio
async def test_shared_catalog_is_single_flight_cached_and_respects_budget():
    adapter, client, _ = catalog()
    proofs = await asyncio.gather(*(adapter.etf_catalog.verify(**IDENTITY) for _ in range(4)))
    assert all(proof == proofs[0] for proof in proofs)
    assert client.get_json.await_count == 2
    adapter._clock.mono += 24 * 3600
    await adapter.etf_catalog.verify(**IDENTITY)
    assert client.get_json.await_count == 4
    assert await adapter._budget.usage() == 4
    adapter._clock.mono += 24 * 3600
    await adapter._budget.synchronize_usage(100, usage_day=adapter._clock.utcnow().date())
    with pytest.raises(MarketDataBudgetExhaustedError):
        await adapter.etf_catalog.verify(**IDENTITY)
    assert client.get_json.await_count == 4


@pytest.mark.asyncio
async def test_malformed_provider_catalog_is_not_cached():
    adapter, client, payloads = catalog({"message": "bad"})
    with pytest.raises(MarketDataInvalidResponseError):
        await adapter.etf_catalog.verify(**IDENTITY)
    payloads["/exchange-symbol-list/US"] = [etf()]
    assert (await adapter.etf_catalog.verify(**IDENTITY)).item.isin == IDENTITY["isin"]
    assert client.get_json.await_count == 3


def search_hit(**changes):
    return {
        "Code": "EXAMPLE",
        "Exchange": "US",
        "ISIN": IDENTITY["isin"],
        "Currency": "USD",
        "Type": "ETF",
        **changes,
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exchanges,mic",
    [
        ([{"Code": "OTHER", "OperatingMIC": "XNYS,XNAS"}], "ARCX"),
        ([{"Code": "US", "OperatingMIC": "XNAS"}], "ARCX"),
        ([{"Code": "US", "OperatingMIC": "XNYS"}], "XNMS"),
        ([{"Code": "US", "OperatingMIC": "ARCX"}], "ARCX"),
        ([{"Code": "US", "OperatingMIC": "XNMS"}], "XNMS"),
        ([*EXCHANGES, {"Code": "US", "OperatingMIC": "XNYS,XNAS"}], "ARCX"),
    ],
)
async def test_missing_or_ambiguous_operating_venue_stops_before_symbol_lookup(exchanges, mic):
    adapter, client, payloads = catalog()
    payloads["/exchanges-list/"] = exchanges
    with pytest.raises(ValueError, match="EODHD_ETF_OPERATING_VENUE_NOT_VERIFIED"):
        await adapter.etf_catalog.verify(**{**IDENTITY, "mic": mic})
    assert [call.args[0] for call in client.get_json.call_args_list] == ["/exchanges-list/"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes",
    [
        {"Currency": None},
        {"Currency": ""},
        {"Currency": "EUR"},
        {"Type": None},
        {"Type": ""},
        {"Type": "FUND"},
        {"Type": "ETC"},
        {"Type": "Common Stock"},
        {"Exchange": "US"},
        {"Exchange": "NYSE"},
        {"Exchange": "NASDAQ"},
    ],
)
async def test_search_cannot_fill_missing_catalog_currency_type_or_listing_venue(
    changes,
):
    adapter, _, _ = catalog([etf(Isin=None, **changes)], [search_hit()])
    with pytest.raises(ValueError, match="EODHD_ETF_CATALOG_IDENTITY_CONFLICT"):
        await adapter.etf_catalog.verify(**IDENTITY)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "hits",
    [
        [search_hit(Currency=None)],
        [search_hit(Currency="EUR")],
        [search_hit(Type="FUND")],
        [search_hit(Type=None)],
        [search_hit(Exchange="NYSE ARCA")],
        [search_hit(ISIN=IDENTITY["isin"] + "0")],
        [search_hit(), search_hit(ISIN="US0000000002")],
        [search_hit(), search_hit(Currency="EUR")],
        [search_hit(), search_hit(Code="ANOTHER")],
    ],
)
async def test_search_suggestions_never_override_exact_identity_or_conflicting_duplicates(
    hits,
):
    adapter, _, _ = catalog([etf(Isin=None)], hits)
    with pytest.raises(ValueError, match="EODHD_ETF_"):
        await adapter.etf_catalog.verify(**IDENTITY)


@pytest.mark.asyncio
async def test_identical_duplicate_rows_do_not_create_another_identity_or_call_search():
    adapter, client, _ = catalog([etf(), etf()])
    proof = await adapter.etf_catalog.verify(**IDENTITY)
    assert proof.item.provider_symbol == "EXAMPLE"
    assert proof.search_endpoint is None and proof.search_retrieved_at is None
    assert [call.args[0] for call in client.get_json.call_args_list] == [
        "/exchanges-list/",
        "/exchange-symbol-list/US",
    ]


@pytest.mark.asyncio
async def test_one_shared_snapshot_keeps_two_reviewed_segments_and_identities_separate():
    second_isin = "US0000000002"
    adapter, client, _ = catalog(
        [etf(), etf(Code="NASDAQ_FUND", Isin=second_isin, Exchange="NASDAQ")]
    )
    first, second = await asyncio.gather(
        adapter.etf_catalog.verify(**IDENTITY),
        adapter.etf_catalog.verify(
            **{
                **IDENTITY,
                "isin": second_isin,
                "mic": "XNMS",
                "listing_ticker": "NASDAQ_FUND",
            }
        ),
    )
    assert (first.item.isin, first.mic, first.provider_venue) == (
        IDENTITY["isin"],
        "ARCX",
        "NYSE ARCA",
    )
    assert (second.item.isin, second.mic, second.provider_venue) == (
        second_isin,
        "XNMS",
        "NASDAQ",
    )
    assert first.catalog_retrieved_at == second.catalog_retrieved_at
    assert client.get_json.await_count == 2
    assert await adapter._budget.usage() == 2


@pytest.mark.asyncio
async def test_reaching_search_limit_is_not_a_unique_identity_proof():
    hits = [search_hit(Code=f"UNRELATED_{index}", ISIN="US0000000002") for index in range(499)] + [
        search_hit()
    ]
    adapter, client, _ = catalog([etf(Isin=None)], hits)
    with pytest.raises(ValueError, match="EODHD_SEARCH_RESULT_LIMIT_REACHED"):
        await adapter.etf_catalog.verify(**IDENTITY)
    assert client.get_json.call_args.kwargs["params"] == {"limit": 500}


@pytest.mark.asyncio
async def test_malformed_search_is_not_cached_or_replaced_with_the_reviewed_ticker():
    adapter, client, payloads = catalog([etf(Isin=None)], {"message": "unavailable"})
    with pytest.raises(MarketDataInvalidResponseError):
        await adapter.etf_catalog.verify(**IDENTITY)
    payloads[f"/search/{IDENTITY['isin']}"] = [search_hit()]
    proof = await adapter.etf_catalog.verify(**IDENTITY)
    assert proof.item.isin == IDENTITY["isin"]
    assert proof.search_endpoint == f"/search/{IDENTITY['isin']}"
    assert client.get_json.await_count == 4
    assert await adapter._budget.usage() == 4
