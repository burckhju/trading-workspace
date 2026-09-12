"""Synthetic contract fixtures, not evidence of an operational vendor feed."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.providers.frankfurt_quotes.schema import (
    FrankfurtSnapshot,
    FrankfurtSourceError,
    QuoteStatus,
    assess_snapshot,
)

NOW = datetime(2026, 9, 11, 12, tzinfo=UTC)


def payload():
    return {
        "schema_version": "frankfurt-quotes-v1",
        "source": "test-vendor",
        "generated_at": NOW.isoformat(),
        "delay_seconds": 0,
        "records": [
            {
                "isin": "DE000VH2LU21",
                "wkn": "VH2LU2",
                "mic": "XFRA",
                "currency": "EUR",
                "kind": "BID_ASK",
                "bid": "0.32",
                "ask": "0.33",
                "bid_at": NOW.isoformat(),
                "ask_at": NOW.isoformat(),
                "bid_size": 1000,
                "ask_size": 2000,
                "trading_status": "OPEN",
            }
        ],
    }


def assess(value=None, **kwargs):
    return assess_snapshot(
        FrankfurtSnapshot.model_validate(value if value is not None else payload()),
        isin="DE000VH2LU21",
        wkn="VH2LU2",
        currency="EUR",
        now=NOW,
        retrieved_at=NOW,
        **kwargs,
    )


def test_exact_quote_is_monitoring_only():
    result = assess()
    assert result.status is QuoteStatus.AVAILABLE
    assert result.record.bid == Decimal("0.32")
    assert result.record.bid_size == 1000
    assert result.execution_usable is False
    assert result.observed_at == NOW


@pytest.mark.parametrize(
    "seconds,expected", [(899, "AVAILABLE"), (900, "AVAILABLE"), (900.001, "STALE")]
)
def test_age_boundary_never_rounds_down(seconds, expected):
    data = payload()
    data["records"][0]["bid_at"] = (NOW - timedelta(seconds=seconds)).isoformat()
    result = assess(data)
    assert result.status == expected
    assert result.age_seconds == seconds


@pytest.mark.parametrize(
    "patch,reason",
    [
        (
            {"kind": "LAST_TRADE", "last_price": "0.99", "last_at": NOW.isoformat()},
            "POST_TRADE_ONLY",
        ),
        ({"bid": None}, "BID_ASK_MISSING"),
        ({"ask": None}, "BID_ASK_MISSING"),
        ({"bid_at": None}, "SIDE_TIMESTAMP_MISSING"),
        ({"ask_at": None}, "SIDE_TIMESTAMP_MISSING"),
        ({"ask": "0.30"}, "CROSSED_QUOTE"),
        ({"currency": "USD"}, "CURRENCY_MISMATCH"),
        ({"wkn": "WRONG1"}, "WKN_MISMATCH"),
        ({"wkn": None}, "WKN_MISMATCH"),
        ({"mic": "XETR"}, "VENUE_NOT_FOUND"),
        ({"mic": "XSTU"}, "VENUE_NOT_FOUND"),
        ({"isin": "DE000VH7S657"}, "INSTRUMENT_NOT_FOUND"),
        ({"trading_status": "CLOSED"}, "MARKET_NOT_OPEN"),
        ({"trading_status": "SUSPENDED"}, "MARKET_NOT_OPEN"),
        ({"trading_status": "UNKNOWN"}, "MARKET_NOT_OPEN"),
        (
            {"ask_at": (NOW + timedelta(seconds=1)).isoformat()},
            "TIMESTAMP_INCONSISTENT",
        ),
    ],
)
def test_rejected_quotes(patch, reason):
    data = payload()
    data["records"][0].update(patch)
    result = assess(data)
    assert result.status != QuoteStatus.AVAILABLE
    assert result.reason == f"FRANKFURT_{reason}"
    assert result.execution_usable is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("bid", "NaN"),
        ("ask", "Infinity"),
        ("bid", "0"),
        ("bid", "-1"),
        ("bid_size", -1),
        ("ask_size", True),
        ("bid_size", 1.5),
        ("bid_at", "2026-09-11T12:00:00"),
        ("bid_at", 1789214400),
    ],
)
def test_malformed_record_is_fail_closed(field, value):
    data = payload()
    data["records"][0][field] = value
    with pytest.raises(FrankfurtSourceError, match="FRANKFURT_RECORD_INVALID"):
        assess(data)


def test_duplicates_are_not_arbitrarily_selected():
    data = payload()
    data["records"].append(deepcopy(data["records"][0]))
    assert assess(data).reason == "FRANKFURT_DUPLICATE_IDENTITY"


def test_foreign_venue_never_supplies_one_side():
    data = payload()
    other = deepcopy(data["records"][0])
    other["mic"] = "XSTU"
    data["records"][0]["bid"] = None
    data["records"].append(other)
    assert assess(data).reason == "FRANKFURT_BID_ASK_MISSING"


def test_empty_snapshot_is_missing_not_available():
    data = payload()
    data["records"] = []
    assert assess(data).status is QuoteStatus.MISSING


@pytest.mark.parametrize(
    "patch,reason",
    [
        ({"delay_seconds": 901}, "FEED_DELAY_EXCEEDED"),
        (
            {"generated_at": (NOW - timedelta(seconds=901)).isoformat()},
            "SNAPSHOT_STALE",
        ),
        (
            {"generated_at": (NOW + timedelta(seconds=1)).isoformat()},
            "TIMESTAMP_INCONSISTENT",
        ),
    ],
)
def test_snapshot_gates(patch, reason):
    data = payload()
    data.update(patch)
    if reason == "SNAPSHOT_STALE":
        data["records"][0]["bid_at"] = data["generated_at"]
        data["records"][0]["ask_at"] = data["generated_at"]
    assert assess(data).reason == f"FRANKFURT_{reason}"


def test_utc_conversion_keeps_instant():
    data = payload()
    data["records"][0]["bid_at"] = "2026-09-11T14:00:00+02:00"
    assert assess(data).observed_at == NOW


def test_unknown_schema_rejected():
    data = payload()
    data["schema_version"] = "an-unverified-exchange-schema"
    with pytest.raises(ValidationError):
        FrankfurtSnapshot.model_validate(data)


def test_policy_cannot_exceed_fifteen_minutes():
    with pytest.raises(ValueError):
        assess(max_age_seconds=901)
