"""Public MarketReference market-data live paths."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.features.market.api.dependencies import get_reference_market_data_service
from app.features.market.api.top_down_market_data_dtos import (
    ReferenceDailyPriceImportRequest,
    ReferenceDailyPriceImportResponse,
    ReferenceProviderMappingRequest,
    ReferenceProviderMappingResponse,
)
from app.features.market_data.service.reference_market_data import ReferenceMarketDataService

router = APIRouter(prefix="/api/v1/top-down-reference-data", tags=["top-down-reference-data"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


def _http_error(error: ValueError) -> HTTPException:
    message = str(error)
    code = (
        status.HTTP_404_NOT_FOUND
        if "not found" in message
        else status.HTTP_422_UNPROCESSABLE_ENTITY
    )
    return HTTPException(status_code=code, detail=message)


@router.put(
    "/market-references/{reference_id}/provider-mapping/eodhd",
    response_model=ReferenceProviderMappingResponse,
)
async def upsert_reference_provider_mapping(
    reference_id: UUID,
    body: ReferenceProviderMappingRequest,
    service: Annotated[ReferenceMarketDataService, Depends(get_reference_market_data_service)],
) -> ReferenceProviderMappingResponse:
    try:
        value = await service.upsert_mapping(
            workspace_id=WORKSPACE_ID,
            market_reference_id=reference_id,
            **body.model_dump(),
        )
    except ValueError as error:
        raise _http_error(error) from error
    return ReferenceProviderMappingResponse.model_validate(value)


@router.post(
    "/market-references/{reference_id}/provider-mapping/eodhd/validate",
    response_model=ReferenceProviderMappingResponse,
)
async def validate_reference_provider_mapping(
    reference_id: UUID,
    service: Annotated[ReferenceMarketDataService, Depends(get_reference_market_data_service)],
) -> ReferenceProviderMappingResponse:
    try:
        value = await service.validate_mapping(
            workspace_id=WORKSPACE_ID,
            market_reference_id=reference_id,
        )
    except ValueError as error:
        raise _http_error(error) from error
    return ReferenceProviderMappingResponse.model_validate(value)


@router.post(
    "/market-references/{reference_id}/daily-prices/import",
    response_model=ReferenceDailyPriceImportResponse,
)
async def import_reference_daily_prices(
    reference_id: UUID,
    body: ReferenceDailyPriceImportRequest,
    service: Annotated[ReferenceMarketDataService, Depends(get_reference_market_data_service)],
) -> ReferenceDailyPriceImportResponse:
    try:
        value = await service.import_daily_prices(
            workspace_id=WORKSPACE_ID,
            market_reference_id=reference_id,
            **body.model_dump(),
        )
    except ValueError as error:
        raise _http_error(error) from error
    return ReferenceDailyPriceImportResponse.from_result(value)
