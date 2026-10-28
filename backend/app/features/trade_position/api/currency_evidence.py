"""Explicit source review for one product; source references are never fetched."""

from datetime import UTC, datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.trade_position.domain.currency_evidence import (
    CurrencyEvidence,
    CurrencyEvidenceKind,
    CurrencyListingEvidence,
)
from app.features.trade_position.service.currency_evidence import (
    CurrencyEvidenceService,
)

router = APIRouter()
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
LOCAL_ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")


class ListingEvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trading_venue_id: UUID
    currency_code: str | None = Field(
        default=None, min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$"
    )


class CurrencyEvidenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    kind: CurrencyEvidenceKind
    source_reference: str = Field(min_length=3, max_length=1000)
    request_id: UUID
    confirmation: Literal["CONFIRM_SOURCE_REVIEW"]
    supersedes_evidence_id: UUID | None = None
    revoked: bool = Field(default=False, strict=True)
    trade_id: UUID | None = None
    execution_id: UUID | None = None
    currency_code: str | None = Field(
        default=None, min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$"
    )
    trading_venue_id: UUID | None = None
    valid_from: AwareDatetime | None = None
    valid_to: AwareDatetime | None = None
    listings: list[ListingEvidenceRequest] = Field(default_factory=list, max_length=100)
    complete_listing_set: bool = Field(default=False, strict=True)

    def listing_facts(self) -> tuple[CurrencyListingEvidence, ...]:
        return tuple(
            CurrencyListingEvidence(item.trading_venue_id, item.currency_code)
            for item in self.listings
        )

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        CurrencyEvidence(
            id=UUID(int=0),
            workspace_id=WORKSPACE_ID,
            product_id=UUID(int=0),
            recorded_at=datetime(2000, 1, 1, tzinfo=UTC),
            recorded_by=LOCAL_ACTOR_ID,
            request_fingerprint="",
            listings=self.listing_facts(),
            **self.model_dump(exclude={"confirmation", "listings"}),
        )
        return self


class CurrencyEvidenceHistory(BaseModel):
    history: list[CurrencyEvidence]


async def evidence_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> CurrencyEvidenceService:
    return CurrencyEvidenceService(session)


@router.get("/{product_id}/currency-evidence", response_model=CurrencyEvidenceHistory)
async def read_evidence(
    product_id: UUID,
    service: Annotated[CurrencyEvidenceService, Depends(evidence_service)],
) -> CurrencyEvidenceHistory:
    return CurrencyEvidenceHistory(history=list(await service.history(WORKSPACE_ID, product_id)))


@router.post("/{product_id}/currency-evidence", response_model=CurrencyEvidence, status_code=201)
async def record_evidence(
    product_id: UUID,
    request: CurrencyEvidenceRequest,
    service: Annotated[CurrencyEvidenceService, Depends(evidence_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> CurrencyEvidence:
    return await service.record(
        workspace_id=WORKSPACE_ID,
        product_id=product_id,
        actor=actor_id or LOCAL_ACTOR_ID,
        listings=request.listing_facts(),
        **request.model_dump(exclude={"confirmation", "listings"}),
    )
