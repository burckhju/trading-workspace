from datetime import UTC, datetime
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
from app.features.market_data.service.errors import MarketDataConfigurationError
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest
from app.features.position_monitoring.service.quote_sources import (
    MultiSourceWarrantQuoteResolver,
    NamedWarrantQuoteSource,
    QuoteSourceAttemptStatus,
)

NOW = datetime(2026, 9, 6, 18, 30, tzinfo=UTC)


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
