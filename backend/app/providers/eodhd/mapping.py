"""Map validated EODHD transport DTOs to provider-independent market data."""

from __future__ import annotations

from datetime import datetime

from app.features.market_data.domain.enums import MarketDataProvider, QualityStatus
from app.features.market_data.domain.models import DailyPrice, ProviderInstrumentMapping
from app.features.market_data.service.errors import MarketDataMappingError
from app.providers.eodhd.dto import EodhdDailyPriceDto


def map_daily_price(
    dto: EodhdDailyPriceDto,
    *,
    mapping: ProviderInstrumentMapping,
    currency: str,
    retrieved_at: datetime,
) -> DailyPrice:
    """Convert one EODHD row while preserving the legacy listing price contract."""
    if mapping.listing_id is None:
        raise MarketDataMappingError(
            "Daily-price mapping requires a listing-owned provider mapping",
            provider=MarketDataProvider.EODHD,
            retryable=False,
        )
    try:
        return DailyPrice(
            listing_id=mapping.listing_id,
            trading_date=dto.date,
            open=dto.open,
            high=dto.high,
            low=dto.low,
            close=dto.close,
            adjusted_close=dto.adjusted_close,
            volume=dto.volume,
            currency=currency,
            provider=MarketDataProvider.EODHD,
            provider_symbol=mapping.provider_symbol,
            retrieved_at=retrieved_at,
            source_updated_at=None,
            quality_status=QualityStatus.VALID,
        )
    except ValueError as exc:
        raise MarketDataMappingError(
            "EODHD daily price violates internal market-data rules",
            provider=MarketDataProvider.EODHD,
            retryable=False,
        ) from exc
