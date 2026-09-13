"""Conservative stock discovery using official, instrument-specific venue evidence."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from app.features.market.domain.enums import LifecycleStatus
from app.features.market.persistence.models import ListingModel, TradingVenueModel, UnderlyingModel
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.persistence.models import ProviderInstrumentMappingModel
from app.features.market_data.service.administration import (
    MappingCommand,
    ProviderMappingAdministrationService,
)
from app.features.market_data.service.catalog_mapping_validation import CatalogMappingResolver
from app.features.market_data.service.instrument_identity import MarketDataInstrumentIdentityService
from app.features.market_data.service.unit_of_work import SqlAlchemyMarketDataUnitOfWork
from app.features.market_data.service.venue_reconciliation import (
    ProviderVenueReconciliationService,
    VerifiedListingVenue,
)

if TYPE_CHECKING:
    from app.core.di import ApplicationContainer


async def discover_underlying(
    container: ApplicationContainer, workspace_id: UUID, listing_id: UUID
) -> dict[str, str]:
    if container.eodhd is None:
        return {"status": "BLOCKED", "reason": "EODHD_DISABLED"}
    async with container.database.session_context() as session:
        listing = await session.scalar(
            select(ListingModel)
            .where(
                ListingModel.id == listing_id,
                ListingModel.workspace_id == workspace_id,
                ListingModel.lifecycle_status == LifecycleStatus.ACTIVE,
            )
            .with_for_update()
        )
        if listing is None:
            return {"status": "BLOCKED", "reason": "ACTIVE_UNDERLYING_LISTING_REQUIRED"}
        existing = await session.scalar(
            select(ProviderInstrumentMappingModel).where(
                ProviderInstrumentMappingModel.workspace_id == workspace_id,
                ProviderInstrumentMappingModel.listing_id == listing_id,
                ProviderInstrumentMappingModel.provider == MarketDataProvider.EODHD,
            )
        )
        if existing is not None:
            return {
                "status": (
                    "AVAILABLE"
                    if existing.status == MappingStatus.ACTIVE and existing.validated_at is not None
                    else "BLOCKED"
                ),
                "reason": "EXISTING_MAPPING_PRESERVED",
            }
        underlying = await session.get(UnderlyingModel, listing.underlying_id)
        if underlying is None or underlying.workspace_id != workspace_id or not underlying.isin:
            return {"status": "BLOCKED", "reason": "UNDERLYING_ISIN_REQUIRED"}
        if underlying.lifecycle_status != LifecycleStatus.ACTIVE:
            return {"status": "BLOCKED", "reason": "ACTIVE_UNDERLYING_REQUIRED"}
        venue = await session.get(TradingVenueModel, listing.trading_venue_id)
        if venue is None or not venue.is_active:
            return {"status": "BLOCKED", "reason": "ACTIVE_TRADING_VENUE_REQUIRED"}
        result = await container.eodhd.adapter.stock_catalog.discover(
            isin=underlying.isin, currency=listing.currency_code, mic=venue.mic
        )
        details = {
            "isin": underlying.isin,
            "listing_currency": listing.currency_code,
            "listing_mic": venue.mic,
            "discovery_source": "EODHD_OFFICIAL_STOCK_CATALOG",
            "provider_exchange_code": result.provider_exchange_code or "",
            "matching_isin_count": str(result.matching_isin_count),
            "candidate_currencies": ",".join(result.candidate_currencies),
        }
        if result.identity is None:
            return {**details, "status": "BLOCKED", "reason": result.reason}
        identity = result.identity
        symbol = identity.item.provider_symbol
        exchange = identity.item.provider_exchange_code
        uow = SqlAlchemyMarketDataUnitOfWork(session)
        reconciliation = ProviderVenueReconciliationService(
            uow,
            verified_listing=VerifiedListingVenue(
                workspace_id,
                listing_id,
                MarketDataProvider.EODHD,
                exchange,
                venue.id,
            ),
        )
        service = ProviderMappingAdministrationService(
            uow,
            resolver=CatalogMappingResolver(session, workspace_id, listing_id, identity),
            venue_reconciliation=reconciliation,
            instrument_identity=MarketDataInstrumentIdentityService(session),
        )
        mapping = await service.create_or_update(
            MappingCommand(
                workspace_id,
                listing_id,
                MarketDataProvider.EODHD,
                symbol,
                exchange,
                None,
                "Automatic market-data discovery",
            )
        )
        mapping = await service.validate(
            workspace_id, mapping.id, actor_id=None, actor_name="Automatic market-data discovery"
        )
        return {
            **details,
            "status": "AVAILABLE" if mapping.status.value == "ACTIVE" else "BLOCKED",
            "reason": "EODHD_MAPPING_" + mapping.status.value,
            "mapping_id": str(mapping.id),
            "provider_identity": symbol,
            "catalog_endpoint": identity.endpoint,
            "catalog_retrieved_at": identity.catalog_retrieved_at.isoformat(),
        }
