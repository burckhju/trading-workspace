"""Frankfurt monitoring quotes behind the existing WarrantListingQuoteProvider port."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from app.core.config.frankfurt import FrankfurtQuoteSettings, FrankfurtSourceMode
from app.database import DatabaseManager
from app.features.market.persistence.models import TradingVenueModel
from app.features.market_data.domain.enums import (
    CacheStatus,
    MappingStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.persistence.models import WarrantProviderMappingModel
from app.features.market_data.service.errors import (
    MarketDataConfigurationError,
    MarketDataInvalidResponseError,
    MarketDataMappingError,
    MarketDataNotFoundError,
)
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest
from app.features.product.domain.models import WarrantLifecycle
from app.features.product.persistence.models import WarrantListingModel, WarrantModel
from app.providers.frankfurt_quotes.client import FrankfurtSnapshotClient, utc_now
from app.providers.frankfurt_quotes.public import PUBLIC_EXCHANGE_CODE, assess_public_price
from app.providers.frankfurt_quotes.schema import (
    FRANKFURT_MIC,
    FrankfurtObservation,
    FrankfurtSourceError,
    QuoteStatus,
    assess_snapshot,
)

PROVIDER = MarketDataProvider.FRANKFURT_QUOTES
CAPABILITY = MarketDataCapability.WARRANT_LISTING_QUOTE


@dataclass(frozen=True, slots=True)
class FrankfurtIdentity:
    listing_id: UUID
    isin: str
    wkn: str | None
    currency: str


class FrankfurtWarrantQuoteAdapter:
    def __init__(
        self,
        *,
        database: DatabaseManager,
        settings: FrankfurtQuoteSettings,
        snapshots: FrankfurtSnapshotClient | None = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._database = database
        self.settings = settings
        self.snapshots = snapshots or FrankfurtSnapshotClient(settings, clock=clock)
        self._clock = clock

    async def _identity(self, request: WarrantQuoteRequest) -> FrankfurtIdentity:
        async with self._database.session_context() as session:
            row = (
                await session.execute(
                    select(
                        WarrantListingModel,
                        WarrantModel,
                        WarrantProviderMappingModel,
                        TradingVenueModel,
                    )
                    .join(WarrantModel, WarrantModel.id == WarrantListingModel.warrant_id)
                    .join(
                        TradingVenueModel,
                        TradingVenueModel.id == WarrantListingModel.trading_venue_id,
                    )
                    .join(
                        WarrantProviderMappingModel,
                        WarrantProviderMappingModel.warrant_listing_id == WarrantListingModel.id,
                    )
                    .where(
                        WarrantListingModel.id == request.warrant_listing_id,
                        WarrantListingModel.workspace_id == request.workspace_id,
                        WarrantListingModel.lifecycle_status == WarrantLifecycle.ACTIVE,
                        WarrantModel.workspace_id == request.workspace_id,
                        WarrantProviderMappingModel.workspace_id == request.workspace_id,
                        WarrantProviderMappingModel.provider == PROVIDER,
                        WarrantProviderMappingModel.status == MappingStatus.ACTIVE,
                    )
                )
            ).one_or_none()
        if row is None:
            raise MarketDataNotFoundError(
                "FRANKFURT_ACTIVE_MAPPING_NOT_FOUND", provider=PROVIDER, capability=CAPABILITY
            )
        listing, warrant, mapping, venue = row
        exchange_code = (
            PUBLIC_EXCHANGE_CODE
            if self.settings.source_mode is FrankfurtSourceMode.PUBLIC_WEBSITE
            else FRANKFURT_MIC
        )
        if (
            venue.mic != FRANKFURT_MIC
            or not warrant.isin
            or mapping.provider_symbol != warrant.isin
            or mapping.provider_exchange_code != exchange_code
            or mapping.validated_at is None
        ):
            raise MarketDataMappingError(
                "FRANKFURT_MAPPING_IDENTITY_INVALID", provider=PROVIDER, capability=CAPABILITY
            )
        return FrankfurtIdentity(
            listing.id, warrant.isin, warrant.wkn, listing.quotation_currency_code
        )

    async def inspect(self, request: WarrantQuoteRequest) -> tuple[FrankfurtObservation, bool]:
        reason = self.settings.readiness_reason
        if reason != "CONFIGURED_NOT_PROBED":
            raise MarketDataConfigurationError(reason, provider=PROVIDER, capability=CAPABILITY)
        identity = await self._identity(request)  # Resolve eligibility before any network I/O.
        try:
            if self.settings.source_mode is FrankfurtSourceMode.PUBLIC_WEBSITE:
                price, retrieved_at, hit = await self.snapshots.load_public(identity.isin)
                return (
                    assess_public_price(
                        price,
                        isin=identity.isin,
                        currency=identity.currency,
                        now=self._clock(),
                        retrieved_at=retrieved_at,
                        max_age_seconds=self.settings.max_quote_age_seconds,
                    ),
                    hit,
                )
            snapshot, retrieved_at, hit = await self.snapshots.load()
            observation = assess_snapshot(
                snapshot,
                isin=identity.isin,
                wkn=identity.wkn,
                currency=identity.currency,
                now=self._clock(),  # Reassess actual age even when the transport cache hits.
                retrieved_at=retrieved_at,
                max_age_seconds=self.settings.max_quote_age_seconds,
            )
        except FrankfurtSourceError as exc:
            raise MarketDataInvalidResponseError(
                str(exc), provider=PROVIDER, capability=CAPABILITY
            ) from None
        return observation, hit

    async def get_warrant_listing_quote(
        self, request: WarrantQuoteRequest
    ) -> MarketDataResult[WarrantQuoteSnapshot | None]:
        observation, hit = await self.inspect(request)
        quote = None
        if observation.status is QuoteStatus.AVAILABLE:
            record = observation.record
            assert record is not None and observation.observed_at is not None
            quote = WarrantQuoteSnapshot(
                warrant_listing_id=request.warrant_listing_id,
                isin=record.isin,
                wkn=record.wkn,
                bid=record.bid,
                ask=record.ask,
                currency=record.currency,
                provider_symbol=record.isin,
                provider_exchange_code=FRANKFURT_MIC,
                observed_at=observation.observed_at,
                trading_status=record.trading_status,
                source_mode=(
                    "FRANKFURT_DELAYED_MONITORING"
                    if observation.declared_delay_seconds
                    else "FRANKFURT_REALTIME_MONITORING"
                ),
            )
        return MarketDataResult(
            data=quote,
            provider=PROVIDER,
            capability=CAPABILITY,
            correlation_id=request.correlation_id,
            retrieved_at=observation.retrieved_at,
            cache_status=CacheStatus.HIT if hit else CacheStatus.MISS,
            quality_status=QualityStatus.VALID if quote is not None else QualityStatus.INCOMPLETE,
            warnings=(observation.reason, f"source={observation.source}", "NOT_EXECUTABLE"),
            reason_code=observation.reason,
            retry_count=0,
            provider_call_cost=None,  # No invented claim that a vendor feed is free.
        )
