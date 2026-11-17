"""Original status points preserve their own clock without claiming a live feed."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import TypeAdapter, ValidationError
from tests.unit.backend.features.market_data.test_original_quote_evidence import (
    ISIN,
    NOW,
)
from tests.unit.backend.features.market_data.test_original_quote_evidence import (
    quote as price_quote,
)

from app.features.market_data.domain.errors import InvalidMarketDataValue
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.domain.original_market_status_evidence import (
    OriginalMarketStatusEvidence,
)


def status_evidence():
    return OriginalMarketStatusEvidence(
        version="original-market-status-evidence-v1",
        source_contract="frankfurt-quotes-v1",
        source_reference="synthetic-vendor",
        generated_at=NOW,
        isin=ISIN,
        venue_mic="XFRA",
        status="OPEN",
        original_status_text="OPEN",
        source_status_field="trading_status",
        observed_at=NOW - timedelta(seconds=30),
        original_time_text="2026-09-11T19:59:30+02:00",
        source_time_field="status_observed_at",
    )


def quote():
    return replace(price_quote(), trading_status="OPEN", original_market_status=status_evidence())


def test_json_roundtrip_retains_distinct_original_status_clock_text_and_source():
    original = quote()
    adapter = TypeAdapter(WarrantQuoteSnapshot)
    restored = adapter.validate_json(adapter.dump_json(original))
    assert restored == original
    assert restored.original_market_status.observed_at == NOW - timedelta(seconds=30)
    assert restored.original_market_status.original_time_text == "2026-09-11T19:59:30+02:00"
    assert restored.original_market_status.temporal_meaning == "OBSERVED_AT_INSTANT"
    assert restored.original_market_status.time_basis == "SEPARATE_STATUS_TIMESTAMP"
    assert restored.original_evidence.bid.observed_at == NOW
    assert restored.observed_at == NOW - timedelta(seconds=10)
    with pytest.raises(FrozenInstanceError):
        restored.original_market_status.status = "CLOSED"


@pytest.mark.parametrize(
    "changes",
    [
        {"version": "original-market-status-evidence-v2"},
        {"source_contract": " "},
        {"source_reference": ""},
        {"source_reference": "x" * 201},
        {"source_status_field": ""},
        {"source_time_field": " "},
        {"isin": "FOREIGN"},
        {"venue_mic": "\uff38\uff26\uff32\uff21"},
        {"status": "AVAILABLE"},
        {"original_status_text": "CLOSED"},
        {"original_status_text": "open"},
        {"generated_at": NOW.replace(tzinfo=None)},
        {"generated_at": NOW - timedelta(seconds=31)},
        {"observed_at": NOW - timedelta(seconds=29)},
        {"observed_at": NOW.replace(tzinfo=None)},
        {"observed_at": NOW.astimezone(timezone(timedelta(hours=1)))},
        {"time_basis": "GENERATION_TIMESTAMP"},
        {"temporal_meaning": "EFFECTIVE_UNTIL_NEXT_UPDATE"},
    ],
)
def test_status_evidence_rejects_mismatched_identity_time_and_semantics(changes):
    with pytest.raises(InvalidMarketDataValue):
        replace(status_evidence(), **changes)


@pytest.mark.parametrize(
    "raw",
    [
        None,
        True,
        1789156770,
        1789156770.0,
        NOW,
        "2026-09-11",
        "2026-09-11T17:59:30",
        "2026-09-11T17:59:30-00:00",
        "2026-09-11T17:59:30+24:00",
        "2026-09-31T17:59:30Z",
        "2026-09-11T17:59:30.0000001Z",
        "20260911T175930Z",
        "17:59:30Z",
    ],
)
def test_original_status_clock_requires_complete_explicit_source_text(raw):
    with pytest.raises(InvalidMarketDataValue):
        replace(status_evidence(), original_time_text=raw)


@pytest.mark.parametrize(
    "raw,normalized",
    [
        ("2026-11-16T10:00:00+01:60", datetime(2026, 11, 16, 8, tzinfo=UTC)),
        ("2026-11-16T10:00:00+00:99", datetime(2026, 11, 16, 8, 21, tzinfo=UTC)),
        ("2026-11-16T10:00:00-01:60", datetime(2026, 11, 16, 12, tzinfo=UTC)),
        ("2026-11-16T10:00:00-00:99", datetime(2026, 11, 16, 11, 39, tzinfo=UTC)),
        ("2026-11-16T10:00:00+24:00", datetime(2026, 11, 15, 10, tzinfo=UTC)),
    ],
)
def test_invalid_offset_is_rejected_even_when_normalized_utc_would_match(raw, normalized):
    # fromisoformat silently normalizes offset-minute overflow. Supplying the
    # matching UTC instant makes this a syntax regression, not an equality test.
    with pytest.raises(InvalidMarketDataValue):
        replace(
            status_evidence(),
            observed_at=normalized,
            generated_at=normalized,
            original_time_text=raw,
        )


@pytest.mark.parametrize(
    "raw,instant",
    [
        ("2026-11-16T10:00:00+23:59", datetime(2026, 11, 15, 10, 1, tzinfo=UTC)),
        ("2026-11-16T10:00:00-23:59", datetime(2026, 11, 17, 9, 59, tzinfo=UTC)),
    ],
)
def test_valid_explicit_offset_boundary_preserves_its_original_text(raw, instant):
    original = replace(
        status_evidence(), observed_at=instant, generated_at=instant, original_time_text=raw
    )
    assert original.original_time_text == raw
    assert original.observed_at == instant


@pytest.mark.parametrize(
    "changes",
    [
        {"provider_symbol": "DE000VH7S657"},
        {"isin": "DE000VH7S657"},
        {"venue_mic": "XSTU"},
        {"venue_mic": None},
        {"trading_status": "CLOSED"},
        {"trading_status": None},
    ],
)
def test_status_cannot_be_rebound_to_a_different_snapshot_identity_or_state(changes):
    with pytest.raises(InvalidMarketDataValue):
        replace(quote(), original_evidence=None, **changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"source_contract": "other-contract"},
        {"source_reference": "other-source"},
        {"generated_at": NOW + timedelta(seconds=1)},
    ],
)
def test_price_and_status_originate_in_one_exact_source_envelope(changes):
    with pytest.raises(InvalidMarketDataValue, match="same source envelope"):
        replace(quote(), original_market_status=replace(status_evidence(), **changes))


@pytest.mark.parametrize("state", ["OPEN", "CLOSED", "SUSPENDED", "UNKNOWN"])
def test_original_status_values_are_not_promoted_or_reclassified(state):
    original = replace(status_evidence(), status=state, original_status_text=state)
    snapshot = replace(quote(), trading_status=state, original_market_status=original)
    assert snapshot.original_market_status.status == state
    assert snapshot.original_market_status.observed_at == NOW - timedelta(seconds=30)
    assert not hasattr(snapshot.original_market_status, "verified")
    assert not hasattr(snapshot.original_market_status, "valid_until")


def test_legacy_snapshot_keeps_its_declared_status_without_inventing_evidence():
    adapter = TypeAdapter(WarrantQuoteSnapshot)
    payload = adapter.dump_python(replace(quote(), original_market_status=None), mode="json")
    payload.pop("original_market_status")
    restored = adapter.validate_python(payload)
    assert restored.trading_status == "OPEN"
    assert restored.original_market_status is None


def test_corrupt_stored_original_status_time_text_is_not_ignored():
    adapter = TypeAdapter(WarrantQuoteSnapshot)
    payload = adapter.dump_python(quote(), mode="json")
    payload["original_market_status"]["original_time_text"] = "2026-09-11T17:59:31Z"
    with pytest.raises(ValidationError):
        adapter.validate_python(payload)


def test_utc_offsets_across_dst_fold_remain_different_original_instants():
    first = datetime(2026, 10, 25, 0, 30, tzinfo=UTC)
    second = first + timedelta(hours=1)
    original = status_evidence()
    summer = replace(
        original,
        observed_at=first,
        generated_at=second,
        original_time_text="2026-10-25T02:30:00+02:00",
    )
    winter = replace(
        original,
        observed_at=second,
        generated_at=second,
        original_time_text="2026-10-25T02:30:00+01:00",
    )
    assert winter.observed_at - summer.observed_at == timedelta(hours=1)
