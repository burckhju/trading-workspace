"""Application-service orchestration for provider-backed daily market data."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from app.features.market_data.domain.enums import (
    CacheStatus,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.persistence.mapping import (
    apply_daily_price,
    daily_price_to_model,
)
from app.features.market_data.service.contracts import HistoricalDailyPriceProvider
from app.features.market_data.service.errors import (
    MarketDataMappingError,
    MarketDataNotFoundError,
)
from app.features.market_data.service.types import DailyPriceRequest
from app.features.market_data.service.unit_of_work import MarketDataUnitOfWork

Clock = Callable[[], datetime]
IdFactory = Callable[[], UUID]


@dataclass(frozen=True, slots=True)
class DailyPriceImportResult:
    """Summarize one traceable, idempotent daily-price import."""

    workspace_id: UUID
    listing_id: UUID
    mapping_id: UUID
    start_date: date
    end_date: date
    inserted: int
    updated: int
    unchanged: int
    provider: MarketDataProvider
    cache_status: CacheStatus
    quality_status: QualityStatus
    warnings: tuple[str, ...]
    retry_count: int
    provider_call_cost: int | None
    retrieved_at: datetime

    @property
    def processed(self) -> int:
        """Return the number of provider rows evaluated by persistence."""
        return self.inserted + self.updated + self.unchanged


class DailyPriceImportService:
    """Fetch validated EOD prices and persist them in one explicit transaction."""

    def __init__(
        self,
        *,
        uow: MarketDataUnitOfWork,
        provider: HistoricalDailyPriceProvider,
        clock: Clock = lambda: datetime.now(UTC),
        id_factory: IdFactory = uuid4,
    ) -> None:
        self._uow = uow
        self._provider = provider
        self._clock = clock
        self._id_factory = id_factory

    async def import_daily_prices(self, request: DailyPriceRequest) -> DailyPriceImportResult:
        """Load one approved mapping, fetch its range and idempotently upsert prices."""
        async with self._uow:
            mapping = await self._uow.mappings.get(request.workspace_id, request.mapping_id)
            if mapping is None or mapping.listing_id != request.listing_id:
                raise MarketDataNotFoundError(
                    "Provider mapping was not found",
                    capability=None,
                )
            market_data_instrument_id = getattr(mapping, "market_data_instrument_id", None)

            result = await self._provider.get_daily_prices(request)
            now = self._clock()
            inserted = 0
            updated = 0
            unchanged = 0

            for price in result.data:
                if price.listing_id != request.listing_id:
                    raise MarketDataMappingError(
                        "Provider result belongs to a different listing",
                        provider=result.provider,
                        capability=result.capability,
                    )
                existing = await self._uow.daily_prices.get(
                    request.workspace_id,
                    request.listing_id,
                    price.trading_date,
                    price.price_type,
                )
                if existing is None:
                    await self._uow.daily_prices.add(
                        daily_price_to_model(
                            price,
                            workspace_id=request.workspace_id,
                            price_id=self._id_factory(),
                            now=now,
                            market_data_instrument_id=market_data_instrument_id,
                        )
                    )
                    inserted += 1
                else:
                    identity_changed = False
                    if (
                        existing.market_data_instrument_id is None
                        and market_data_instrument_id is not None
                    ):
                        existing.market_data_instrument_id = market_data_instrument_id
                        existing.updated_at = now
                        identity_changed = True
                    if apply_daily_price(existing, price, now=now) or identity_changed:
                        updated += 1
                    else:
                        unchanged += 1

            if inserted or updated:
                await self._uow.daily_prices.flush()
                await self._uow.commit()

            return DailyPriceImportResult(
                workspace_id=request.workspace_id,
                listing_id=request.listing_id,
                mapping_id=request.mapping_id,
                start_date=request.start_date,
                end_date=request.end_date,
                inserted=inserted,
                updated=updated,
                unchanged=unchanged,
                provider=result.provider,
                cache_status=result.cache_status,
                quality_status=result.quality_status,
                warnings=result.warnings,
                retry_count=result.retry_count,
                provider_call_cost=result.provider_call_cost,
                retrieved_at=result.retrieved_at,
            )
