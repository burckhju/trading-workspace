"""Pydantic transport contracts for the FT-001 REST API.

The DTO layer owns HTTP serialization and structural request parsing only.
Business normalization and business-rule validation remain in the domain and
service layers. Field-level and request-level transport constraints are
implemented in Sprint-2 step 9.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from pydantic_core import PydanticCustomError

from app.features.market.domain.enums import (
    LifecycleStatus,
    QualityStatus,
    UnderlyingType,
)
from app.features.market.persistence.models import ListingModel, UnderlyingModel

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Ticker = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]
CurrencyCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$"),
]
OptionalIsin = (
    Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)] | None
)
OptionalWkn = (
    Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=16)] | None
)


class RequestDto(BaseModel):
    """Base configuration for request bodies."""

    model_config = ConfigDict(extra="forbid")


class ResponseDto(BaseModel):
    """Base configuration for ORM-backed response bodies."""

    model_config = ConfigDict(from_attributes=True)


class CreateListingRequest(RequestDto):
    trading_venue_id: UUID
    ticker: Ticker
    currency_code: CurrencyCode
    is_primary: bool = True


class CreateUnderlyingRequest(RequestDto):
    name: Name
    type: UnderlyingType = UnderlyingType.STOCK
    isin: OptionalIsin = None
    wkn: OptionalWkn = None
    primary_listing: CreateListingRequest


class UpdateUnderlyingRequest(RequestDto):
    version: int = Field(ge=1)
    name: Name | None = None
    isin: OptionalIsin = None
    wkn: OptionalWkn = None

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if not ({"name", "isin", "wkn"} & self.model_fields_set):
            raise PydanticCustomError(
                "missing_change",
                "At least one mutable field must be supplied",
            )
        return self


class VersionRequest(RequestDto):
    version: int = Field(ge=1)


class AddListingRequest(RequestDto):
    trading_venue_id: UUID
    ticker: Ticker
    currency_code: CurrencyCode
    is_primary: bool = False


class UpdateListingRequest(RequestDto):
    version: int = Field(ge=1)
    trading_venue_id: UUID | None = None
    ticker: Ticker | None = None
    currency_code: CurrencyCode | None = None
    lifecycle_status: LifecycleStatus | None = None

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if not (
            {"trading_venue_id", "ticker", "currency_code", "lifecycle_status"}
            & self.model_fields_set
        ):
            raise PydanticCustomError(
                "missing_change",
                "At least one mutable field must be supplied",
            )
        return self


class CreateTradingVenueRequest(RequestDto):
    mic: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=4,
            max_length=4,
            pattern=r"^[A-Za-z0-9]{4}$",
        ),
    ]
    name: Name
    country_code: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=2,
            max_length=2,
            pattern=r"^[A-Za-z]{2}$",
        ),
    ]
    timezone: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


class UpdateTradingVenueRequest(RequestDto):
    expected_version: int = Field(ge=1)
    name: Name | None = None
    country_code: (
        Annotated[
            str,
            StringConstraints(
                strip_whitespace=True,
                min_length=2,
                max_length=2,
                pattern=r"^[A-Za-z]{2}$",
            ),
        ]
        | None
    ) = None
    timezone: (
        Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)] | None
    ) = None

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if not ({"name", "country_code", "timezone"} & self.model_fields_set):
            raise PydanticCustomError(
                "missing_change",
                "At least one mutable field must be supplied",
            )
        return self


class TradingVenueVersionRequest(RequestDto):
    expected_version: int = Field(ge=1)


CountryCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$"),
]
Lei = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=20, max_length=20, pattern=r"^[A-Za-z0-9]{20}$"
    ),
]


class CreateIssuerRequest(RequestDto):
    legal_name: Name
    display_name: Name
    country_code: CountryCode | None = None
    lei: Lei | None = None


class UpdateIssuerRequest(RequestDto):
    expected_version: int = Field(ge=1)
    legal_name: Name | None = None
    display_name: Name | None = None
    country_code: CountryCode | None = None
    lei: Lei | None = None

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if not ({"legal_name", "display_name", "country_code", "lei"} & self.model_fields_set):
            raise PydanticCustomError(
                "missing_change", "At least one mutable field must be supplied"
            )
        return self


class IssuerVersionRequest(RequestDto):
    expected_version: int = Field(ge=1)


class IssuerResponse(ResponseDto):
    id: UUID
    legal_name: str
    display_name: str
    country_code: str | None
    lei: str | None


class IssuerAdminResponse(IssuerResponse):
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class IssuerListResponse(BaseModel):
    items: list[IssuerResponse]


class IssuerAdminListResponse(BaseModel):
    items: list[IssuerAdminResponse]


class PrimaryListingSummaryResponse(ResponseDto):
    id: UUID
    ticker: str
    trading_venue_id: UUID
    trading_venue_mic: str
    trading_venue_name: str
    currency_code: str


class ListingResponse(ResponseDto):
    id: UUID
    underlying_id: UUID
    trading_venue_id: UUID
    trading_venue_mic: str | None = None
    trading_venue_name: str | None = None
    ticker: str
    currency_code: str
    lifecycle_status: LifecycleStatus
    is_primary: bool
    version: int
    created_at: datetime
    updated_at: datetime


class UnderlyingSummaryResponse(ResponseDto):
    id: UUID
    type: UnderlyingType
    name: str
    isin: str | None
    wkn: str | None
    lifecycle_status: LifecycleStatus
    quality_status: QualityStatus
    version: int
    created_at: datetime
    updated_at: datetime
    primary_listing: PrimaryListingSummaryResponse | None = None


class UnderlyingDetailResponse(UnderlyingSummaryResponse):
    listings: list[ListingResponse] = Field(default_factory=list)


class UnderlyingSearchResponse(BaseModel):
    items: list[UnderlyingSummaryResponse]
    total: int
    offset: int
    limit: int


class TradingVenueResponse(ResponseDto):
    id: UUID
    mic: str
    name: str
    country_code: str
    timezone: str
    reference_version: str


class TradingVenueAdminResponse(TradingVenueResponse):
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class CurrencyResponse(ResponseDto):
    code: str
    name: str
    minor_unit: int
    reference_version: str


class TradingVenueListResponse(BaseModel):
    items: list[TradingVenueResponse]


class TradingVenueAdminListResponse(BaseModel):
    items: list[TradingVenueAdminResponse]


class CurrencyListResponse(BaseModel):
    items: list[CurrencyResponse]


class AuditEventResponse(BaseModel):
    id: UUID
    aggregate_type: str
    aggregate_id: UUID
    occurred_at: datetime
    actor_display_name: str
    change_type: str
    version_before: int | None
    version_after: int | None
    field_changes: dict[str, dict[str, object]]


class AuditEventListResponse(BaseModel):
    items: list[AuditEventResponse]
    total: int
    offset: int
    limit: int


class UnderlyingUsageResponse(BaseModel):
    usage_type: str
    count: int
    object_ids: list[UUID]


class UnderlyingUsageListResponse(BaseModel):
    items: list[UnderlyingUsageResponse]


def listing_response(model: ListingModel) -> ListingResponse:
    return ListingResponse(
        id=model.id,
        underlying_id=model.underlying_id,
        trading_venue_id=model.trading_venue_id,
        trading_venue_mic=model.trading_venue.mic,
        trading_venue_name=model.trading_venue.name,
        ticker=model.ticker,
        currency_code=model.currency_code,
        lifecycle_status=model.lifecycle_status,
        is_primary=model.is_primary,
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def underlying_summary_response(model: UnderlyingModel) -> UnderlyingSummaryResponse:
    primary = next(
        (
            item
            for item in getattr(model, "listings", ())
            if item.is_primary and item.lifecycle_status == LifecycleStatus.ACTIVE
        ),
        None,
    )
    return UnderlyingSummaryResponse(
        id=model.id,
        type=model.type,
        name=model.name,
        isin=model.isin,
        wkn=model.wkn,
        lifecycle_status=model.lifecycle_status,
        quality_status=model.quality_status,
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
        primary_listing=(
            PrimaryListingSummaryResponse(
                id=primary.id,
                ticker=primary.ticker,
                trading_venue_id=primary.trading_venue_id,
                trading_venue_mic=primary.trading_venue.mic,
                trading_venue_name=primary.trading_venue.name,
                currency_code=primary.currency_code,
            )
            if primary is not None
            else None
        ),
    )


def underlying_detail_response(model: UnderlyingModel) -> UnderlyingDetailResponse:
    summary = underlying_summary_response(model)
    return UnderlyingDetailResponse(
        **summary.model_dump(),
        listings=[listing_response(item) for item in model.listings],
    )
