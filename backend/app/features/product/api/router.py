"""FT-004 Warrant REST API."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.product.api.errors import translate_product_error
from app.features.product.domain.models import (
    OptionDirection,
    ProductFamily,
    WarrantLifecycle,
)
from app.features.product.service.application import WarrantService
from app.features.product.service.hard_delete import WarrantHardDeleteService

router = APIRouter(prefix="/api/v1/warrants", tags=["warrants"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
StrikeCurrencyCode = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_upper=True,
        min_length=3,
        max_length=3,
        pattern=r"^[A-Za-z]{3}$",
    ),
]


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CreateWarrantRequest(Request):
    issuer_id: UUID
    underlying_id: UUID
    display_name: str = Field(min_length=1, max_length=200)
    isin: str | None = Field(default=None, max_length=12)
    wkn: str | None = Field(default=None, max_length=16)
    option_direction: OptionDirection
    strike: Decimal = Field(ge=0)
    strike_currency_code: StrikeCurrencyCode | None = Field(
        default=None,
        description="Currency of the contractual strike, not the listing currency. Null is unknown.",
    )
    maturity_date: date
    ratio: Decimal = Field(gt=0)


class VersionRequest(Request):
    version: int = Field(ge=1)


class TermsRequest(Request):
    expected_version: int = Field(ge=1)
    option_direction: OptionDirection
    strike: Decimal = Field(ge=0)
    strike_currency_code: StrikeCurrencyCode | None = Field(
        default=None,
        description="Explicit currency for this terms version; never inferred from a listing.",
    )
    maturity_date: date
    ratio: Decimal = Field(gt=0)


class ListingRequest(Request):
    trading_venue_id: UUID
    symbol: str | None = Field(default=None, max_length=64)
    quotation_currency_code: str = Field(min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")


class ListingLifecycleRequest(Request):
    expected_version: int = Field(ge=1)


class WarrantResponse(ResponseModel):
    id: UUID
    workspace_id: UUID
    issuer_id: UUID
    underlying_id: UUID
    product_family: ProductFamily
    display_name: str
    isin: str | None
    wkn: str | None
    lifecycle_status: WarrantLifecycle
    version: int
    created_at: datetime
    updated_at: datetime


class TermsResponse(ResponseModel):
    id: UUID
    warrant_id: UUID
    version_no: int
    effective_from: datetime
    effective_to: datetime | None
    option_direction: OptionDirection
    strike: Decimal
    strike_currency_code: str | None = None
    maturity_date: date
    ratio: Decimal
    created_at: datetime


class ListingResponse(ResponseModel):
    id: UUID
    workspace_id: UUID
    warrant_id: UUID
    trading_venue_id: UUID
    symbol: str | None
    quotation_currency_code: str
    lifecycle_status: WarrantLifecycle
    version: int
    created_at: datetime
    updated_at: datetime


async def service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> WarrantService:
    return WarrantService(session)


async def hard_delete_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> WarrantHardDeleteService:
    return WarrantHardDeleteService(session)


@router.get("", response_model=list[WarrantResponse])
async def list_warrants(svc: Annotated[WarrantService, Depends(service)]) -> list[WarrantResponse]:
    return [WarrantResponse.model_validate(x) for x in await svc.list(WORKSPACE_ID)]


@router.post("", response_model=WarrantResponse, status_code=status.HTTP_201_CREATED)
async def create_warrant(
    payload: CreateWarrantRequest, svc: Annotated[WarrantService, Depends(service)]
) -> WarrantResponse:
    try:
        model = await svc.create(WORKSPACE_ID, **payload.model_dump())
        return WarrantResponse.model_validate(model)
    except Exception as error:
        raise translate_product_error(error) from error


@router.get("/{warrant_id}", response_model=WarrantResponse)
async def get_warrant(
    warrant_id: UUID, svc: Annotated[WarrantService, Depends(service)]
) -> WarrantResponse:
    try:
        return WarrantResponse.model_validate(await svc.get(WORKSPACE_ID, warrant_id))
    except Exception as error:
        raise translate_product_error(error) from error


@router.delete("/{warrant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_warrant(
    warrant_id: UUID,
    svc: Annotated[WarrantHardDeleteService, Depends(hard_delete_service)],
    version: int = Query(ge=1),
) -> Response:
    try:
        await svc.delete(WORKSPACE_ID, warrant_id, version)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as error:
        raise translate_product_error(error) from error


@router.post("/{warrant_id}/deactivate", response_model=WarrantResponse)
async def deactivate(
    warrant_id: UUID, payload: VersionRequest, svc: Annotated[WarrantService, Depends(service)]
) -> WarrantResponse:
    try:
        return WarrantResponse.model_validate(
            await svc.change_status(
                WORKSPACE_ID, warrant_id, payload.version, WarrantLifecycle.INACTIVE
            )
        )
    except Exception as error:
        raise translate_product_error(error) from error


@router.post("/{warrant_id}/reactivate", response_model=WarrantResponse)
async def reactivate(
    warrant_id: UUID, payload: VersionRequest, svc: Annotated[WarrantService, Depends(service)]
) -> WarrantResponse:
    try:
        return WarrantResponse.model_validate(
            await svc.change_status(
                WORKSPACE_ID, warrant_id, payload.version, WarrantLifecycle.ACTIVE
            )
        )
    except Exception as error:
        raise translate_product_error(error) from error


@router.get("/{warrant_id}/terms", response_model=list[TermsResponse])
async def terms(
    warrant_id: UUID, svc: Annotated[WarrantService, Depends(service)]
) -> list[TermsResponse]:
    try:
        return [
            TermsResponse.model_validate(x)
            for x in await svc.terms_history(WORKSPACE_ID, warrant_id)
        ]
    except Exception as error:
        raise translate_product_error(error) from error


@router.post(
    "/{warrant_id}/terms", response_model=TermsResponse, status_code=status.HTTP_201_CREATED
)
async def add_terms(
    warrant_id: UUID, payload: TermsRequest, svc: Annotated[WarrantService, Depends(service)]
) -> TermsResponse:
    try:
        return TermsResponse.model_validate(
            await svc.add_terms_version(WORKSPACE_ID, warrant_id, **payload.model_dump())
        )
    except Exception as error:
        raise translate_product_error(error) from error


@router.get("/{warrant_id}/listings", response_model=list[ListingResponse])
async def listings(
    warrant_id: UUID, svc: Annotated[WarrantService, Depends(service)]
) -> list[ListingResponse]:
    try:
        return [
            ListingResponse.model_validate(x) for x in await svc.listings(WORKSPACE_ID, warrant_id)
        ]
    except Exception as error:
        raise translate_product_error(error) from error


@router.post(
    "/{warrant_id}/listings", response_model=ListingResponse, status_code=status.HTTP_201_CREATED
)
async def add_listing(
    warrant_id: UUID, payload: ListingRequest, svc: Annotated[WarrantService, Depends(service)]
) -> ListingResponse:
    try:
        return ListingResponse.model_validate(
            await svc.add_listing(WORKSPACE_ID, warrant_id, **payload.model_dump())
        )
    except Exception as error:
        raise translate_product_error(error) from error


@router.post(
    "/{warrant_id}/listings/{listing_id}/deactivate",
    response_model=ListingResponse,
)
async def deactivate_listing(
    warrant_id: UUID,
    listing_id: UUID,
    payload: ListingLifecycleRequest,
    svc: Annotated[WarrantService, Depends(service)],
) -> ListingResponse:
    try:
        return ListingResponse.model_validate(
            await svc.deactivate_listing(
                WORKSPACE_ID,
                warrant_id,
                listing_id,
                expected_version=payload.expected_version,
            )
        )
    except Exception as error:
        raise translate_product_error(error) from error
