"""Conservative discovery for stock listings using existing venue evidence."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from app.features.market.domain.enums import LifecycleStatus
from app.features.market.persistence.models import ListingModel, UnderlyingModel
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.persistence.models import ProviderInstrumentMappingModel
from app.features.market_data.service.administration import (
    MappingCommand,
    ProviderMappingAdministrationService,
)
from app.features.market_data.service.instrument_identity import MarketDataInstrumentIdentityService
from app.features.market_data.service.unit_of_work import SqlAlchemyMarketDataUnitOfWork
from app.features.market_data.service.venue_reconciliation import (
    ProviderVenueReconciliationService,
    VenueReconciliationStatus,
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
        results = await container.eodhd.adapter.search_instruments(underlying.isin, limit=20)
        uow = SqlAlchemyMarketDataUnitOfWork(session)
        reconciliation = ProviderVenueReconciliationService(uow)
        matches = []
        for result in results:
            if (
                result.isin != underlying.isin
                or result.currency != listing.currency_code
                or (result.instrument_type or "").lower() not in {"common stock", "stock"}
            ):
                continue
            venue = await reconciliation.reconcile(
                workspace_id, listing_id, MarketDataProvider.EODHD, result.provider_exchange_code
            )
            if venue.status is VenueReconciliationStatus.MATCHED:
                matches.append(result)
        identities = {(m.provider_symbol, m.provider_exchange_code) for m in matches}
        if len(identities) != 1:
            return {"status": "BLOCKED", "reason": "UNAMBIGUOUS_ISIN_CURRENCY_VENUE_MATCH_REQUIRED"}
        symbol, exchange = next(iter(identities))
        service = ProviderMappingAdministrationService(
            uow,
            resolver=container.eodhd.adapter,
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
            "status": "AVAILABLE" if mapping.status.value == "ACTIVE" else "BLOCKED",
            "reason": "EODHD_MAPPING_" + mapping.status.value,
        }
