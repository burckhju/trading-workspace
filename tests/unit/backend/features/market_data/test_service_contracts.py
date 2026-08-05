"""Unit tests for market-data requests, results, contracts and errors."""

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest

from app.features.market_data.domain.enums import (
    CacheStatus,
    MappingStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.errors import InvalidMarketDataValue
from app.features.market_data.service.contracts import HistoricalDailyPriceProvider
from app.features.market_data.service.errors import MarketDataRateLimitError
from app.features.market_data.service.types import (
    DailyPriceRequest,
    MappingValidationResult,
    MarketDataResult,
)

UTC_NOW = datetime(2026, 8, 5, 10, 0, tzinfo=UTC)


def test_daily_price_request_rejects_inverted_range() -> None:
    with pytest.raises(InvalidMarketDataValue) as exc_info:
        DailyPriceRequest(
            workspace_id=uuid4(),
            listing_id=uuid4(),
            mapping_id=uuid4(),
            start_date=date(2026, 8, 5),
            end_date=date(2026, 8, 4),
            correlation_id=uuid4(),
        )

    assert exc_info.value.field == "end_date"


def test_market_data_result_preserves_provenance() -> None:
    result = MarketDataResult(
        data=(),
        provider=MarketDataProvider.EODHD,
        capability=MarketDataCapability.HISTORICAL_DAILY_PRICES,
        correlation_id=uuid4(),
        retrieved_at=UTC_NOW,
        cache_status=CacheStatus.MISS,
        quality_status=QualityStatus.VALID,
        warnings=("", "mapped"),
        retry_count=2,
        provider_call_cost=1,
    )

    assert result.warnings == ("mapped",)
    assert result.retry_count == 2
    assert result.provider_call_cost == 1


@pytest.mark.parametrize(
    ("retry_count", "provider_call_cost", "field"),
    [(-1, 1, "retry_count"), (0, -1, "provider_call_cost")],
)
def test_market_data_result_rejects_negative_counters(
    retry_count: int, provider_call_cost: int, field: str
) -> None:
    with pytest.raises(InvalidMarketDataValue) as exc_info:
        MarketDataResult(
            data=None,
            provider=MarketDataProvider.EODHD,
            capability=MarketDataCapability.HISTORICAL_DAILY_PRICES,
            correlation_id=uuid4(),
            retrieved_at=UTC_NOW,
            cache_status=CacheStatus.BYPASS,
            quality_status=QualityStatus.INCOMPLETE,
            warnings=(),
            retry_count=retry_count,
            provider_call_cost=provider_call_cost,
        )

    assert exc_info.value.field == field


def test_mapping_validation_result_requires_utc() -> None:
    with pytest.raises(InvalidMarketDataValue):
        MappingValidationResult(
            mapping_id=uuid4(),
            provider=MarketDataProvider.EODHD,
            status=MappingStatus.INVALID,
            validated_at=datetime(2026, 8, 5, 10, 0),
        )


def test_rate_limit_error_exposes_stable_metadata() -> None:
    retry_after = timedelta(seconds=10)
    error = MarketDataRateLimitError(
        "Provider budget exhausted",
        provider=MarketDataProvider.EODHD,
        capability=MarketDataCapability.HISTORICAL_DAILY_PRICES,
        retryable=True,
        retry_after=retry_after,
    )

    assert error.code == "MARKET_DATA_RATE_LIMIT_ERROR"
    assert error.provider is MarketDataProvider.EODHD
    assert error.retryable is True
    assert error.retry_after == retry_after


def test_historical_provider_protocol_is_structural() -> None:
    class Adapter:
        async def get_daily_prices(
            self, request: DailyPriceRequest
        ) -> MarketDataResult[tuple]:
            raise NotImplementedError

    adapter: HistoricalDailyPriceProvider = Adapter()
    assert adapter is not None
