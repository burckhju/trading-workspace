from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.features.market_data.domain.enums import (
    CacheStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.service.errors import (
    MarketDataConfigurationError,
    MarketDataInvalidResponseError,
)
from app.features.market_data.service.refresh_diagnostics import job_diagnostics
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest
from app.features.position_monitoring.service.quote_sources import (
    MultiSourceWarrantQuoteResolver,
    NamedWarrantQuoteSource,
    QuoteSourceAttemptStatus,
)

NOW = datetime(2026, 9, 6, 18, 30, tzinfo=UTC)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("FRANKFURT_REQUEST_THROTTLED", "FRANKFURT_REQUEST_THROTTLED"),
        ("FRANKFURT_HTTP_404", "FRANKFURT_HTTP_404"),
        ("https://provider.example/?token=SECRET", "MarketDataInvalidResponseError"),
        ("FRANKFURT_HTTP_503\nSECRET", "MarketDataInvalidResponseError"),
    ],
)
async def test_source_diagnostics_preserve_machine_codes_without_raw_exception_text(
    message, expected
):
    source = _Provider(error=MarketDataInvalidResponseError(message))
    resolved = await MultiSourceWarrantQuoteResolver(
        (NamedWarrantQuoteSource("FRANKFURT_QUOTES", source),)
    ).resolve(_request(uuid4()))
    assert resolved.result is None
    assert resolved.attempts[0].reason == expected


