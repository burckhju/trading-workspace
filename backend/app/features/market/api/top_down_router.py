"""Administrative API for semantic top-down reference configuration."""

from dataclasses import asdict
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.features.analysis.service.reference_application import MarketReferenceAnalysisService
from app.features.market.api.dependencies import (
    get_market_reference_analysis_service,
    get_reference_market_data_service,
    get_top_down_reference_administration_service,
    get_top_down_reference_readiness_service,
)
from app.features.market.api.top_down_dtos import (
    ActiveStateRequest,
    AssignmentResponse,
    CreateSectorReferenceRequest,
    CreateSectorRequest,
    MarketReferenceResponse,
    ProviderReferenceSuggestionResponse,
    ReferenceListingAssignmentRequest,
    SectorReferenceAssignmentRequest,
    SectorResponse,
    TopDownReferenceReadinessResponse,
    UnderlyingBenchmarkAssignmentRequest,
    UnderlyingSectorAssignmentRequest,
)
from app.features.market.api.top_down_market_data_dtos import (
    ReferenceAnalysisCreateRequest,
    ReferenceAnalysisResponse,
    ReferenceAnalysisRunRequest,
    ReferenceAnalysisRunResponse,
    ReferenceDailyPriceImportRequest,
    ReferenceDailyPriceImportResponse,
    ReferenceProviderMappingRequest,
    ReferenceProviderMappingResponse,
)
from app.features.market.service.top_down_administration import (
    TopDownReferenceAdministrationService,
)
from app.features.market.service.top_down_readiness import TopDownReferenceReadinessService
from app.features.market_data.service.reference_market_data import ReferenceMarketDataService
from app.providers.eodhd.reference_catalog import TOP_DOWN_V1_EODHD_SUGGESTIONS

