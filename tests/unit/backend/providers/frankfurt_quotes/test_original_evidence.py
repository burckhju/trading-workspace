"""Synthetic normalized-source evidence; no claim about a live Frankfurt feed."""

from datetime import timedelta

import pytest

from app.providers.frankfurt_quotes.schema import QuoteStatus
from tests.unit.backend.providers.frankfurt_quotes.test_adapter_api import context
from tests.unit.backend.providers.frankfurt_quotes.test_schema import NOW, assess, payload


@pytest.mark.asyncio
async def test_adapter_preserves_exact_side_text_source_and_prices_without_changing_min_clock():
    data = payload()
    data["records"][0].update(bid_at="2026-09-11T14:00:00+02:00", ask_at="2026-09-11T11:59:59Z")
    adapter, _database, _snapshots, request, _row = context(data)
    result = await adapter.get_warrant_listing_quote(request)
    quote = result.data
    original = quote.original_evidence
    assert quote.observed_at == NOW - timedelta(seconds=1)
    assert original.version == "original-quote-evidence-v1"
    assert original.source_contract == data["schema_version"]
    assert original.source_reference == data["source"]
    assert original.generated_at == NOW
    assert original.isin == quote.isin == quote.provider_symbol
    assert original.currency == quote.currency == "EUR"
    assert original.venue_mic == quote.venue_mic == "XFRA"
    assert original.bid.price == quote.bid
    assert original.ask.price == quote.ask
    assert original.bid.observed_at == NOW
    assert original.ask.observed_at == quote.observed_at
    assert original.bid.original_time_text == "2026-09-11T14:00:00+02:00"
    assert original.ask.original_time_text == "2026-09-11T11:59:59Z"
    assert original.bid.source_field == "bid_at"
    assert original.ask.source_field == "ask_at"
    assert original.bid.time_basis == original.ask.time_basis == "SEPARATE_SIDE_TIMESTAMP"


@pytest.mark.parametrize("field", ["bid_at", "ask_at"])
def test_missing_side_or_original_text_never_infers_from_other_clock(field):
    data = payload()
    data["records"][0][field] = None
    assert assess(data).original_evidence is None
    data["records"][0][field] = NOW
    result = assess(data)
    assert result.status is QuoteStatus.AVAILABLE
    assert result.original_evidence is None


@pytest.mark.parametrize(
    "kind,price_field,time_field",
    [
        ("LAST_TRADE", "last_price", "last_at"),
        ("PREVIOUS_CLOSE", "close_price", "close_at"),
    ],
)
@pytest.mark.asyncio
async def test_reference_prices_do_not_inherit_present_side_fields(kind, price_field, time_field):
    data = payload()
    data["records"][0].update(kind=kind, **{price_field: "0.34", time_field: NOW.isoformat()})
    adapter, _database, _snapshots, request, _row = context(data)
    quote = (await adapter.get_warrant_listing_quote(request)).data
    assert quote.bid is quote.ask is quote.original_evidence is None
    assert quote.reference_price_type == kind


@pytest.mark.parametrize("change", ["currency", "identity", "future", "duplicate"])
def test_rejected_source_never_attaches_side_evidence(change):
    data = payload()
    if change == "currency":
        data["records"][0]["currency"] = "USD"
    elif change == "identity":
        data["records"][0]["isin"] = "DE000VH7S657"
    elif change == "future":
        data["records"][0]["bid_at"] = (NOW + timedelta(seconds=1)).isoformat()
    else:
        data["records"].append(dict(data["records"][0]))
    result = assess(data)
    assert result.status is not QuoteStatus.AVAILABLE
    assert result.original_evidence is None


def test_stale_evidence_remains_original_without_becoming_fresh():
    data = payload()
    old = NOW - timedelta(seconds=901)
    data["records"][0]["bid_at"] = old.isoformat()
    result = assess(data)
    assert result.status is QuoteStatus.STALE
    assert result.original_evidence.bid.observed_at == old
    assert result.observed_at == old
