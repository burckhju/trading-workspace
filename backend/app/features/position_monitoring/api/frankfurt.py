"""Read-only configuration health and exact-listing Frankfurt quote diagnostics."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.di import ApplicationContainer, get_container
from app.features.market_data.service.errors import (
    MarketDataConfigurationError,
    MarketDataInvalidResponseError,
    MarketDataMappingError,
    MarketDataNotFoundError,
)
from app.features.market_data.service.types import WarrantQuoteRequest
from app.providers.frankfurt_quotes.client import utc_now
from app.providers.frankfurt_quotes.schema import (
    SCHEMA_VERSION,
    FrankfurtObservation,
    QuoteStatus,
)

router = APIRouter()


class FrankfurtHealthResponse(BaseModel):
    provider: Literal["FRANKFURT_QUOTES"] = "FRANKFURT_QUOTES"
    enabled: bool
    reason: str
    source_name: str | None
    schema_version: str = SCHEMA_VERSION
    max_quote_age_seconds: int
    last_success_at: datetime | None
    last_error: str | None
    # A successful transport request is not an instrument-coverage or freshness check.
    coverage_verified: Literal[False] = False
    execution_usable: Literal[False] = False


class FrankfurtProbeResponse(BaseModel):
    workspace_id: UUID
    warrant_listing_id: UUID
    correlation_id: UUID
    status: QuoteStatus
    reason: str
    observation: FrankfurtObservation | None = None
    cache_hit: bool = False


@router.get("/quote-sources/frankfurt/health", response_model=FrankfurtHealthResponse)
async def get_frankfurt_health(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> FrankfurtHealthResponse:
    settings = container.settings.market_data.frankfurt
    client = container.frankfurt.snapshots if container.frankfurt is not None else None
    return FrankfurtHealthResponse(
        enabled=settings.enabled,
        reason=settings.readiness_reason,
        source_name=settings.source_name,
        max_quote_age_seconds=settings.max_quote_age_seconds,
        last_success_at=client.last_success_at if client else None,
        last_error=client.last_error if client else None,
    )


@router.get("/quote-sources/frankfurt/listings/{listing_id}", response_model=FrankfurtProbeResponse)
async def get_frankfurt_quote(
    listing_id: UUID,
    workspace_id: UUID,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> FrankfurtProbeResponse:
    correlation_id = uuid4()
    result = FrankfurtProbeResponse(
        workspace_id=workspace_id,
        warrant_listing_id=listing_id,
        correlation_id=correlation_id,
        status=QuoteStatus.UNAVAILABLE,
        reason=container.settings.market_data.frankfurt.readiness_reason,
    )
    if container.frankfurt is None:
        return result
    try:
        observation, hit = await container.frankfurt.inspect(
            WarrantQuoteRequest(workspace_id, listing_id, correlation_id, utc_now())
        )
    except (MarketDataConfigurationError, MarketDataNotFoundError) as exc:
        result.reason = str(exc)
    except (MarketDataInvalidResponseError, MarketDataMappingError) as exc:
        result.status = QuoteStatus.ERROR
        result.reason = str(exc)
    else:
        result.observation = observation
        result.status = observation.status
        result.reason = observation.reason
        result.cache_hit = hit
    return result
