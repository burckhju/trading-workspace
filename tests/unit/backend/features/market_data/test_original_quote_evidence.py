"""Explicit source-side clocks stay distinct from snapshot and receipt clocks."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import TypeAdapter, ValidationError

from app.features.market_data.domain.errors import InvalidMarketDataValue
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.domain.original_quote_evidence import (
    OriginalQuoteEvidence,
    OriginalQuoteSideEvidence,
)

NOW = datetime(2026, 9, 11, 18, tzinfo=UTC)
ISIN = "DE000VH2LU21"


def evidence():
    return OriginalQuoteEvidence(
        version="original-quote-evidence-v1",
        source_contract="frankfurt-quotes-v1",
        source_reference="synthetic-vendor",
        generated_at=NOW,
        isin=ISIN,
        currency="EUR",
        venue_mic="XFRA",
        bid=OriginalQuoteSideEvidence(Decimal("0.20"), NOW, "2026-09-11T20:00:00+02:00", "bid_at"),
        ask=OriginalQuoteSideEvidence(
            Decimal("0.22"),
            NOW - timedelta(seconds=10),
            "2026-09-11T17:59:50Z",
            "ask_at",
        ),
    )


def quote():
    original = evidence()
    return WarrantQuoteSnapshot(
        warrant_listing_id=uuid4(),
        bid=original.bid.price,
        ask=original.ask.price,
        currency="EUR",
        provider_symbol=ISIN,
        provider_exchange_code="XFRA",
        observed_at=original.ask.observed_at,
        isin=ISIN,
        source_mode="FRANKFURT_REALTIME_MONITORING",
        venue_mic="XFRA",
        original_evidence=original,
    )


def test_snapshot_json_roundtrip_preserves_two_original_clocks_and_text():
    original = quote()
    adapter = TypeAdapter(WarrantQuoteSnapshot)
    restored = adapter.validate_json(adapter.dump_json(original))
    assert restored == original
    assert restored.observed_at == NOW - timedelta(seconds=10)
    assert restored.original_evidence.bid.observed_at == NOW
    assert restored.original_evidence.bid.original_time_text == "2026-09-11T20:00:00+02:00"
    assert restored.original_evidence.ask.original_time_text == "2026-09-11T17:59:50Z"


@pytest.mark.parametrize(
    "changes",
    [
        {"price": Decimal("0")},
        {"price": Decimal("NaN")},
        {"price": Decimal("Infinity")},
        {"price": 0.2},
        {"price": True},
        {"observed_at": NOW.replace(tzinfo=None)},
        {"observed_at": NOW - timedelta(seconds=1)},
        {"original_time_text": "2026-09-11T18:00:00"},
        {"original_time_text": "18:00:00"},
        {"original_time_text": ""},
        {"original_time_text": "2026-09-11T18:00:01Z"},
        {"source_field": " "},
        {"time_basis": "SHARED_QUOTE_TIMESTAMP"},
    ],
)
def test_side_evidence_rejects_guessed_or_inconsistent_material(changes):
    with pytest.raises(InvalidMarketDataValue):
        replace(evidence().bid, **changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"version": "original-quote-evidence-v2"},
        {"source_contract": ""},
        {"source_reference": " "},
        {"generated_at": NOW.replace(tzinfo=None)},
        {"generated_at": NOW - timedelta(seconds=1)},
        {"isin": "FOREIGN"},
        {"currency": "eur"},
        {"venue_mic": "\uff38\uff26\uff32\uff21"},
        {"bid": None, "ask": None},
    ],
)
def test_quote_evidence_requires_source_identity_and_chronology(changes):
    with pytest.raises(InvalidMarketDataValue):
        replace(evidence(), **changes)


def test_crossed_original_sides_are_rejected():
    original = evidence()
    with pytest.raises(InvalidMarketDataValue, match="crossed"):
        replace(original, ask=replace(original.ask, price=Decimal("0.19")))


@pytest.mark.parametrize(
    "changes",
    [
        {"bid": Decimal("0.19")},
        {"ask": Decimal("0.23")},
        {"bid": None},
        {"currency": "USD"},
        {"provider_symbol": "DE000VH7S657"},
        {"isin": "DE000VH7S657"},
        {"venue_mic": "XSTU"},
        {"venue_mic": None},
        {
            "bid": None,
            "ask": None,
            "reference_price": Decimal("0.20"),
            "reference_price_type": "LAST_TRADE",
        },
    ],
)
def test_original_evidence_cannot_be_rebound_to_another_snapshot(changes):
    with pytest.raises(InvalidMarketDataValue):
        replace(quote(), **changes)


def test_legacy_payload_is_readable_without_inventing_a_side_time():
    adapter = TypeAdapter(WarrantQuoteSnapshot)
    payload = adapter.dump_python(replace(quote(), original_evidence=None), mode="json")
    payload.pop("original_evidence")
    restored = adapter.validate_python(payload)
    assert restored.original_evidence is None
    assert restored.observed_at == NOW - timedelta(seconds=10)


def test_corrupt_stored_original_time_text_is_rejected():
    adapter = TypeAdapter(WarrantQuoteSnapshot)
    payload = adapter.dump_python(quote(), mode="json")
    payload["original_evidence"]["bid"]["original_time_text"] = "2026-09-11T18:00:01Z"
    with pytest.raises(ValidationError):
        adapter.validate_python(payload)
