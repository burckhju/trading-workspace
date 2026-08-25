"""Transport contracts for top-down reference administration."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.features.market.domain.top_down import BenchmarkRole


class RequestDto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MarketReferenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    reference_type: str
    region: str
    role: str
    reference_version: str
    active: bool
    created_at: datetime


class SectorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str
    classification_system: str
    classification_version: str
    active: bool
    created_at: datetime


class CreateSectorRequest(RequestDto):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    classification_system: str = Field(min_length=1, max_length=100)
    classification_version: str = Field(min_length=1, max_length=50)


class CreateSectorReferenceRequest(RequestDto):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    region: str = Field(min_length=1, max_length=50)
    reference_version: str = Field(min_length=1, max_length=50)


class ActiveStateRequest(RequestDto):
    active: bool


class AssignmentRequest(RequestDto):
    valid_from: date
    valid_to: date | None = None
    source: str = Field(min_length=1, max_length=100)
    source_reference: str | None = Field(default=None, max_length=200)
    quality_status: str = Field(default="GOOD", min_length=1, max_length=30)


class ReferenceListingAssignmentRequest(AssignmentRequest):
    listing_id: UUID


class UnderlyingBenchmarkAssignmentRequest(AssignmentRequest):
    market_reference_id: UUID
    role: BenchmarkRole = BenchmarkRole.BROAD_MARKET


class UnderlyingSectorAssignmentRequest(AssignmentRequest):
    sector_id: UUID


class SectorReferenceAssignmentRequest(AssignmentRequest):
    market_reference_id: UUID


class AssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    valid_from: date
    valid_to: date | None
    source: str
    quality_status: str
    created_at: datetime


class ProviderReferenceSuggestionResponse(BaseModel):
    reference_code: str
    provider_symbol: str | None
    provider_exchange_code: str | None
    verification_status: str
    verification_source: str
    note: str


class TopDownReferenceReadinessResponse(BaseModel):
    reference_id: UUID
    reference_code: str
    reference_type: str
    market_data_instrument_id: UUID | None = None
    # Deprecated compatibility field. Index/reference readiness no longer requires a stock Listing.
    listing_id: UUID | None
    provider_mapping_id: UUID | None
    provider_mapping_active: bool
    daily_price_count: int
    latest_price_date: date | None
    completed_analysis_id: UUID | None
    completed_analysis_version: int | None
    ready: bool
    blockers: list[str]
