"""Read-only controlled reference-data endpoints used by FT-001."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.features.market.api.dependencies import get_reference_data_service
from app.features.market.api.dtos import (
    CurrencyListResponse,
    CurrencyResponse,
    TradingVenueListResponse,
    TradingVenueResponse,
)
from app.features.market.service.reference_data_service import ReferenceDataService

router = APIRouter(
    prefix="/api/v1/market-reference-data", tags=["market-reference-data"]
)


@router.get("/trading-venues", response_model=TradingVenueListResponse)
async def list_trading_venues(
    service: Annotated[ReferenceDataService, Depends(get_reference_data_service)],
) -> TradingVenueListResponse:
    items = await service.list_active_trading_venues()
    return TradingVenueListResponse(
        items=[TradingVenueResponse.model_validate(item) for item in items]
    )


@router.get("/currencies", response_model=CurrencyListResponse)
async def list_currencies(
    service: Annotated[ReferenceDataService, Depends(get_reference_data_service)],
) -> CurrencyListResponse:
    items = await service.list_active_currencies()
    return CurrencyListResponse(
        items=[CurrencyResponse.model_validate(item) for item in items]
    )
