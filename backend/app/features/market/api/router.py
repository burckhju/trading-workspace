"""Versioned REST endpoints for FT-001 Basiswertverwaltung."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response, status

from app.features.market.api.dependencies import (
    get_listing_service,
    get_underlying_service,
)
from app.features.market.api.dtos import (
    AddListingRequest,
    AuditEventListResponse,
    AuditEventResponse,
    CreateUnderlyingRequest,
    ListingResponse,
    UnderlyingDetailResponse,
    UnderlyingSearchResponse,
    UnderlyingSummaryResponse,
    UnderlyingUsageListResponse,
    UnderlyingUsageResponse,
    UpdateListingRequest,
    UpdateUnderlyingRequest,
    VersionRequest,
    underlying_detail_response,
    underlying_summary_response,
)
from app.features.market.api.errors import translate_market_error
from app.features.market.domain.enums import LifecycleStatus
from app.features.market.service.listing_service import ListingService
from app.features.market.service.service import UnderlyingService
from app.features.market.service.types import (
    Actor,
    AddListing,
    ChangeUnderlyingStatus,
    CreateListing,
    CreateUnderlying,
    DeleteUnderlying,
    SearchUnderlyings,
    SetPrimaryListing,
    UpdateListing,
    UpdateUnderlying,
)

router = APIRouter(prefix="/api/v1/underlyings", tags=["underlyings"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


def _actor(actor_id: str | None, actor_name: str | None) -> Actor:
    return Actor(id=actor_id, display_name=actor_name or "Trading Workspace User")


@router.get("", response_model=UnderlyingSearchResponse)
async def search_underlyings(
    service: Annotated[UnderlyingService, Depends(get_underlying_service)],
    query: str | None = Query(default=None, alias="q", min_length=1, max_length=200),
    lifecycle_status: LifecycleStatus | None = None,
    trading_venue_id: UUID | None = None,
    currency_code: str | None = Query(
        default=None,
        min_length=3,
        max_length=3,
        pattern=r"^[A-Za-z]{3}$",
    ),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> UnderlyingSearchResponse:
    try:
        items, total = await service.search(
            SearchUnderlyings(
                WORKSPACE_ID,
                query,
                lifecycle_status,
                trading_venue_id,
                currency_code.upper() if currency_code else None,
                offset,
                limit,
            )
        )
        return UnderlyingSearchResponse(
            items=[underlying_summary_response(item) for item in items],
            total=total,
            offset=offset,
            limit=limit,
        )
    except Exception as error:
        raise translate_market_error(error) from error


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=UnderlyingSummaryResponse,
)
async def create_underlying(
    payload: CreateUnderlyingRequest,
    service: Annotated[UnderlyingService, Depends(get_underlying_service)],
    x_actor_id: Annotated[str | None, Header()] = None,
    x_actor_name: Annotated[str | None, Header()] = None,
) -> UnderlyingSummaryResponse:
    try:
        result = await service.create(
            CreateUnderlying(
                workspace_id=WORKSPACE_ID,
                actor=_actor(x_actor_id, x_actor_name),
                name=payload.name,
                type=payload.type,
                isin=payload.isin,
                wkn=payload.wkn,
                primary_listing=CreateListing(
                    trading_venue_id=payload.primary_listing.trading_venue_id,
                    ticker=payload.primary_listing.ticker,
                    currency_code=payload.primary_listing.currency_code,
                    is_primary=True,
                ),
            )
        )
        return UnderlyingSummaryResponse.model_validate(result)
    except Exception as error:
        raise translate_market_error(error) from error


@router.get("/{underlying_id}", response_model=UnderlyingDetailResponse)
async def get_underlying(
    underlying_id: UUID,
    service: Annotated[UnderlyingService, Depends(get_underlying_service)],
) -> UnderlyingDetailResponse:
    try:
        return underlying_detail_response(
            await service.get(WORKSPACE_ID, underlying_id)
        )
    except Exception as error:
        raise translate_market_error(error) from error


@router.get("/{underlying_id}/audit-events", response_model=AuditEventListResponse)
async def get_underlying_audit_events(
    underlying_id: UUID,
    service: Annotated[UnderlyingService, Depends(get_underlying_service)],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> AuditEventListResponse:
    try:
        items, total = await service.audit_history(
            WORKSPACE_ID,
            underlying_id,
            offset=offset,
            limit=limit,
        )
        return AuditEventListResponse(
            items=[
                AuditEventResponse.model_validate(item, from_attributes=True)
                for item in items
            ],
            total=total,
            offset=offset,
            limit=limit,
        )
    except Exception as error:
        raise translate_market_error(error) from error


@router.get("/{underlying_id}/usages", response_model=UnderlyingUsageListResponse)
async def get_underlying_usages(
    underlying_id: UUID,
    service: Annotated[UnderlyingService, Depends(get_underlying_service)],
) -> UnderlyingUsageListResponse:
    try:
        items = await service.usages(WORKSPACE_ID, underlying_id)
        return UnderlyingUsageListResponse(
            items=[
                UnderlyingUsageResponse(
                    usage_type=item.usage_type,
                    count=item.count,
                    object_ids=list(item.object_ids),
                )
                for item in items
            ]
        )
    except Exception as error:
        raise translate_market_error(error) from error


@router.patch("/{underlying_id}", response_model=UnderlyingSummaryResponse)
async def update_underlying(
    underlying_id: UUID,
    payload: UpdateUnderlyingRequest,
    service: Annotated[UnderlyingService, Depends(get_underlying_service)],
    x_actor_id: Annotated[str | None, Header()] = None,
    x_actor_name: Annotated[str | None, Header()] = None,
) -> UnderlyingSummaryResponse:
    try:
        fields = payload.model_fields_set
        kwargs: dict[str, object] = {}
        for field in ("name", "isin", "wkn"):
            if field in fields:
                kwargs[field] = getattr(payload, field)
        result = await service.update(
            UpdateUnderlying(
                workspace_id=WORKSPACE_ID,
                underlying_id=underlying_id,
                expected_version=payload.version,
                actor=_actor(x_actor_id, x_actor_name),
                **kwargs,
            )
        )
        return UnderlyingSummaryResponse.model_validate(result)
    except Exception as error:
        raise translate_market_error(error) from error


async def _status_change(
    underlying_id: UUID,
    payload: VersionRequest,
    service: UnderlyingService,
    actor_id: str | None,
    actor_name: str | None,
    operation: str,
) -> UnderlyingSummaryResponse:
    command = ChangeUnderlyingStatus(
        WORKSPACE_ID,
        underlying_id,
        payload.version,
        _actor(actor_id, actor_name),
    )
    result = await getattr(service, operation)(command)
    return UnderlyingSummaryResponse.model_validate(result)


@router.post("/{underlying_id}/verify", response_model=UnderlyingSummaryResponse)
async def verify_underlying(
    underlying_id: UUID,
    payload: VersionRequest,
    service: Annotated[UnderlyingService, Depends(get_underlying_service)],
    x_actor_id: Annotated[str | None, Header()] = None,
    x_actor_name: Annotated[str | None, Header()] = None,
) -> UnderlyingSummaryResponse:
    try:
        return await _status_change(
            underlying_id, payload, service, x_actor_id, x_actor_name, "verify"
        )
    except Exception as error:
        raise translate_market_error(error) from error


@router.post("/{underlying_id}/deactivate", response_model=UnderlyingSummaryResponse)
async def deactivate_underlying(
    underlying_id: UUID,
    payload: VersionRequest,
    service: Annotated[UnderlyingService, Depends(get_underlying_service)],
    x_actor_id: Annotated[str | None, Header()] = None,
    x_actor_name: Annotated[str | None, Header()] = None,
) -> UnderlyingSummaryResponse:
    try:
        return await _status_change(
            underlying_id, payload, service, x_actor_id, x_actor_name, "deactivate"
        )
    except Exception as error:
        raise translate_market_error(error) from error


@router.post("/{underlying_id}/reactivate", response_model=UnderlyingSummaryResponse)
async def reactivate_underlying(
    underlying_id: UUID,
    payload: VersionRequest,
    service: Annotated[UnderlyingService, Depends(get_underlying_service)],
    x_actor_id: Annotated[str | None, Header()] = None,
    x_actor_name: Annotated[str | None, Header()] = None,
) -> UnderlyingSummaryResponse:
    try:
        return await _status_change(
            underlying_id, payload, service, x_actor_id, x_actor_name, "reactivate"
        )
    except Exception as error:
        raise translate_market_error(error) from error


@router.delete("/{underlying_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_underlying(
    underlying_id: UUID,
    version: int,
    service: Annotated[UnderlyingService, Depends(get_underlying_service)],
    x_actor_id: Annotated[str | None, Header()] = None,
    x_actor_name: Annotated[str | None, Header()] = None,
) -> Response:
    try:
        await service.delete(
            DeleteUnderlying(
                WORKSPACE_ID,
                underlying_id,
                version,
                _actor(x_actor_id, x_actor_name),
            )
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as error:
        raise translate_market_error(error) from error


@router.post(
    "/{underlying_id}/listings",
    status_code=status.HTTP_201_CREATED,
    response_model=ListingResponse,
)
async def add_listing(
    underlying_id: UUID,
    payload: AddListingRequest,
    service: Annotated[ListingService, Depends(get_listing_service)],
    x_actor_id: Annotated[str | None, Header()] = None,
    x_actor_name: Annotated[str | None, Header()] = None,
) -> ListingResponse:
    try:
        result = await service.add(
            AddListing(
                WORKSPACE_ID,
                underlying_id,
                _actor(x_actor_id, x_actor_name),
                payload.trading_venue_id,
                payload.ticker,
                payload.currency_code,
                payload.is_primary,
            )
        )
        return ListingResponse.model_validate(result)
    except Exception as error:
        raise translate_market_error(error) from error


@router.patch("/{underlying_id}/listings/{listing_id}", response_model=ListingResponse)
async def update_listing(
    underlying_id: UUID,
    listing_id: UUID,
    payload: UpdateListingRequest,
    service: Annotated[ListingService, Depends(get_listing_service)],
    x_actor_id: Annotated[str | None, Header()] = None,
    x_actor_name: Annotated[str | None, Header()] = None,
) -> ListingResponse:
    del underlying_id
    try:
        fields = payload.model_fields_set
        result = await service.update(
            UpdateListing(
                workspace_id=WORKSPACE_ID,
                listing_id=listing_id,
                expected_version=payload.version,
                actor=_actor(x_actor_id, x_actor_name),
                trading_venue_id=(
                    payload.trading_venue_id if "trading_venue_id" in fields else None
                ),
                ticker=payload.ticker if "ticker" in fields else None,
                currency_code=(
                    payload.currency_code if "currency_code" in fields else None
                ),
                lifecycle_status=(
                    payload.lifecycle_status if "lifecycle_status" in fields else None
                ),
            )
        )
        return ListingResponse.model_validate(result)
    except Exception as error:
        raise translate_market_error(error) from error


@router.put(
    "/{underlying_id}/primary-listing/{listing_id}", response_model=ListingResponse
)
async def set_primary_listing(
    underlying_id: UUID,
    listing_id: UUID,
    payload: VersionRequest,
    service: Annotated[ListingService, Depends(get_listing_service)],
    x_actor_id: Annotated[str | None, Header()] = None,
    x_actor_name: Annotated[str | None, Header()] = None,
) -> ListingResponse:
    try:
        result = await service.set_primary(
            SetPrimaryListing(
                WORKSPACE_ID,
                underlying_id,
                listing_id,
                payload.version,
                _actor(x_actor_id, x_actor_name),
            )
        )
        return ListingResponse.model_validate(result)
    except Exception as error:
        raise translate_market_error(error) from error
