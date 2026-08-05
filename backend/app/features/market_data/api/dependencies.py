"""FastAPI dependencies for provider-independent market-data services."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from app.core.di import ApplicationContainer, get_container
from app.features.market_data.service.application import DailyPriceImportService


async def get_daily_price_import_service(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> AsyncIterator[DailyPriceImportService]:
    """Yield one session-scoped import service and close its DB session afterwards."""
    async with container.daily_price_import_service() as service:
        yield service

from app.features.market_data.service.administration import ProviderMappingAdministrationService


async def get_provider_mapping_service(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> AsyncIterator[ProviderMappingAdministrationService]:
    """Yield one session-scoped administrative mapping service."""
    async with container.provider_mapping_service() as service:
        yield service
