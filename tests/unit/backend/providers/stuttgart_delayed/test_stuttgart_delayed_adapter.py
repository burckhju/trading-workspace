from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.config.settings import StuttgartDelayedSettings
from app.features.market_data.service.errors import (
    MarketDataConfigurationError,
    MarketDataInvalidResponseError,
    MarketDataMappingError,
)
from app.providers.stuttgart_delayed.adapter import (
    StuttgartDelayedWarrantQuoteAdapter,
    _ListingIdentity,
)


class _Database:
    pass


def _settings(**overrides) -> StuttgartDelayedSettings:
    values = {
        "enabled": True,
        "schema_version": "verified-fixture-v1",
        "records_path": "records",
        "isin_field": "instrument.isin",
        "mic_field": "venue.mic",
        "side_field": "quote.side",
        "price_field": "quote.price",
        "currency_field": "quote.currency",
        "observed_at_field": "quote.observed_at",
        "bid_side_value": "BID",
        "ask_side_value": "ASK",
    }
    values.update(overrides)
    return StuttgartDelayedSettings(**values)


def _adapter(**overrides) -> StuttgartDelayedWarrantQuoteAdapter:
    return StuttgartDelayedWarrantQuoteAdapter(
        database=_Database(),  # type: ignore[arg-type]
        settings=_settings(**overrides),
    )


def _identity(*, mic: str = "XSTU") -> _ListingIdentity:
    return _ListingIdentity(
        listing_id=uuid4(),
        symbol="TEST12",
        currency="EUR",
        isin="DE000TEST123",
        mic=mic,
    )


def _record(*, side: str, price: str, isin: str = "DE000TEST123", mic: str = "XSTU"):
    return {
        "instrument": {"isin": isin},
        "venue": {"mic": mic},
        "quote": {
            "side": side,
            "price": price,
            "currency": "EUR",
            "observed_at": "2026-09-06T18:30:00Z",
        },
    }


def test_configuration_is_fail_closed_without_verified_schema() -> None:
    adapter = StuttgartDelayedWarrantQuoteAdapter(
        database=_Database(),  # type: ignore[arg-type]
        settings=StuttgartDelayedSettings(enabled=True),
    )

    with pytest.raises(MarketDataConfigurationError):
        adapter._require_ready_configuration()


def test_extracts_only_official_https_download_host() -> None:
    adapter = _adapter()
    html = '<a href="https://ddl.service.boerse-stuttgart.de/s/abc123">Download</a>'

    assert adapter._extract_official_download_url(html) == (
        "https://ddl.service.boerse-stuttgart.de/s/abc123"
    )

    with pytest.raises(MarketDataInvalidResponseError):
        adapter._extract_official_download_url('<a href="https://example.com/file.json.gz">x</a>')


def test_parses_best_bid_and_ask_for_exact_isin_and_xstu_only() -> None:
    adapter = _adapter()
    identity = _identity()
    payload = {
        "records": [
            _record(side="BID", price="2.40"),
            _record(side="BID", price="2.42"),
            _record(side="ASK", price="2.49"),
            _record(side="ASK", price="2.47"),
            _record(side="BID", price="9.99", isin="DE000OTHER1"),
            _record(side="BID", price="8.88", mic="XETR"),
        ]
    }

    quote = adapter._parse_quote(payload, identity)

    assert quote is not None
    assert quote.warrant_listing_id == identity.listing_id
    assert quote.bid == Decimal("2.42")
    assert quote.ask == Decimal("2.47")
    assert quote.currency == "EUR"
    assert quote.provider_exchange_code == "XSTU"
    assert quote.observed_at == datetime(2026, 9, 6, 18, 30, tzinfo=UTC)


def test_returns_missing_when_no_exact_listing_identity_matches() -> None:
    adapter = _adapter()

    quote = adapter._parse_quote(
        {"records": [_record(side="BID", price="2.40", mic="XETR")]},
        _identity(),
    )

    assert quote is None


def test_rejects_currency_conflict_and_crossed_quotes() -> None:
    adapter = _adapter()
    currency_record = _record(side="BID", price="2.40")
    currency_record["quote"]["currency"] = "USD"

    with pytest.raises(MarketDataMappingError):
        adapter._parse_quote({"records": [currency_record]}, _identity())

    with pytest.raises(MarketDataInvalidResponseError):
        adapter._parse_quote(
            {"records": [_record(side="BID", price="2.50"), _record(side="ASK", price="2.40")]},
            _identity(),
        )


def test_rejects_non_array_configured_record_path() -> None:
    adapter = _adapter()

    with pytest.raises(MarketDataInvalidResponseError):
        adapter._parse_quote({"records": {"not": "a list"}}, _identity())