router = APIRouter(prefix="/api/v1/top-down-reference-data", tags=["top-down-reference-data"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


def _http_error(error: ValueError) -> HTTPException:
    message = str(error)
    code = (
        status.HTTP_409_CONFLICT
        if "overlap" in message or "already exists" in message
        else status.HTTP_422_UNPROCESSABLE_ENTITY
    )
    return HTTPException(status_code=code, detail=message)


@router.get(
    "/provider-suggestions/eodhd",
    response_model=list[ProviderReferenceSuggestionResponse],
)
async def eodhd_reference_suggestions() -> list[ProviderReferenceSuggestionResponse]:
    """Return provider-boundary hints; mappings still require explicit validation."""
    return [
        ProviderReferenceSuggestionResponse(**asdict(item))
        for item in TOP_DOWN_V1_EODHD_SUGGESTIONS
    ]


@router.get("/readiness", response_model=list[TopDownReferenceReadinessResponse])
async def reference_readiness(
    service: Annotated[
        TopDownReferenceReadinessService,
        Depends(get_top_down_reference_readiness_service),
    ],
) -> list[TopDownReferenceReadinessResponse]:
    values = await service.evaluate(WORKSPACE_ID)
    return [
        TopDownReferenceReadinessResponse.model_validate(item, from_attributes=True)
        for item in values
    ]


@router.get("/market-references", response_model=list[MarketReferenceResponse])
async def list_market_references(
    service: Annotated[
        TopDownReferenceAdministrationService,
        Depends(get_top_down_reference_administration_service),
    ],
) -> list[MarketReferenceResponse]:
    return [
        MarketReferenceResponse.model_validate(item)
        for item in await service.list_market_references(WORKSPACE_ID)
    ]


@router.post("/bootstrap-v1", response_model=list[MarketReferenceResponse])
async def bootstrap_v1(
    service: Annotated[
        TopDownReferenceAdministrationService,
        Depends(get_top_down_reference_administration_service),
    ],
) -> list[MarketReferenceResponse]:
    result = await service.bootstrap_v1(WORKSPACE_ID)
    return [MarketReferenceResponse.model_validate(item) for item in result.market_references]


@router.get("/sectors", response_model=list[SectorResponse])
async def list_sectors(
    service: Annotated[
        TopDownReferenceAdministrationService,
        Depends(get_top_down_reference_administration_service),
    ],
) -> list[SectorResponse]:
    return [
        SectorResponse.model_validate(item) for item in await service.list_sectors(WORKSPACE_ID)
    ]


@router.patch("/market-references/{reference_id}/active", response_model=MarketReferenceResponse)
async def set_market_reference_active(
    reference_id: UUID,
    body: ActiveStateRequest,
    service: Annotated[
        TopDownReferenceAdministrationService,
        Depends(get_top_down_reference_administration_service),
    ],
) -> MarketReferenceResponse:
    try:
        value = await service.set_market_reference_active(
            workspace_id=WORKSPACE_ID,
            market_reference_id=reference_id,
            active=body.active,
        )
    except ValueError as error:
        raise _http_error(error) from error
    return MarketReferenceResponse.model_validate(value)


@router.patch("/sectors/{sector_id}/active", response_model=SectorResponse)
async def set_sector_active(
    sector_id: UUID,
    body: ActiveStateRequest,
    service: Annotated[
        TopDownReferenceAdministrationService,
        Depends(get_top_down_reference_administration_service),
    ],
) -> SectorResponse:
    try:
        value = await service.set_sector_active(
            workspace_id=WORKSPACE_ID, sector_id=sector_id, active=body.active
        )
    except ValueError as error:
        raise _http_error(error) from error
    return SectorResponse.model_validate(value)


@router.post("/sectors", response_model=SectorResponse, status_code=status.HTTP_201_CREATED)
async def create_sector(
    body: CreateSectorRequest,
    service: Annotated[
        TopDownReferenceAdministrationService,
        Depends(get_top_down_reference_administration_service),
    ],
) -> SectorResponse:
    try:
        value = await service.create_sector(workspace_id=WORKSPACE_ID, **body.model_dump())
    except ValueError as error:
        raise _http_error(error) from error
    return SectorResponse.model_validate(value)


@router.post(
    "/sector-references",
    response_model=MarketReferenceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sector_reference(
    body: CreateSectorReferenceRequest,
    service: Annotated[
        TopDownReferenceAdministrationService,
        Depends(get_top_down_reference_administration_service),
    ],
) -> MarketReferenceResponse:
    try:
        value = await service.create_sector_reference(
            workspace_id=WORKSPACE_ID, **body.model_dump()
        )
    except ValueError as error:
        raise _http_error(error) from error
    return MarketReferenceResponse.model_validate(value)


@router.post(
    "/market-references/{reference_id}/listing-assignments",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_reference_listing(
    reference_id: UUID,
    body: ReferenceListingAssignmentRequest,
    service: Annotated[
        TopDownReferenceAdministrationService,
        Depends(get_top_down_reference_administration_service),
    ],
) -> AssignmentResponse:
    try:
        value = await service.assign_reference_listing(
            workspace_id=WORKSPACE_ID, market_reference_id=reference_id, **body.model_dump()
        )
    except ValueError as error:
        raise _http_error(error) from error
    return AssignmentResponse.model_validate(value)


@router.post(
    "/underlyings/{underlying_id}/benchmark-assignments",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_underlying_benchmark(
    underlying_id: UUID,
    body: UnderlyingBenchmarkAssignmentRequest,
    service: Annotated[
        TopDownReferenceAdministrationService,
        Depends(get_top_down_reference_administration_service),
    ],
) -> AssignmentResponse:
    try:
        value = await service.assign_underlying_benchmark(
            workspace_id=WORKSPACE_ID, underlying_id=underlying_id, **body.model_dump()
        )
    except ValueError as error:
        raise _http_error(error) from error
    return AssignmentResponse.model_validate(value)


@router.post(
    "/underlyings/{underlying_id}/sector-assignments",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_underlying_sector(
    underlying_id: UUID,
    body: UnderlyingSectorAssignmentRequest,
    service: Annotated[
        TopDownReferenceAdministrationService,
        Depends(get_top_down_reference_administration_service),
    ],
) -> AssignmentResponse:
    try:
        value = await service.assign_underlying_sector(
            workspace_id=WORKSPACE_ID, underlying_id=underlying_id, **body.model_dump()
        )
    except ValueError as error:
        raise _http_error(error) from error
    return AssignmentResponse.model_validate(value)


@router.post(
    "/sectors/{sector_id}/reference-assignments",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_sector_reference(
    sector_id: UUID,
    body: SectorReferenceAssignmentRequest,
    service: Annotated[
        TopDownReferenceAdministrationService,
        Depends(get_top_down_reference_administration_service),
    ],
) -> AssignmentResponse:
    data = body.model_dump(exclude={"source_reference"})
    try:
        value = await service.assign_sector_reference(
            workspace_id=WORKSPACE_ID, sector_id=sector_id, **data
        )
    except ValueError as error:
        raise _http_error(error) from error
    return AssignmentResponse.model_validate(value)


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
    body: ReferenceAnalysisCreateRequest,
    service: Annotated[
        MarketReferenceAnalysisService,
        Depends(get_market_reference_analysis_service),
    ],
) -> ReferenceAnalysisResponse:
    try:
        value = await service.create_for_market_reference(
            workspace_id=WORKSPACE_ID,
            market_reference_id=reference_id,
            actor=body.actor,
        )
    except ValueError as error:
        raise _http_error(error) from error
    return ReferenceAnalysisResponse.model_validate(value)


@router.post(
    "/market-references/{reference_id}/analyses/{analysis_id}/run",
    response_model=ReferenceAnalysisRunResponse,
)
async def run_reference_analysis(
    reference_id: UUID,
    analysis_id: UUID,
    body: ReferenceAnalysisRunRequest,
    service: Annotated[
        MarketReferenceAnalysisService,
        Depends(get_market_reference_analysis_service),
    ],
) -> ReferenceAnalysisRunResponse:
    del reference_id  # identity ownership is validated through analysis.market_data_instrument_id
    try:
        value = await service.run_market_reference(
            workspace_id=WORKSPACE_ID,
            analysis_id=analysis_id,
            start_date=body.start_date,
            end_date=body.end_date,
            parameters=body.to_parameters(),
            correlation_id=body.correlation_id,
        )
    except ValueError as error:
        raise _http_error(error) from error
    return ReferenceAnalysisRunResponse.model_validate(value)
