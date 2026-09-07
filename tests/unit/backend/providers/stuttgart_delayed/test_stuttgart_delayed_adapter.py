import gzip
import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest

from app.core.config.settings import StuttgartDelayedSettings, StuttgartDelayedSourceMode
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
        "schema_version": "xstu-pretrade-flat-2026-09-04",
        "records_path": "$",
        "isin_field": "Isin",
        "mic_field": "VenueOfPublication",
        "bid_field": "Bid",
        "ask_field": "Ask",
        "currency_field": "PriceCurrency",
        "observed_at_field": "TransactionTime",
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


def _record(
    *,
    bid: str = "2.40",
    ask: str = "2.50",
    isin: str = "DE000TEST123",
    mic: str = "XSTU",
    currency: str = "EUR",
    transaction_time: str | None = "2026-09-06T18:30:00.000000Z",
):
    record = {
        "Isin": isin,
        "VenueOfPublication": mic,
        "Bid": bid,
        "Ask": ask,
        "PriceCurrency": currency,
        "TransactionTimestamp": None,
    }
    if transaction_time is not None:
        record["TransactionTime"] = transaction_time
    return record


def _gzip_payload(records: list[dict]) -> bytes:
    return gzip.compress(json.dumps(records).encode("utf-8"))


def test_configuration_is_fail_closed_when_disabled() -> None:
    adapter = StuttgartDelayedWarrantQuoteAdapter(
        database=_Database(),  # type: ignore[arg-type]
        settings=StuttgartDelayedSettings(),
    )

    with pytest.raises(MarketDataConfigurationError):
        adapter._require_ready_configuration()


def test_source_configuration_is_fail_closed_when_required_value_is_missing() -> None:
    with pytest.raises(MarketDataConfigurationError):
        _adapter(source_mode=StuttgartDelayedSourceMode.LOCAL_DIRECTORY)._require_ready_configuration()

    with pytest.raises(MarketDataConfigurationError):
        _adapter(source_mode=StuttgartDelayedSourceMode.DIRECT_URL)._require_ready_configuration()


def test_verified_default_schema_is_complete_but_disabled() -> None:
    settings = StuttgartDelayedSettings()

    assert settings.enabled is False
    assert settings.source_mode == StuttgartDelayedSourceMode.INDEX
    assert settings.has_verified_schema is True
    assert settings.has_source_configuration is True
    assert settings.records_path == "$"
    assert settings.isin_field == "Isin"
    assert settings.mic_field == "VenueOfPublication"
    assert settings.bid_field == "Bid"
    assert settings.ask_field == "Ask"
    assert settings.currency_field == "PriceCurrency"
    assert settings.observed_at_field == "TransactionTime"


def test_direct_url_requires_absolute_https() -> None:
    with pytest.raises(ValueError):
        StuttgartDelayedSettings(direct_url="http://example.com/xstu.json.gz")

    settings = StuttgartDelayedSettings(direct_url="https://mirror.example/xstu.json.gz")
    assert settings.direct_url == "https://mirror.example/xstu.json.gz"


def test_extracts_only_official_https_download_host() -> None:
    adapter = _adapter()
    html = '<a href="https://ddl.service.boerse-stuttgart.de/s/abc123">Download</a>'

    assert adapter._extract_official_download_url(html) == (
        "https://ddl.service.boerse-stuttgart.de/s/abc123"
    )

    with pytest.raises(MarketDataInvalidResponseError):
        adapter._extract_official_download_url('<a href="https://example.com/file.json.gz">x</a>')


@pytest.mark.asyncio
async def test_local_directory_uses_latest_verified_xstu_file(tmp_path) -> None:
    older = tmp_path / "XSTU-pretrade-20260907T1840.json.gz"
    latest = tmp_path / "XSTU-pretrade-20260907T1849.json.gz"
    ignored = tmp_path / "other.json.gz"
    older.write_bytes(_gzip_payload([_record(bid="1.00")]))
    latest.write_bytes(_gzip_payload([_record(bid="2.42")]))
    ignored.write_bytes(_gzip_payload([_record(bid="9.99")]))

    adapter = _adapter(
        source_mode=StuttgartDelayedSourceMode.LOCAL_DIRECTORY,
        local_directory=str(tmp_path),
    )

    payload = await adapter._load_latest_payload()
    quote = adapter._parse_quote(payload, _identity())

    assert quote is not None
    assert quote.bid == Decimal("2.42")


