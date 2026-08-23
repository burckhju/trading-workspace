"""FastAPI dependencies for provider-independent market-data services."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from app.core.di import ApplicationContainer, get_container
from app.features.market_data.api.errors import translate_market_data_error
from app.features.market_data.service.administration import (
    ProviderMappingAdministrationService,
)
from app.features.market_data.service.application import DailyPriceImportService
from app.features.market_data.service.errors import MarketDataError
from app.features.market_data.service.venue_reconciliation import (
    ProviderVenueReconciliationService,
)


async def get_daily_price_import_service(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> AsyncIterator[DailyPriceImportService]:
    """Yield one session-scoped import service and translate provider setup failures."""
    try:
        async with container.daily_price_import_service() as service:
            yield service
    except MarketDataError as error:
        raise translate_market_data_error(error) from error


async def get_provider_mapping_service(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> AsyncIterator[ProviderMappingAdministrationService]:
    """Yield one session-scoped administrative mapping service."""
    async with container.provider_mapping_service() as service:
        yield service


async def get_provider_venue_reconciliation_service(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> AsyncIterator[ProviderVenueReconciliationService]:
    """Yield one session-scoped read-only venue-reconciliation service."""
    async with container.provider_venue_reconciliation_service() as service:
        yield service
