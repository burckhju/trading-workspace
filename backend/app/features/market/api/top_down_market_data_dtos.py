"""HTTP contracts for MarketReference market-data and analysis orchestration."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.features.analysis.domain.enums import PriceField
from app.features.analysis.domain.models import AnalysisParameters
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
    def validate_period(self) -> "ReferenceDailyPriceImportRequest":
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
    def from_result(cls, value: ReferencePriceImportResult) -> "ReferenceDailyPriceImportResponse":
        return cls(**{
            "market_reference_id": value.market_reference_id,
            "market_data_instrument_id": value.market_data_instrument_id,
            "mapping_id": value.mapping_id,
            "currency": value.currency,
            "start_date": value.start_date,
            "end_date": value.end_date,
            "inserted": value.inserted,
            "updated": value.updated,
            "unchanged": value.unchanged,
        })


class ReferenceAnalysisCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actor: str = Field(default="Top-down analysis", min_length=1, max_length=200)


class ReferenceAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    workspace_id: UUID
    market_data_instrument_id: UUID
    underlying_id: UUID | None
    listing_id: UUID | None
    created_at: datetime
    created_by: str


class ReferenceAnalysisRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start_date: date
    end_date: date
    correlation_id: str | None = Field(default=None, max_length=100)
    price_field: PriceField = PriceField.ADJUSTED_CLOSE
    short_window: int = Field(default=20, ge=1)
    medium_window: int = Field(default=50, ge=1)
    long_window: int = Field(default=200, ge=1)
    momentum_windows: tuple[int, ...] = (20, 60, 120)
    volatility_window: int = Field(default=20, ge=1)
    range_window: int = Field(default=52, ge=1)
    minimum_required_observations: int = Field(default=200, ge=1)
    maximum_data_age_days: int = Field(default=7, ge=0)
    annualization_factor: Decimal = Field(default=Decimal("252"), gt=0)
    rounding_scale: int = Field(default=6, ge=0, le=12)

    @model_validator(mode="after")
    def validate_period(self) -> "ReferenceAnalysisRunRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self

    def to_parameters(self) -> AnalysisParameters:
        return AnalysisParameters(
            price_field=self.price_field,
            short_window=self.short_window,
            medium_window=self.medium_window,
            long_window=self.long_window,
            momentum_windows=self.momentum_windows,
            volatility_window=self.volatility_window,
            range_window=self.range_window,
            minimum_required_observations=self.minimum_required_observations,
            maximum_data_age_days=self.maximum_data_age_days,
            annualization_factor=self.annualization_factor,
            rounding_scale=self.rounding_scale,
        )


class ReferenceAnalysisRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    analysis_id: UUID
    version: int
    status: str
    quality_status: str
    observation_count: int
    analysis_time: datetime
    correlation_id: str | None
