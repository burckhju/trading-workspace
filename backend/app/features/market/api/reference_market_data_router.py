"""Public MarketReference market-data and analysis live paths."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.features.analysis.api.dtos import RunAnalysisRequest, RunSummaryResponse
from app.features.analysis.api.errors import translate_analysis_error
from app.features.analysis.domain.errors import AnalysisError
from app.features.analysis.service.reference_application import MarketReferenceAnalysisService
from app.features.market.api.dependencies import (
    get_market_reference_analysis_service,
    get_reference_market_data_service,
)
from app.features.market.api.top_down_market_data_dtos import (
    ReferenceAnalysisResponse,
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


def _run_summary(model: object) -> RunSummaryResponse:
    return RunSummaryResponse(
        version=model.version,  # type: ignore[attr-defined]
        status=model.status,  # type: ignore[attr-defined]
        quality_status=model.quality_status,  # type: ignore[attr-defined]
        model_id=model.model_id,  # type: ignore[attr-defined]
        model_version=model.model_version,  # type: ignore[attr-defined]
        observation_count=model.observation_count,  # type: ignore[attr-defined]
        analysis_time=model.analysis_time,  # type: ignore[attr-defined]
        input_hash=model.input_hash,  # type: ignore[attr-defined]
    )


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


@router.post(
    "/market-references/{reference_id}/analyses",
    response_model=ReferenceAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_reference_analysis(
    reference_id: UUID,
    service: Annotated[
        MarketReferenceAnalysisService,
        Depends(get_market_reference_analysis_service),
    ],
    actor: Annotated[str | None, Header(alias="X-Actor-Name")] = None,
) -> ReferenceAnalysisResponse:
    try:
        value = await service.create_for_market_reference(
            workspace_id=WORKSPACE_ID,
            market_reference_id=reference_id,
            actor=actor or "Trading Workspace User",
        )
    except AnalysisError as error:
        raise translate_analysis_error(error) from error
    instrument_id = value.market_data_instrument_id
    if instrument_id is None:
        raise AssertionError("MarketReference analysis has no market-data instrument")
    return ReferenceAnalysisResponse(
        market_reference_id=reference_id,
        analysis_id=value.id,
        market_data_instrument_id=instrument_id,
        created_at=value.created_at,
        created_by=value.created_by,
    )


@router.post(
    "/market-reference-analyses/{analysis_id}/runs",
    response_model=RunSummaryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def run_reference_analysis(
    analysis_id: UUID,
    body: RunAnalysisRequest,
    service: Annotated[
        MarketReferenceAnalysisService,
        Depends(get_market_reference_analysis_service),
    ],
    correlation_id: Annotated[str | None, Header(alias="X-Correlation-ID")] = None,
) -> RunSummaryResponse:
    if body.end_date < body.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must not precede start_date",
        )
    try:
        value = await service.run_market_reference(
            workspace_id=WORKSPACE_ID,
            analysis_id=analysis_id,
            start_date=body.start_date,
            end_date=body.end_date,
            parameters=body.parameters.to_domain(),
            correlation_id=correlation_id,
        )
    except AnalysisError as error:
        raise translate_analysis_error(error) from error
    return _run_summary(value)