class _Provider:
    def __init__(self, *, result=None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.calls = 0

    async def get_warrant_listing_quote(self, _request):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result


def _request(listing_id):
    return WarrantQuoteRequest(
        workspace_id=uuid4(),
        warrant_listing_id=listing_id,
        correlation_id=uuid4(),
        as_of=NOW,
    )


def _result(listing_id, *, bid=Decimal("2.40"), quality=QualityStatus.VALID):
    return MarketDataResult(
        data=WarrantQuoteSnapshot(
            warrant_listing_id=listing_id,
            bid=bid,
            ask=Decimal("2.45"),
            currency="EUR",
            provider_symbol="TEST12",
            provider_exchange_code="XSTU",
            observed_at=NOW,
        ),
        provider=MarketDataProvider.EODHD,
        capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
        correlation_id=uuid4(),
        retrieved_at=NOW,
        cache_status=CacheStatus.MISS,
        quality_status=quality,
        warnings=(),
        retry_count=0,
        provider_call_cost=1,
    )


@pytest.mark.asyncio
async def test_falls_back_after_unavailable_source() -> None:
    listing_id = uuid4()
    first = _Provider(
        error=MarketDataConfigurationError(
            "not configured",
            provider=MarketDataProvider.EODHD,
            capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            retryable=False,
        )
    )
    second = _Provider(result=_result(listing_id))
    resolver = MultiSourceWarrantQuoteResolver(
        (
            NamedWarrantQuoteSource("EODHD", first),
            NamedWarrantQuoteSource("SECONDARY", second, delayed=True),
        )
    )

    resolved = await resolver.resolve(_request(listing_id))

    assert resolved.result is not None
    assert resolved.selected_source == "SECONDARY"
    assert [attempt.status for attempt in resolved.attempts] == [
        QuoteSourceAttemptStatus.UNAVAILABLE,
        QuoteSourceAttemptStatus.AVAILABLE,
    ]
    assert resolved.attempts[1].delayed is True


@pytest.mark.asyncio
async def test_continues_after_missing_bid() -> None:
    listing_id = uuid4()
    first = _Provider(result=_result(listing_id, bid=None))
    second = _Provider(result=_result(listing_id, bid=Decimal("2.41")))
    resolver = MultiSourceWarrantQuoteResolver(
        (
            NamedWarrantQuoteSource("PRIMARY", first),
            NamedWarrantQuoteSource("FALLBACK", second),
        )
    )

    resolved = await resolver.resolve(_request(listing_id))

    assert resolved.selected_source == "FALLBACK"
    assert resolved.attempts[0].status is QuoteSourceAttemptStatus.INSUFFICIENT
    assert resolved.attempts[0].reason == "BID_MISSING"


@pytest.mark.parametrize("refresh_error", [None, "JPMORGAN_SNAPSHOT_TIMEOUT"])
async def test_missing_bid_keeps_refresh_and_unknown_clock_diagnostics_without_fallback(
    refresh_error,
):
    listing_id = uuid4()
    original = _result(listing_id, bid=None)
    quote = replace(
        original.data,
        ask=None,
        provider_exchange_code="ISSUER",
        observed_at=None,
        source_mode="OFFICIAL_ISSUER_INDICATION_TIME_ONLY",
        quote_time_text="18:20:00",
        quote_time_basis="DATE_AND_TIMEZONE_UNKNOWN",
        retained=refresh_error is not None,
        refresh_error=refresh_error,
    )
    provider_result = replace(
        original,
        data=quote,
        provider=MarketDataProvider.JPMORGAN,
        retrieved_at=NOW - timedelta(minutes=10),
        reason_code="QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY",
    )
    selected = _Provider(result=provider_result)
    fallback = _Provider(result=_result(listing_id))
    resolver = MultiSourceWarrantQuoteResolver(
        (
            NamedWarrantQuoteSource("JPMORGAN", selected),
            NamedWarrantQuoteSource("FALLBACK", fallback),
        )
    )

    resolved = await resolver.resolve_selected("JPMORGAN", _request(listing_id))

    assert resolved.result is None
    assert resolved.selected_source is None
    assert selected.calls == 1
    assert fallback.calls == 0
    attempt = resolved.attempts[0]
    assert attempt.status is QuoteSourceAttemptStatus.INSUFFICIENT
    assert attempt.reason == "BID_MISSING"
    assert attempt.bid_available is False
    assert attempt.ask_available is False
    assert attempt.currency == "EUR"
    assert attempt.refresh_error == refresh_error
    assert attempt.retained is (refresh_error is not None)
    assert attempt.provider_reason == "QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY"
    assert attempt.quote_time_basis == "DATE_AND_TIMEZONE_UNKNOWN"
    assert attempt.observed_at is None
    assert provider_result.data is quote
    assert provider_result.retrieved_at == NOW - timedelta(minutes=10)
    diagnostics = job_diagnostics(
        None,
        "MISSING",
        {"reason": "NO_USABLE_WARRANT_QUOTE", "source_attempts": [asdict(attempt)]},
        NOW,
    )
    source_check = next(item for item in diagnostics["checks"] if item["kind"] == "SOURCE")
    assert source_check["reason"] == (refresh_error or "BID_MISSING")
    assert source_check["qualified_success"] is False


@pytest.mark.parametrize("provider_reason", [None, "SOURCE_DATA_INCOMPLETE"])
@pytest.mark.parametrize("bid", [None, Decimal("2.40")])
async def test_invalid_quality_keeps_its_failure_with_or_without_bid(provider_reason, bid):
    listing_id = uuid4()
    provider_result = replace(
        _result(listing_id, bid=bid, quality=QualityStatus.INCOMPLETE),
        reason_code=provider_reason,
    )
    resolved = await MultiSourceWarrantQuoteResolver(
        (NamedWarrantQuoteSource("PRIMARY", _Provider(result=provider_result)),)
    ).resolve(_request(listing_id))

    assert resolved.result is None
    attempt = resolved.attempts[0]
    assert attempt.status is QuoteSourceAttemptStatus.INSUFFICIENT
    assert attempt.bid_available is (bid is not None)
    assert attempt.reason == (provider_reason or "QUALITY_INCOMPLETE")
    assert attempt.provider_reason == provider_reason


async def test_reference_price_without_bid_remains_available_only_as_reference():
    listing_id = uuid4()
    original = _result(listing_id, bid=None)
    provider_result = replace(
        original,
        data=replace(
            original.data,
            ask=None,
            reference_price=Decimal("2.40"),
            reference_price_type="PREVIOUS_CLOSE",
        ),
    )
    resolved = await MultiSourceWarrantQuoteResolver(
        (NamedWarrantQuoteSource("PRIMARY", _Provider(result=provider_result)),)
    ).resolve(_request(listing_id))

    assert resolved.result is provider_result
    attempt = resolved.attempts[0]
    assert attempt.status is QuoteSourceAttemptStatus.AVAILABLE
    assert attempt.reason == "REFERENCE_PRICE_AVAILABLE_FOR_ANALYSIS"
    assert attempt.bid_available is False
    assert attempt.reference_price == Decimal("2.40")
    assert attempt.reference_price_type == "PREVIOUS_CLOSE"


async def test_positive_retained_bid_preserves_refresh_failure_and_source_clock():
    listing_id = uuid4()
    original = _result(listing_id)
    provider_result = replace(
        original,
        data=replace(
            original.data,
            provider_exchange_code="ISSUER",
            observed_at=None,
            source_mode="OFFICIAL_ISSUER_INDICATION_TIME_ONLY",
            quote_time_text="18:20:00",
            quote_time_basis="DATE_AND_TIMEZONE_UNKNOWN",
            retained=True,
            refresh_error="JPMORGAN_SNAPSHOT_TIMEOUT",
        ),
        provider=MarketDataProvider.JPMORGAN,
        reason_code="QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY",
    )
    resolved = await MultiSourceWarrantQuoteResolver(
        (NamedWarrantQuoteSource("JPMORGAN", _Provider(result=provider_result)),)
    ).resolve_selected("JPMORGAN", _request(listing_id))

    assert resolved.result is provider_result
    attempt = resolved.attempts[0]
    assert attempt.status is QuoteSourceAttemptStatus.AVAILABLE
    assert attempt.reason == "LAST_SUCCESSFUL_QUOTE_REFRESH_FAILED"
    assert attempt.bid_available is True
    assert attempt.refresh_error == "JPMORGAN_SNAPSHOT_TIMEOUT"
    assert attempt.retained is True
    assert attempt.provider_reason == "QUOTE_TIMESTAMP_UNKNOWN_INDICATIVE_ANALYSIS_ONLY"
    assert attempt.quote_time_basis == "DATE_AND_TIMEZONE_UNKNOWN"
    assert attempt.observed_at is None


@pytest.mark.asyncio
async def test_rejects_wrong_listing_and_keeps_searching() -> None:
    listing_id = uuid4()
    first = _Provider(result=_result(uuid4()))
    second = _Provider(result=_result(listing_id))
    resolver = MultiSourceWarrantQuoteResolver(
        (
            NamedWarrantQuoteSource("WRONG", first),
            NamedWarrantQuoteSource("RIGHT", second),
        )
    )

    resolved = await resolver.resolve(_request(listing_id))

    assert resolved.selected_source == "RIGHT"
    assert resolved.attempts[0].status is QuoteSourceAttemptStatus.ERROR
    assert resolved.attempts[0].reason == "WARRANT_LISTING_MISMATCH"


@pytest.mark.asyncio
async def test_returns_complete_attempt_trace_when_no_source_is_usable() -> None:
    listing_id = uuid4()
    first = _Provider(result=None)
    second = _Provider(error=RuntimeError("down"))
    resolver = MultiSourceWarrantQuoteResolver(
        (
            NamedWarrantQuoteSource("EMPTY", first),
            NamedWarrantQuoteSource("DOWN", second),
        )
    )

    resolved = await resolver.resolve(_request(listing_id))

    assert resolved.result is None
    assert resolved.selected_source is None
    assert [attempt.status for attempt in resolved.attempts] == [
        QuoteSourceAttemptStatus.MISSING,
        QuoteSourceAttemptStatus.ERROR,
    ]


@pytest.mark.asyncio
async def test_unconfigured_placeholder_is_not_reported_as_executed_attempt() -> None:
    listing_id = uuid4()
    provider = _Provider(result=_result(listing_id))
    resolver = MultiSourceWarrantQuoteResolver(
        (
            NamedWarrantQuoteSource("RESERVED", None),
            NamedWarrantQuoteSource("ACTIVE", provider),
        )
    )

    resolved = await resolver.resolve(_request(listing_id))

    assert provider.calls == 1
    assert resolved.selected_source == "ACTIVE"
    assert [attempt.source for attempt in resolved.attempts] == ["ACTIVE"]


@pytest.mark.asyncio
async def test_persisted_source_resolution_never_falls_back() -> None:
    listing_id = uuid4()
    selected = _Provider(result=_result(listing_id))
    fallback = _Provider(result=_result(listing_id, bid=Decimal("2.44")))
    resolver = MultiSourceWarrantQuoteResolver(
        (
            NamedWarrantQuoteSource("EODHD", selected),
            NamedWarrantQuoteSource("FALLBACK", fallback),
        )
    )

    resolved = await resolver.resolve_selected("EODHD", _request(listing_id))

    assert resolved.selected_source == "EODHD"
    assert selected.calls == 1
    assert fallback.calls == 0


@pytest.mark.asyncio
async def test_persisted_disabled_source_is_unavailable_without_fallback() -> None:
    listing_id = uuid4()
    fallback = _Provider(result=_result(listing_id))
    resolver = MultiSourceWarrantQuoteResolver(
        (
            NamedWarrantQuoteSource(
                "GETTEX_DELAYED",
                None,
                delayed=True,
                unavailable_reason="GETTEX_DELAYED_DISABLED",
            ),
            NamedWarrantQuoteSource("FALLBACK", fallback),
        )
    )

    resolved = await resolver.resolve_selected("GETTEX_DELAYED", _request(listing_id))

    assert resolved.result is None
    assert resolved.selected_source is None
    assert resolved.attempts[0].status is QuoteSourceAttemptStatus.UNAVAILABLE
    assert resolved.attempts[0].reason == "GETTEX_DELAYED_DISABLED"
    assert fallback.calls == 0
