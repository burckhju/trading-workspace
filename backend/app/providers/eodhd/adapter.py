"""Provider adapter implementing market-data capabilities through EODHD."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Protocol
from urllib.parse import quote
from uuid import UUID

from pydantic import TypeAdapter, ValidationError

from app.features.market_data.domain.enums import (
    CacheStatus,
    MappingStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import DailyPrice, ProviderInstrumentMapping
from app.features.market_data.service.errors import (
    MarketDataInvalidResponseError,
    MarketDataMappingError,
    MarketDataNotFoundError,
)
from app.features.market_data.service.types import (
    DailyPriceRequest,
    LatestDailyPriceRequest,
    MappingValidationResult,
    MarketDataResult,
    ProviderInstrumentSearchItem,
)
from app.providers.eodhd.client import EodhdClient
from app.providers.eodhd.dto import EodhdDailyPriceDto, EodhdSearchResultDto
from app.providers.eodhd.mapping import map_daily_price
from app.providers.shared.budget import DailyCallBudget
from app.providers.shared.cache import InMemoryTtlCache
from app.providers.shared.clock import Clock
from app.providers.shared.rate_limit import TokenBucketRateLimiter
from app.providers.shared.retry import RetryPolicy


class MappingReader(Protocol):
    """Load one provider mapping without exposing persistence implementation details."""

    async def get_mapping(
        self, workspace_id: UUID, mapping_id: UUID
    ) -> ProviderInstrumentMapping | None:
        """Return a mapping scoped to its workspace."""
        ...


class ListingCurrencyReader(Protocol):
    """Resolve the internal listing currency owned by FT-001."""

    async def get_currency(self, workspace_id: UUID, listing_id: UUID) -> str | None:
        """Return the listing currency code."""
        ...


@dataclass(frozen=True, slots=True)
class EodhdAdapterSettings:
    """Capability-specific technical settings for the EODHD adapter."""

    historical_ttl: timedelta = timedelta(hours=24)
    latest_ttl: timedelta = timedelta(minutes=15)
    provider_call_cost: int = 1

    def __post_init__(self) -> None:
        if self.historical_ttl.total_seconds() <= 0 or self.latest_ttl.total_seconds() <= 0:
            raise ValueError("cache TTLs must be positive")
        if self.provider_call_cost < 1:
            raise ValueError("provider_call_cost must be positive")


@dataclass(frozen=True, slots=True)
class _CachedPrices:
    prices: tuple[DailyPrice, ...]
    retrieved_at: datetime


_DTO_LIST = TypeAdapter(list[EodhdDailyPriceDto])
_SEARCH_DTO_LIST = TypeAdapter(list[EodhdSearchResultDto])


class EodhdMarketDataAdapter:
    """Implement EOD price capabilities without leaking EODHD into the domain."""

    def __init__(
        self,
        *,
        client: EodhdClient,
        mappings: MappingReader,
        currencies: ListingCurrencyReader,
        cache: InMemoryTtlCache[tuple[object, ...], _CachedPrices],
        retry_policy: RetryPolicy,
        rate_limiter: TokenBucketRateLimiter,
        call_budget: DailyCallBudget,
        clock: Clock,
        settings: EodhdAdapterSettings | None = None,
    ) -> None:
        self._client = client
        self._mappings = mappings
        self._currencies = currencies
        self._cache = cache
        self._retry = retry_policy
        self._rate_limiter = rate_limiter
        self._budget = call_budget
        self._clock = clock
        self._settings = settings or EodhdAdapterSettings()

    async def search_instruments(
        self, query: str, *, limit: int = 10
    ) -> tuple[ProviderInstrumentSearchItem, ...]:
        """Return read-only provider suggestions without mutating workspace master data."""
        normalized = query.strip()
        if not normalized:
            return ()
        if not 1 <= limit <= 20:
            raise ValueError("limit must be between 1 and 20")
        capability = MarketDataCapability.INSTRUMENT_SEARCH

        async def operation() -> tuple[EodhdSearchResultDto, ...]:
            await self._budget.consume(self._settings.provider_call_cost, capability=capability)
            await self._rate_limiter.acquire()
            payload = await self._client.get_json(
                f"/search/{quote(normalized, safe='')}",
                capability=capability,
                params={"limit": limit},
            )
            try:
                return tuple(_SEARCH_DTO_LIST.validate_python(payload))
            except ValidationError as exc:
                raise MarketDataInvalidResponseError(
                    "EODHD search response has an invalid structure",
                    provider=MarketDataProvider.EODHD,
                    capability=capability,
                    retryable=False,
                ) from exc

        outcome = await self._retry.execute(operation)
        return tuple(
            ProviderInstrumentSearchItem(
                provider=MarketDataProvider.EODHD,
                provider_symbol=row.code,
                provider_exchange_code=row.exchange,
                name=row.name,
                instrument_type=row.type,
                currency=row.currency,
                isin=row.isin,
            )
            for row in outcome.value
        )

    async def validate_mapping(self, mapping: ProviderInstrumentMapping) -> MappingValidationResult:
        """Validate a mapping technically through EODHD Search API without mutation."""
        capability = MarketDataCapability.INSTRUMENT_MAPPING_VALIDATION

        async def operation() -> tuple[EodhdSearchResultDto, ...]:
            await self._budget.consume(self._settings.provider_call_cost, capability=capability)
            await self._rate_limiter.acquire()
            payload = await self._client.get_json(
                f"/search/{mapping.provider_symbol}",
                capability=capability,
                params={"exchange": mapping.provider_exchange_code, "limit": 20},
            )
            try:
                return tuple(_SEARCH_DTO_LIST.validate_python(payload))
            except ValidationError as exc:
                raise MarketDataInvalidResponseError(
                    "EODHD search response has an invalid structure",
                    provider=MarketDataProvider.EODHD,
                    capability=capability,
                    retryable=False,
                ) from exc

        outcome = await self._retry.execute(operation)
        expected_symbol = mapping.provider_symbol.upper()
        expected_exchange = mapping.provider_exchange_code.upper()
        match = next(
            (
                row
                for row in outcome.value
                if row.code.upper() == expected_symbol and row.exchange.upper() == expected_exchange
            ),
            None,
        )
        now = self._clock.utcnow()
        if match is None:
            return MappingValidationResult(
                mapping_id=mapping.id,
                provider=MarketDataProvider.EODHD,
                status=MappingStatus.INVALID,
                validated_at=now,
                message="EODHD did not return an exact symbol and exchange match",
            )
        return MappingValidationResult(
            mapping_id=mapping.id,
            provider=MarketDataProvider.EODHD,
            status=MappingStatus.ACTIVE,
            validated_at=now,
            message="Technically validated against EODHD Search API",
            provider_symbol=match.code,
            provider_exchange_code=match.exchange,
            currency=match.currency,
        )

    async def get_daily_prices(
        self, request: DailyPriceRequest
    ) -> MarketDataResult[tuple[DailyPrice, ...]]:
        """Return completed daily prices for the inclusive requested range."""
        capability = MarketDataCapability.HISTORICAL_DAILY_PRICES
        mapping, currency = await self._context(
            request.workspace_id, request.listing_id, request.mapping_id, capability
        )
        key = (
            MarketDataProvider.EODHD,
            capability,
            mapping.provider_exchange_code,
            mapping.provider_symbol,
            request.start_date,
            request.end_date,
        )
        return await self._load(
            key=key,
            mapping=mapping,
            currency=currency,
            capability=capability,
            start=request.start_date,
            end=request.end_date,
            ttl=self._settings.historical_ttl,
            correlation_id=request.correlation_id,
            latest=False,
        )

    async def get_latest_completed_daily_price(
        self, request: LatestDailyPriceRequest
    ) -> MarketDataResult[DailyPrice | None]:
        """Return the newest available completed daily price on or before a date."""
        capability = MarketDataCapability.LATEST_COMPLETED_DAILY_PRICE
        mapping, currency = await self._context(
            request.workspace_id, request.listing_id, request.mapping_id, capability
        )
        end = request.as_of_date or self._clock.utcnow().date()
        start = end - timedelta(days=14)
        key = (
            MarketDataProvider.EODHD,
            capability,
            mapping.provider_exchange_code,
            mapping.provider_symbol,
            end,
        )
        result = await self._load(
            key=key,
            mapping=mapping,
            currency=currency,
            capability=capability,
            start=start,
            end=end,
            ttl=self._settings.latest_ttl,
            correlation_id=request.correlation_id,
            latest=True,
        )
        latest = result.data[-1] if result.data else None
        return MarketDataResult(
            data=latest,
            provider=result.provider,
            capability=result.capability,
            correlation_id=result.correlation_id,
            retrieved_at=result.retrieved_at,
            cache_status=result.cache_status,
            quality_status=result.quality_status,
            warnings=result.warnings,
            retry_count=result.retry_count,
            provider_call_cost=result.provider_call_cost,
        )

    async def _load(
        self,
        *,
        key: tuple[object, ...],
        mapping: ProviderInstrumentMapping,
        currency: str,
        capability: MarketDataCapability,
        start: date,
        end: date,
        ttl: timedelta,
        correlation_id: UUID,
        latest: bool,
    ) -> MarketDataResult[tuple[DailyPrice, ...]]:
        lookup = await self._cache.get(key)
        if lookup.hit and lookup.value is not None:
            cached = lookup.value
            return self._result(
                cached.prices,
                capability=capability,
                correlation_id=correlation_id,
                retrieved_at=(
                    cached.prices[0].retrieved_at if cached.prices else self._clock.utcnow()
                ),
                cache_status=CacheStatus.HIT,
                retry_count=0,
                provider_call_cost=0,
            )

        async def operation() -> tuple[DailyPrice, ...]:
            await self._budget.consume(self._settings.provider_call_cost, capability=capability)
            await self._rate_limiter.acquire()
            payload = await self._client.get_json(
                f"/eod/{mapping.provider_symbol}.{mapping.provider_exchange_code}",
                capability=capability,
                params={
                    "from": start.isoformat(),
                    "to": end.isoformat(),
                    "period": "d",
                    "order": "a",
                },
            )
            rows = self._parse(payload, capability=capability)
            retrieved_at = self._clock.utcnow()
            prices = tuple(
                map_daily_price(
                    row,
                    mapping=mapping,
                    currency=currency,
                    retrieved_at=retrieved_at,
                )
                for row in rows
                if start <= row.date <= end
            )
            prices = tuple(sorted(prices, key=lambda price: price.trading_date))
            if latest and prices:
                prices = (prices[-1],)
            return prices

        outcome = await self._retry.execute(operation)
        retrieved_at = outcome.value[0].retrieved_at if outcome.value else self._clock.utcnow()
        await self._cache.set(key, _CachedPrices(outcome.value, retrieved_at), ttl=ttl)
        return self._result(
            outcome.value,
            capability=capability,
            correlation_id=correlation_id,
            retrieved_at=retrieved_at,
            cache_status=(CacheStatus.STALE_REJECTED if lookup.stale else CacheStatus.MISS),
            retry_count=outcome.retry_count,
            provider_call_cost=(outcome.retry_count + 1) * self._settings.provider_call_cost,
        )

    async def _context(
        self,
        workspace_id: UUID,
        listing_id: UUID,
        mapping_id: UUID,
        capability: MarketDataCapability,
    ) -> tuple[ProviderInstrumentMapping, str]:
        mapping = await self._mappings.get_mapping(workspace_id, mapping_id)
        if mapping is None or mapping.listing_id != listing_id:
            raise MarketDataNotFoundError(
                "Provider mapping was not found",
                provider=MarketDataProvider.EODHD,
                capability=capability,
            )
        if (
            mapping.provider is not MarketDataProvider.EODHD
            or mapping.status is not MappingStatus.ACTIVE
        ):
            raise MarketDataMappingError(
                "Provider mapping is not active for EODHD",
                provider=MarketDataProvider.EODHD,
                capability=capability,
            )
        currency = await self._currencies.get_currency(workspace_id, listing_id)
        if currency is None:
            raise MarketDataMappingError(
                "Listing currency could not be resolved",
                provider=MarketDataProvider.EODHD,
                capability=capability,
            )
        return mapping, currency

    @staticmethod
    def _parse(
        payload: object, *, capability: MarketDataCapability
    ) -> tuple[EodhdDailyPriceDto, ...]:
        try:
            rows = _DTO_LIST.validate_python(payload)
        except ValidationError as exc:
            raise MarketDataInvalidResponseError(
                "EODHD daily-price response has an invalid structure",
                provider=MarketDataProvider.EODHD,
                capability=capability,
                retryable=False,
            ) from exc
        return tuple(rows)

    @staticmethod
    def _result(
        prices: tuple[DailyPrice, ...],
        *,
        capability: MarketDataCapability,
        correlation_id: UUID,
        retrieved_at: datetime,
        cache_status: CacheStatus,
        retry_count: int,
        provider_call_cost: int,
    ) -> MarketDataResult[tuple[DailyPrice, ...]]:
        warnings = () if prices else ("Provider returned no completed daily prices",)
        quality = QualityStatus.VALID if prices else QualityStatus.INCOMPLETE
        return MarketDataResult(
            data=prices,
            provider=MarketDataProvider.EODHD,
            capability=capability,
            correlation_id=correlation_id,
            retrieved_at=retrieved_at,
            cache_status=cache_status,
            quality_status=quality,
            warnings=warnings,
            retry_count=retry_count,
            provider_call_cost=provider_call_cost,
        )
