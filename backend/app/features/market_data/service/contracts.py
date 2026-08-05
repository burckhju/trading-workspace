"""Capability-based provider contracts consumed by application services."""

from __future__ import annotations

from typing import Protocol

from app.features.market_data.domain.models import DailyPrice, ProviderInstrumentMapping
from app.features.market_data.service.types import (
    DailyPriceRequest,
    LatestDailyPriceRequest,
    MappingValidationResult,
    MarketDataResult,
)


class HistoricalDailyPriceProvider(Protocol):
    """Supply historical completed daily prices for one mapped listing."""

    async def get_daily_prices(
        self, request: DailyPriceRequest
    ) -> MarketDataResult[tuple[DailyPrice, ...]]:
        """Return validated prices in the requested inclusive date range."""
        ...


class LatestCompletedDailyPriceProvider(Protocol):
    """Supply the latest completed daily price for one mapped listing."""

    async def get_latest_completed_daily_price(
        self, request: LatestDailyPriceRequest
    ) -> MarketDataResult[DailyPrice | None]:
        """Return the newest completed daily price or ``None`` when unavailable."""
        ...


class ProviderInstrumentResolver(Protocol):
    """Validate an approved internal-to-provider instrument association."""

    async def validate_mapping(
        self, mapping: ProviderInstrumentMapping
    ) -> MappingValidationResult:
        """Validate the provider symbol without mutating FT-001 master data."""
        ...