@pytest.mark.asyncio
async def test_local_directory_rejects_missing_payload(tmp_path) -> None:
    adapter = _adapter(
        source_mode=StuttgartDelayedSourceMode.LOCAL_DIRECTORY,
        local_directory=str(tmp_path),
    )

    with pytest.raises(MarketDataInvalidResponseError):
        await adapter._load_latest_payload()


@pytest.mark.asyncio
async def test_direct_url_loads_gzip_payload_from_configured_https_endpoint() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://mirror.example/latest-xstu.json.gz"
        return httpx.Response(200, content=_gzip_payload([_record(bid="2.43")]))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = StuttgartDelayedWarrantQuoteAdapter(
            database=_Database(),  # type: ignore[arg-type]
            settings=_settings(
                source_mode=StuttgartDelayedSourceMode.DIRECT_URL,
                direct_url="https://mirror.example/latest-xstu.json.gz",
            ),
            client=client,
        )
        payload = await adapter._load_latest_payload()

    quote = adapter._parse_quote(payload, _identity())
    assert quote is not None
    assert quote.bid == Decimal("2.43")


def test_selects_latest_flat_xstu_quote_instead_of_historical_best_price() -> None:
    adapter = _adapter()
    identity = _identity()
    payload = [
        _record(
            bid="9.99",
            ask="10.10",
            transaction_time="2026-09-06T18:29:00.000000Z",
        ),
        _record(
            bid="2.42",
            ask="2.47",
            transaction_time="2026-09-06T18:30:00.000000Z",
        ),
        _record(
            bid="8.88",
            ask="8.99",
            isin="DE000OTHER1",
            transaction_time="2026-09-06T18:31:00.000000Z",
        ),
        _record(
            bid="7.77",
            ask="7.88",
            mic="XETR",
            transaction_time="2026-09-06T18:32:00.000000Z",
        ),
    ]

    quote = adapter._parse_quote(payload, identity)

    assert quote is not None
    assert quote.warrant_listing_id == identity.listing_id
    assert quote.bid == Decimal("2.42")
    assert quote.ask == Decimal("2.47")
    assert quote.currency == "EUR"
    assert quote.provider_exchange_code == "XSTU"
    assert quote.observed_at == datetime(2026, 9, 6, 18, 30, tzinfo=UTC)


def test_zero_quote_side_means_unavailable_not_invalid() -> None:
    adapter = _adapter()

    quote = adapter._parse_quote([_record(bid="0", ask="2.47")], _identity())

    assert quote is not None
    assert quote.bid is None
    assert quote.ask == Decimal("2.47")


def test_status_record_without_transaction_time_is_ignored() -> None:
    adapter = _adapter()
    status_record = _record(bid="0", ask="0", transaction_time=None)
    status_record["TransactionTimestamp"] = "2026-09-06T18:31:00.000000Z"

    quote = adapter._parse_quote(
        [
            _record(transaction_time="2026-09-06T18:30:00.000000Z"),
            status_record,
        ],
        _identity(),
    )

    assert quote is not None
    assert quote.bid == Decimal("2.40")
    assert quote.ask == Decimal("2.50")
    assert quote.observed_at == datetime(2026, 9, 6, 18, 30, tzinfo=UTC)


def test_same_timestamp_rows_are_combined_only_within_latest_timestamp() -> None:
    adapter = _adapter()

    quote = adapter._parse_quote(
        [
            _record(
                bid="2.40",
                ask="0",
                transaction_time="2026-09-06T18:30:00.000000Z",
            ),
            _record(
                bid="0",
                ask="2.47",
                transaction_time="2026-09-06T18:30:00.000000Z",
            ),
        ],
        _identity(),
    )

    assert quote is not None
    assert quote.bid == Decimal("2.40")
    assert quote.ask == Decimal("2.47")


def test_returns_missing_when_no_exact_listing_identity_matches() -> None:
    adapter = _adapter()

    quote = adapter._parse_quote([_record(mic="XETR")], _identity())

    assert quote is None


def test_rejects_currency_mismatch_crossed_latest_quote_and_negative_price() -> None:
    adapter = _adapter()

    with pytest.raises(MarketDataMappingError):
        adapter._parse_quote([_record(currency="USD")], _identity())

    with pytest.raises(MarketDataInvalidResponseError):
        adapter._parse_quote([_record(bid="2.50", ask="2.40")], _identity())

    with pytest.raises(MarketDataInvalidResponseError):
        adapter._parse_quote([_record(bid="-1", ask="2.40")], _identity())


def test_rejects_non_array_configured_record_path() -> None:
    adapter = _adapter(records_path="records")

    with pytest.raises(MarketDataInvalidResponseError):
        adapter._parse_quote({"records": {"not": "a list"}}, _identity())