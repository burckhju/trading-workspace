"""Provider-independent HTTP contracts for market-data imports."""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.features.market_data.domain.enums import (
    CacheStatus,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.service.application import DailyPriceImportResult
from app.features.market_data.service.venue_reconciliation import (
    VenueReconciliationResult,
    VenueReconciliationStatus,
)


class ImportDailyPricesRequest(BaseModel):
    """Request an idempotent import of completed daily prices."""

    model_config = ConfigDict(extra="forbid")

    listing_id: UUID
    mapping_id: UUID
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_period(self) -> "ImportDailyPricesRequest":
        """Reject reversed ranges and ranges exceeding ten years."""
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        if (self.end_date - self.start_date).days > 3660:
            raise ValueError("date range must not exceed 10 years")
        return self


class ImportDailyPricesResponse(BaseModel):
    """Traceable result of one daily-price import."""

    workspace_id: UUID
    listing_id: UUID
    mapping_id: UUID
    start_date: date
    end_date: date
    inserted: int = Field(ge=0)
    updated: int = Field(ge=0)
    unchanged: int = Field(ge=0)
    processed: int = Field(ge=0)
    provider: MarketDataProvider
    cache_status: CacheStatus
    quality_status: QualityStatus
    warnings: list[str]
    retry_count: int = Field(ge=0)
    provider_call_cost: int | None = Field(default=None, ge=0)
    retrieved_at: datetime

    @classmethod
    def from_result(cls, result: DailyPriceImportResult) -> "ImportDailyPricesResponse":
        """Create an HTTP response without exposing provider transport details."""
        return cls(
            workspace_id=result.workspace_id,
            listing_id=result.listing_id,
            mapping_id=result.mapping_id,
            start_date=result.start_date,
            end_date=result.end_date,
            inserted=result.inserted,
            updated=result.updated,
            unchanged=result.unchanged,
            processed=result.processed,
            provider=result.provider,
            cache_status=result.cache_status,
            quality_status=result.quality_status,
            warnings=list(result.warnings),
            retry_count=result.retry_count,
            provider_call_cost=result.provider_call_cost,
            retrieved_at=result.retrieved_at,
        )


class ProviderMappingUpsertRequest(BaseModel):
    """Create or update an administrative provider-symbol assignment."""

    model_config = ConfigDict(extra="forbid")
    listing_id: UUID
    provider: MarketDataProvider = MarketDataProvider.EODHD
    provider_symbol: str = Field(min_length=1, max_length=64)
    provider_exchange_code: str = Field(min_length=1, max_length=32)
    actor_id: str | None = Field(default=None, max_length=100)
    actor_name: str = Field(default="Administrator", min_length=1, max_length=200)


class ProviderMappingStateRequest(BaseModel):
    """Enable or disable an existing provider mapping."""

    model_config = ConfigDict(extra="forbid")
    enabled: bool
    actor_id: str | None = Field(default=None, max_length=100)
    actor_name: str = Field(default="Administrator", min_length=1, max_length=200)


class ProviderMappingResponse(BaseModel):
    """Provider-independent public representation of one mapping."""

    id: UUID
    workspace_id: UUID
    listing_id: UUID
    provider: MarketDataProvider
    provider_symbol: str
    provider_exchange_code: str
    status: str
    validated_at: datetime | None
    validation_message: str | None
    created_at: datetime
    updated_at: datetime
    version: int

    @classmethod
    def from_domain(cls, value: object) -> "ProviderMappingResponse":
        return cls.model_validate(value, from_attributes=True)


class ProviderStatusResponse(BaseModel):
    """Non-secret operational status of the configured provider."""

    provider: MarketDataProvider
    enabled: bool
    configured: bool
    daily_limit: int
    safety_reserve: int
    effective_budget: int
    used_today: int
    remaining_today: int
    requests_per_minute: int
    burst_capacity: int
    single_instance_only: bool = True


class VenueReconciliationResponse(BaseModel):
    """Read-only explanation of provider-exchange evidence for one mapping."""

    status: VenueReconciliationStatus
    listing_venue_id: UUID | None
    evidence_venue_ids: list[UUID]
    explanation: str

    @classmethod
    def from_result(cls, result: VenueReconciliationResult) -> "VenueReconciliationResponse":
        explanations = {
            VenueReconciliationStatus.MATCHED: (
                "Provider evidence confirms the listing trading venue."
            ),
            VenueReconciliationStatus.CONFLICT: (
                "Provider evidence points to a different trading venue."
            ),
            VenueReconciliationStatus.AMBIGUOUS: (
                "Provider evidence maps to multiple trading venues; " "no automatic choice is made."
            ),
            VenueReconciliationStatus.UNRESOLVED: (
                "No reliable existing venue evidence is available; " "no automatic choice is made."
            ),
        }
        return cls(
            status=result.status,
            listing_venue_id=result.listing_venue_id,
            evidence_venue_ids=list(result.evidence_venue_ids),
            explanation=explanations[result.status],
        )
