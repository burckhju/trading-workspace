"""Conservative stock discovery using official, instrument-specific venue evidence."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
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
) -> dict[str, Any]:
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
        result = await container.eodhd.adapter.stock_catalog.discover_with_search(
            isin=underlying.isin, currency=listing.currency_code, mic=venue.mic
        )
        details: dict[str, Any] = {
            "isin": underlying.isin,
            "listing_currency": listing.currency_code,
            "listing_mic": venue.mic,
            "discovery_source": "EODHD_OFFICIAL_STOCK_CATALOG",
            "provider_exchange_code": result.provider_exchange_code or "",
            "matching_isin_count": str(result.matching_isin_count),
            "candidate_currencies": ",".join(result.candidate_currencies),
        }
        if result.search_endpoint is not None:
            details.update(
                search_endpoint=result.search_endpoint,
                search_retrieved_at=(
                    result.search_retrieved_at.isoformat() if result.search_retrieved_at else None
                ),
                search_reason=result.search_reason,
                alternative_candidates=[
                    {
                        "isin": underlying.isin,
                        "provider": MarketDataProvider.EODHD.value,
                        "provider_identity": candidate.provider_symbol,
                        "provider_exchange_code": candidate.provider_exchange_code,
                        "mic": candidate.mic,
                        "currency": candidate.currency,
                        "identity_verified": candidate.identity is not None,
                        "reason": candidate.reason,
                        "same_currency": candidate.currency == listing.currency_code,
                        "same_venue": candidate.mic == venue.mic,
                        "requires_listing_review": (
                            candidate.mic != venue.mic
                            or candidate.currency != listing.currency_code
                        ),
                        "requires_rule_currency_review": candidate.currency
                        != listing.currency_code,
                        "catalog_endpoint": (
                            candidate.identity.endpoint if candidate.identity else None
                        ),
                        "catalog_retrieved_at": (
                            candidate.identity.catalog_retrieved_at.isoformat()
                            if candidate.identity
                            else None
                        ),
                        "execution_usable": False,
                    }
                    for candidate in result.alternatives
                ],
            )
        if result.identity is None:
            return {**details, "status": "BLOCKED", "reason": result.reason}
        identity = result.identity
        details["discovery_source"] = identity.source
        symbol = identity.item.provider_symbol
        exchange = identity.item.provider_exchange_code
        owner = await session.scalar(
            select(ProviderInstrumentMappingModel).where(
                ProviderInstrumentMappingModel.workspace_id == workspace_id,
                ProviderInstrumentMappingModel.provider == MarketDataProvider.EODHD,
                ProviderInstrumentMappingModel.provider_symbol == symbol,
                ProviderInstrumentMappingModel.provider_exchange_code == exchange,
            )
        )
        if owner is not None:
            return {
                **details,
                "status": "BLOCKED",
                "reason": "EODHD_PROVIDER_IDENTITY_ALREADY_MAPPED",
                "mapping_id": str(owner.id),
                "provider_identity": symbol,
                "owner_listing_id": str(owner.listing_id),
            }
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
