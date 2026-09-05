"""Versioned REST endpoints for provider-independent market-data imports."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.di import ApplicationContainer, get_container
from app.features.market_data.api.dependencies import (
    get_daily_price_import_service,
    get_provider_mapping_service,
    get_provider_venue_reconciliation_service,
)
from app.features.market_data.api.dtos import (
    ImportDailyPricesRequest,
    ImportDailyPricesResponse,
    ProviderInstrumentSearchItemResponse,
    ProviderInstrumentSearchResponse,
    ProviderMappingResponse,
    ProviderMappingStateRequest,
    ProviderMappingUpsertRequest,
    ProviderStatusResponse,
    VenueReconciliationResponse,
)
from app.features.market_data.api.errors import translate_market_data_error
from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.service.administration import (
    MappingCommand,
    ProviderMappingAdministrationService,
)
from app.features.market_data.service.application import DailyPriceImportService
from app.features.market_data.service.errors import MarketDataError
from app.features.market_data.service.types import DailyPriceRequest
from app.features.market_data.service.venue_reconciliation import (
    ProviderVenueReconciliationService,
)

router = APIRouter(prefix="/api/v1/market-data", tags=["market-data"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


@router.post(
    "/daily-prices/import",
    response_model=ImportDailyPricesResponse,
    status_code=status.HTTP_200_OK,
)
async def import_daily_prices(
    body: ImportDailyPricesRequest,
    request: Request,
    service: Annotated[DailyPriceImportService, Depends(get_daily_price_import_service)],
) -> ImportDailyPricesResponse:
    """Import one listing's completed daily prices idempotently."""
    correlation_id = UUID(request.state.request_id)
    try:
        result = await service.import_daily_prices(
            DailyPriceRequest(
                workspace_id=WORKSPACE_ID,
                listing_id=body.listing_id,
                mapping_id=body.mapping_id,
                start_date=body.start_date,
                end_date=body.end_date,
                correlation_id=correlation_id,
            )
        )
    except MarketDataError as error:
        raise translate_market_data_error(error) from error
    return ImportDailyPricesResponse.from_result(result)


@router.get("/instruments/search", response_model=ProviderInstrumentSearchResponse)
async def search_provider_instruments(
    container: Annotated[ApplicationContainer, Depends(get_container)],
    q: Annotated[str, Query(min_length=2, max_length=100)],
    limit: Annotated[int, Query(ge=1, le=20)] = 10,
) -> ProviderInstrumentSearchResponse:
    """Search EODHD without creating or mutating workspace master data."""
    try:
        values = await container.require_eodhd_adapter().search_instruments(q, limit=limit)
    except MarketDataError as error:
        raise translate_market_data_error(error) from error
    return ProviderInstrumentSearchResponse(
        provider=MarketDataProvider.EODHD,
        items=[ProviderInstrumentSearchItemResponse.from_result(value) for value in values],
    )


@router.get("/provider-mappings", response_model=list[ProviderMappingResponse])
async def list_provider_mappings(
    service: Annotated[ProviderMappingAdministrationService, Depends(get_provider_mapping_service)],
) -> list[ProviderMappingResponse]:
    """List administrative provider mappings for the current workspace."""
    values = await service.list_mappings(WORKSPACE_ID)
    return [ProviderMappingResponse.from_domain(value) for value in values]


@router.put("/provider-mappings", response_model=ProviderMappingResponse)
async def upsert_provider_mapping(
    body: ProviderMappingUpsertRequest,
    service: Annotated[ProviderMappingAdministrationService, Depends(get_provider_mapping_service)],
) -> ProviderMappingResponse:
    """Create or update a disabled mapping without modifying listing master data."""
    try:
        value = await service.create_or_update(
            MappingCommand(
                workspace_id=WORKSPACE_ID,
                listing_id=body.listing_id,
                provider=body.provider,
                provider_symbol=body.provider_symbol,
                provider_exchange_code=body.provider_exchange_code,
                actor_id=body.actor_id,
                actor_name=body.actor_name,
            )
        )
    except MarketDataError as error:
        raise translate_market_data_error(error) from error
    return ProviderMappingResponse.from_domain(value)


@router.post("/provider-mappings/{mapping_id}/validate", response_model=ProviderMappingResponse)
async def validate_provider_mapping(
    mapping_id: UUID,
    body: ProviderMappingStateRequest,
    service: Annotated[ProviderMappingAdministrationService, Depends(get_provider_mapping_service)],
) -> ProviderMappingResponse:
    """Validate and activate one mapping through an explicit administrative action."""
    try:
        value = await service.validate(
            WORKSPACE_ID, mapping_id, actor_id=body.actor_id, actor_name=body.actor_name
        )
    except MarketDataError as error:
        raise translate_market_data_error(error) from error
    return ProviderMappingResponse.from_domain(value)


@router.patch("/provider-mappings/{mapping_id}/state", response_model=ProviderMappingResponse)
async def set_provider_mapping_state(
    mapping_id: UUID,
    body: ProviderMappingStateRequest,
    service: Annotated[ProviderMappingAdministrationService, Depends(get_provider_mapping_service)],
) -> ProviderMappingResponse:
    """Enable or disable one mapping without deleting its history."""
    try:
        value = await service.set_enabled(
            WORKSPACE_ID,
            mapping_id,
            enabled=body.enabled,
            actor_id=body.actor_id,
            actor_name=body.actor_name,
        )
    except MarketDataError as error:
        raise translate_market_data_error(error) from error
    return ProviderMappingResponse.from_domain(value)


@router.get(
    "/provider-mappings/{mapping_id}/venue-reconciliation",
    response_model=VenueReconciliationResponse,
)
async def provider_mapping_venue_reconciliation(
    mapping_id: UUID,
    service: Annotated[
        ProviderVenueReconciliationService,
        Depends(get_provider_venue_reconciliation_service),
    ],
) -> VenueReconciliationResponse:
    """Explain venue evidence for one mapping without mutating reference data."""
    try:
        result = await service.reconcile_mapping(WORKSPACE_ID, mapping_id)
    except MarketDataError as error:
        raise translate_market_data_error(error) from error
    return VenueReconciliationResponse.from_result(result)


@router.get("/providers/status", response_model=ProviderStatusResponse)
async def provider_status(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> ProviderStatusResponse:
    """Expose non-secret local EODHD budget and rate-limit status."""
    return ProviderStatusResponse.model_validate(await container.provider_status())
