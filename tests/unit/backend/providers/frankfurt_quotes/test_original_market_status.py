"""Synthetic extension of our normalized import, not a verified vendor status feed."""

from datetime import timedelta

import pytest

from app.features.market_data.domain.enums import QualityStatus
from app.providers.frankfurt_quotes.schema import FrankfurtSourceError, QuoteStatus
from tests.unit.backend.providers.frankfurt_quotes.test_adapter_api import context
from tests.unit.backend.providers.frankfurt_quotes.test_schema import (
    NOW,
    assess,
    payload,
)


def status_payload():
    data = payload()
    data["records"][0]["status_observed_at"] = "2026-09-11T13:59:30+02:00"
    return data


@pytest.mark.asyncio
async def test_adapter_transports_source_status_point_on_its_own_original_clock():
    data = status_payload()
    data["records"][0]["ask_at"] = "2026-09-11T11:59:50Z"
    adapter, _database, _snapshots, request, _row = context(data)
    result = await adapter.get_warrant_listing_quote(request)
    original = result.data.original_market_status
    assert original.status == original.original_status_text == result.data.trading_status == "OPEN"
    assert original.observed_at == NOW - timedelta(seconds=30)
    assert original.original_time_text == "2026-09-11T13:59:30+02:00"
    assert original.generated_at == NOW
    assert original.source_contract == data["schema_version"]
    assert original.source_reference == data["source"]
    assert original.source_status_field == "trading_status"
    assert original.source_time_field == "status_observed_at"
    assert original.isin == result.data.isin
    assert original.venue_mic == result.data.venue_mic == "XFRA"
    assert original.temporal_meaning == "OBSERVED_AT_INSTANT"
    assert original.time_basis == "SEPARATE_STATUS_TIMESTAMP"
    assert result.data.observed_at == NOW - timedelta(seconds=10)
    assert result.data.original_evidence.bid.observed_at == NOW


@pytest.mark.parametrize("missing", ["absent", "null", "status_absent"])
def test_absent_original_status_never_uses_price_or_generation_clock(missing):
    data = payload()
    if missing == "null":
        data["records"][0]["status_observed_at"] = None
    elif missing == "status_absent":
        data["records"][0]["status_observed_at"] = NOW.isoformat()
        data["records"][0].pop("trading_status")
    result = assess(data)
    assert result.original_market_status is None
    assert result.record.trading_status == ("UNKNOWN" if missing == "status_absent" else "OPEN")


@pytest.mark.parametrize(
    "raw",
    [
        NOW,
        NOW.timestamp(),
        int(NOW.timestamp()),
        True,
        "2026-09-11",
        "2026-09-11T12:00:00",
        "2026-09-11T12:00:00-00:00",
        "2026-09-11T12:00:00.0000001Z",
        "2026-09-11T12:00:00+24:00",
    ],
)
def test_present_status_clock_requires_actual_offset_aware_original_string(raw):
    data = status_payload()
    data["records"][0]["status_observed_at"] = raw
    with pytest.raises(FrankfurtSourceError, match="FRANKFURT_RECORD_INVALID"):
        assess(data)


@pytest.mark.parametrize(
    "raw",
    [
        "2026-09-11T14:00:00+01:60",
        "2026-09-11T13:39:00+00:99",
        "2026-09-11T10:00:00-01:60",
        "2026-09-11T10:21:00-00:99",
    ],
)
def test_normalized_input_rejects_offset_overflow_even_when_it_would_match_quote_clocks(raw):
    # Each invalid offset normalizes to NOW in Python, matching the generated
    # time and both quote clocks. It must still be rejected as original text.
    data = status_payload()
    data["records"][0]["status_observed_at"] = raw
    with pytest.raises(FrankfurtSourceError, match="FRANKFURT_RECORD_INVALID"):
        assess(data)


@pytest.mark.parametrize("state", ["CLOSED", "SUSPENDED", "UNKNOWN"])
@pytest.mark.asyncio
async def test_negative_or_unknown_status_is_preserved_without_becoming_open(state):
    data = status_payload()
    data["records"][0]["trading_status"] = state
    adapter, _database, _snapshots, request, _row = context(data)
    result = await adapter.get_warrant_listing_quote(request)
    assert result.data.trading_status == state
    assert result.data.original_market_status.status == state
    assert result.reason_code == "FRANKFURT_MARKET_NOT_OPEN"


@pytest.mark.parametrize("invalid", ["future", "currency", "identity", "duplicate"])
def test_invalid_records_do_not_attach_original_status_evidence(invalid):
    data = status_payload()
    if invalid == "future":
        data["records"][0]["status_observed_at"] = (NOW + timedelta(microseconds=1)).isoformat()
    elif invalid == "currency":
        data["records"][0]["currency"] = "USD"
    elif invalid == "identity":
        data["records"][0]["isin"] = "DE000VH7S657"
    else:
        data["records"].append(dict(data["records"][0]))
    result = assess(data)
    assert result.status is not QuoteStatus.AVAILABLE
    assert result.original_market_status is None


def test_old_status_point_has_no_borrowed_quote_ttl_or_inferred_validity():
    data = status_payload()
    old = NOW - timedelta(days=2)
    data["records"][0]["status_observed_at"] = old.isoformat()
    result = assess(data)
    assert result.status is QuoteStatus.AVAILABLE  # Existing price classification is unchanged.
    assert result.original_market_status.observed_at == old
    assert result.original_market_status.temporal_meaning == "OBSERVED_AT_INSTANT"


@pytest.mark.asyncio
async def test_status_point_does_not_turn_last_trade_into_an_original_bid():
    data = status_payload()
    data["records"][0].update(kind="LAST_TRADE", last_price="0.34", last_at=NOW.isoformat())
    adapter, _database, _snapshots, request, _row = context(data)
    result = await adapter.get_warrant_listing_quote(request)
    assert result.data.bid is result.data.ask is result.data.original_evidence is None
    assert result.data.original_market_status.status == "OPEN"
    assert result.data.reference_price_type == "LAST_TRADE"


@pytest.mark.asyncio
async def test_status_without_bid_is_not_misrepresented_as_a_persistable_price_success():
    data = status_payload()
    data["records"][0].update(trading_status="CLOSED", bid=None, ask=None)
    observation = assess(data)
    assert observation.original_market_status.status == "CLOSED"
    assert observation.analysis_usable is False
    adapter, _database, _snapshots, request, _row = context(data)
    result = await adapter.get_warrant_listing_quote(request)
    assert result.data.original_market_status == observation.original_market_status
    assert result.data.bid is result.data.ask is result.data.observed_at is None
    assert result.data.original_evidence is None
    assert result.quality_status is QualityStatus.INCOMPLETE


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,value", [("bid", "not-a-price"), ("bid", "0"), ("bid_at", "bad-time")]
)
async def test_status_has_independent_validation_when_price_fields_are_invalid(field, value):
    data = status_payload()
    data["records"][0].update({field: value, "trading_status": "SUSPENDED"})
    observation = assess(data)
    assert observation.status is QuoteStatus.ERROR
    assert observation.reason == "FRANKFURT_RECORD_INVALID"
    assert observation.record is None
    assert observation.original_market_status.status == "SUSPENDED"
    assert "status_record" not in observation.model_dump(mode="json")
    adapter, _database, _snapshots, request, _row = context(data)
    result = await adapter.get_warrant_listing_quote(request)
    assert result.quality_status is QualityStatus.INCOMPLETE
    assert result.data.bid is result.data.ask is result.data.observed_at is None
    assert result.data.original_evidence is None
    assert result.data.original_market_status == observation.original_market_status
