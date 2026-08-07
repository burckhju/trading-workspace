"""Application-level dependency container."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta
from random import Random

import httpx
from pydantic import ValidationError

from app.core.config import Settings
from app.database import DatabaseManager
from app.features.market_data.domain.enums import (
    MarketDataCapability,
    MarketDataProvider,
)
from app.features.market_data.service.administration import (
    ProviderMappingAdministrationService,
)
from app.features.market_data.service.application import DailyPriceImportService
from app.features.market_data.service.errors import MarketDataConfigurationError
from app.features.market_data.service.unit_of_work import SqlAlchemyMarketDataUnitOfWork
from app.providers.eodhd.adapter import EodhdAdapterSettings, EodhdMarketDataAdapter
from app.providers.eodhd.client import EodhdClient, create_http_client
from app.providers.eodhd.dto import EodhdUserDto
from app.providers.eodhd.persistence import (
    SqlAlchemyListingCurrencyReader,
    SqlAlchemyMappingReader,
)
from app.providers.shared.budget import DailyCallBudget
from app.providers.shared.cache import InMemoryTtlCache
from app.providers.shared.clock import AsyncioSleeper, SystemClock
from app.providers.shared.metrics import ProviderMetrics
from app.providers.shared.rate_limit import TokenBucketRateLimiter
from app.providers.shared.retry import RetryPolicy


@dataclass(frozen=True, slots=True)
class EodhdRuntime:
    """Own process-wide EODHD transport and resilience components."""

    http_client: httpx.AsyncClient
    adapter: EodhdMarketDataAdapter
    call_budget: DailyCallBudget
    client: EodhdClient
    metrics: ProviderMetrics

    async def close(self) -> None:
        """Close the shared HTTP connection pool."""
        await self.http_client.aclose()


@dataclass(frozen=True, slots=True)
class ApplicationContainer:
    """Own process-wide technical dependencies and their lifecycle."""

    settings: Settings
    database: DatabaseManager
    eodhd: EodhdRuntime | None = None

    @classmethod
    def build(cls, settings: Settings) -> ApplicationContainer:
        """Build the technical dependency graph for one application instance."""
        database = DatabaseManager(settings)
        runtime = cls._build_eodhd(settings, database)
        return cls(settings=settings, database=database, eodhd=runtime)

    @staticmethod
    def _build_eodhd(settings: Settings, database: DatabaseManager) -> EodhdRuntime | None:
        provider_settings = settings.market_data.eodhd
        if not provider_settings.enabled:
            return None
        if provider_settings.api_key is None:
            raise MarketDataConfigurationError(
                "EODHD is enabled but no API key is configured",
                provider=MarketDataProvider.EODHD,
            )

        clock = SystemClock()
        sleeper = AsyncioSleeper()
        http_client = create_http_client(provider_settings)
        client = EodhdClient(settings=provider_settings, client=http_client)
        effective_budget = (
            provider_settings.daily_call_limit - provider_settings.daily_call_safety_reserve
        )
        call_budget = DailyCallBudget(
            configured_budget=effective_budget,
            safety_reserve_percent=0,
            clock=clock,
            provider=MarketDataProvider.EODHD,
        )
        adapter = EodhdMarketDataAdapter(
            client=client,
            mappings=SqlAlchemyMappingReader(database),
            currencies=SqlAlchemyListingCurrencyReader(database),
            cache=InMemoryTtlCache(clock=clock),
            retry_policy=RetryPolicy(
                clock=clock,
                sleeper=sleeper,
                random=Random(),
                max_attempts=provider_settings.retry_max_attempts,
                base_delay_seconds=provider_settings.retry_base_delay_seconds,
                max_retry_after_seconds=(provider_settings.retry_max_retry_after_seconds),
                total_timeout_seconds=provider_settings.retry_total_timeout_seconds,
            ),
            rate_limiter=TokenBucketRateLimiter(
                requests_per_second=provider_settings.requests_per_minute / 60,
                burst_capacity=provider_settings.rate_limit_burst_capacity,
                clock=clock,
                sleeper=sleeper,
            ),
            call_budget=call_budget,
            clock=clock,
            settings=EodhdAdapterSettings(
                historical_ttl=timedelta(seconds=provider_settings.historical_cache_ttl_seconds),
                latest_ttl=timedelta(seconds=provider_settings.latest_cache_ttl_seconds),
                provider_call_cost=provider_settings.historical_eod_call_cost,
            ),
        )
        return EodhdRuntime(
            http_client=http_client,
            adapter=adapter,
            call_budget=call_budget,
            client=client,
            metrics=ProviderMetrics(),
        )

    def require_eodhd_adapter(self) -> EodhdMarketDataAdapter:
        """Return the configured adapter or a stable configuration error."""
        if self.eodhd is None:
            raise MarketDataConfigurationError(
                "EODHD provider is disabled",
                provider=MarketDataProvider.EODHD,
            )
        return self.eodhd.adapter

    @asynccontextmanager
    async def daily_price_import_service(
        self,
    ) -> AsyncIterator[DailyPriceImportService]:
        """Create a session-scoped import service with one explicit unit of work."""
        async with self.database.session_context() as session:
            yield DailyPriceImportService(
                uow=SqlAlchemyMarketDataUnitOfWork(session),
                provider=self.require_eodhd_adapter(),
            )

    @asynccontextmanager
    async def provider_mapping_service(
        self,
    ) -> AsyncIterator[ProviderMappingAdministrationService]:
        """Create a session-scoped administrative mapping service."""
        async with self.database.session_context() as session:
            yield ProviderMappingAdministrationService(
                uow=SqlAlchemyMarketDataUnitOfWork(session),
                resolver=self.require_eodhd_adapter(),
            )

    async def synchronize_eodhd_account_usage(self) -> dict[str, int]:
        """Synchronize local usage with the non-secret EODHD User API counters."""
        if self.eodhd is None:
            raise MarketDataConfigurationError(
                "EODHD provider is disabled", provider=MarketDataProvider.EODHD
            )
        payload = await self.eodhd.client.get_json(
            "/user/",
            capability=MarketDataCapability.INSTRUMENT_MAPPING_VALIDATION,
            params={"fmt": "json"},
        )
        try:
            user = EodhdUserDto.model_validate(payload)
        except ValidationError as exc:
            raise MarketDataConfigurationError(
                "EODHD User API returned invalid account data",
                provider=MarketDataProvider.EODHD,
            ) from exc
        used = await self.eodhd.call_budget.synchronize_usage(
            user.apiRequests, usage_day=user.apiRequestsDate
        )
        await self.eodhd.metrics.increment("user_api_syncs")
        return {
            "api_requests": used,
            "daily_rate_limit": user.dailyRateLimit,
            "extra_limit": user.extraLimit,
        }

    async def provider_status(
        self,
    ) -> dict[str, int | bool | str | dict[str, int]]:
        """Return non-secret EODHD runtime and budget status."""
        settings = self.settings.market_data.eodhd
        used = await self.eodhd.call_budget.usage() if self.eodhd else 0
        effective = max(settings.daily_call_limit - settings.daily_call_safety_reserve, 0)
        metrics = await self.eodhd.metrics.snapshot() if self.eodhd else {}
        return {
            "provider": MarketDataProvider.EODHD,
            "enabled": settings.enabled,
            "configured": settings.api_key is not None,
            "daily_limit": settings.daily_call_limit,
            "safety_reserve": settings.daily_call_safety_reserve,
            "effective_budget": effective,
            "used_today": used,
            "remaining_today": max(effective - used, 0),
            "requests_per_minute": settings.requests_per_minute,
            "burst_capacity": settings.rate_limit_burst_capacity,
            "single_instance_only": True,
            "metrics": metrics,
        }

    async def close(self) -> None:
        """Release resources owned by the container in dependency order."""
        if self.eodhd is not None:
            await self.eodhd.close()
        await self.database.dispose()
