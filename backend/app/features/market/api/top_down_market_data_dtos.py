"""HTTP contracts for MarketReference provider mapping, EOD import, and analysis."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.features.market_data.service.reference_market_data import ReferencePriceImportResult


class ReferenceProviderMappingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    provider_symbol: str = Field(min_length=1, max_length=64)
    provider_exchange_code: str = Field(min_length=1, max_length=32)


class ReferenceProviderMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    workspace_id: UUID
    listing_id: UUID | None
    market_data_instrument_id: UUID
    provider: str
    provider_symbol: str
    provider_exchange_code: str
    status: str
    validated_at: datetime | None
    validation_message: str | None
    version: int


class ReferenceDailyPriceImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_period(self) -> ReferenceDailyPriceImportRequest:
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        if (self.end_date - self.start_date).days > 3660:
            raise ValueError("date range must not exceed 10 years")
        return self


class ReferenceDailyPriceImportResponse(BaseModel):
    market_reference_id: UUID
    market_data_instrument_id: UUID
    mapping_id: UUID
    currency: str
    start_date: date
    end_date: date
    inserted: int = Field(ge=0)
    updated: int = Field(ge=0)
    unchanged: int = Field(ge=0)

    @classmethod
    def from_result(cls, value: ReferencePriceImportResult) -> ReferenceDailyPriceImportResponse:
        return cls(
            market_reference_id=value.market_reference_id,
            market_data_instrument_id=value.market_data_instrument_id,
            mapping_id=value.mapping_id,
            currency=value.currency,
            start_date=value.start_date,
            end_date=value.end_date,
            inserted=value.inserted,
            updated=value.updated,
            unchanged=value.unchanged,
        )


class ReferenceAnalysisResponse(BaseModel):
    market_reference_id: UUID
    analysis_id: UUID
    market_data_instrument_id: UUID
    created_at: datetime
    created_by: str
