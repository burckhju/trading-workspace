"""Pydantic transport contracts for FT-006."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from app.features.analysis.domain.enums import PriceField
from app.features.analysis.domain.models import AnalysisParameters


class CreateAnalysisRequest(BaseModel):
    underlying_id: UUID
    listing_id: UUID


class AnalysisParametersRequest(BaseModel):
    price_field: PriceField = PriceField.ADJUSTED_CLOSE
    short_window: int = Field(20, gt=0)
    medium_window: int = Field(50, gt=0)
    long_window: int = Field(200, gt=0)
    momentum_windows: list[int] = Field(default_factory=lambda: [20, 60, 120])
    volatility_window: int = Field(20, gt=0)
    range_window: int = Field(52, gt=0)
    minimum_required_observations: int = Field(200, gt=0)
    maximum_data_age_days: int = Field(7, ge=0)
    annualization_factor: Decimal = Field(Decimal("252"), gt=0)
    rounding_scale: int = Field(6, ge=0, le=12)

    def to_domain(self) -> AnalysisParameters:
        return AnalysisParameters(
            self.price_field,
            self.short_window,
            self.medium_window,
            self.long_window,
            tuple(self.momentum_windows),
            self.volatility_window,
            self.range_window,
            self.minimum_required_observations,
            self.maximum_data_age_days,
            self.annualization_factor,
            self.rounding_scale,
        )


class RunAnalysisRequest(BaseModel):
    start_date: date
    end_date: date
    parameters: AnalysisParametersRequest = Field(
        default_factory=lambda: AnalysisParametersRequest()
    )


class AnalysisSummaryResponse(BaseModel):
    id: UUID
    underlying_id: UUID
    listing_id: UUID
    created_at: datetime
    created_by: str


class AnalysisOverviewResponse(AnalysisSummaryResponse):
    underlying_name: str
    ticker: str
    trading_venue_mic: str
    trading_venue_name: str
    currency_code: str
    latest_version: int | None
    latest_status: str | None
    latest_quality_status: str | None
    latest_analysis_time: datetime | None


class AnalysisOverviewPageResponse(BaseModel):
    items: list[AnalysisOverviewResponse]
    total: int
    offset: int
    limit: int


class RunSummaryResponse(BaseModel):
    version: int
    status: str
    quality_status: str
    model_id: str
    model_version: str
    observation_count: int
    analysis_time: datetime
    input_hash: str


class CriterionResponse(BaseModel):
    code: str
    classification: str
    value: str | None
    explanation: str


class SnapshotRowResponse(BaseModel):
    trading_date: date
    open: str
    high: str
    low: str
    close: str
    adjusted_close: str | None
    volume: str | None
    currency: str
    provider: str
    provider_symbol: str
    quality_status: str
    warnings: list[str]


class AnalysisDetailResponse(BaseModel):
    analysis: AnalysisSummaryResponse
    runs: list[RunSummaryResponse]


class SnapshotPageResponse(BaseModel):
    items: list[SnapshotRowResponse]
    total: int
    offset: int
    limit: int


class AnalysisRunDetailResponse(BaseModel):
    analysis: AnalysisSummaryResponse
    run: RunSummaryResponse
    parameters: dict[str, object]
    metrics: dict[str, str | None]
    notes: list[str]
    data_sources: list[str]
    criteria: list[CriterionResponse]
    snapshot: list[SnapshotRowResponse]


class RetryAnalysisRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class SupersedeAnalysisRequest(BaseModel):
    replacement_version: int = Field(gt=0)
    reason: str | None = Field(default=None, max_length=1000)


class AnalysisEventResponse(BaseModel):
    id: UUID
    version: int | None
    event_type: str
    from_status: str | None
    to_status: str
    source_version: int | None
    replacement_version: int | None
    reason: str | None
    correlation_id: str | None
    occurred_at: datetime


class AnalysisVerificationResponse(BaseModel):
    verified: bool
    model_available: bool
    input_hash_matches: bool
    metrics_match: bool
    criteria_match: bool
    quality_status_match: bool
    notes_match: bool
