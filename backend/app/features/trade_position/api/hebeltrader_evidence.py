"""F207-4 evidence transport: explicit review command and independent pure reads."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal, Self
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_manager, get_database_session
from app.database.manager import DatabaseManager
from app.features.trade_position.domain.hebeltrader_evidence import (
    EntryOrderEvidence,
    HebeltraderEvidenceDeclaration,
    HebeltraderEvidenceRevision,
    UnderlyingTradeEvidence,
    Z1SaleEvidence,
)
from app.features.trade_position.domain.price_binding import PriceBasis, PriceBinding
from app.features.trade_position.service.hebeltrader_coverage import HebeltraderCoverage
from app.features.trade_position.service.hebeltrader_evidence import (
    HebeltraderEvidenceHistory,
    HebeltraderEvidenceReader,
    HebeltraderEvidenceService,
    evidence_error,
)

router = APIRouter(prefix="/api/v1/trade-position/trades", tags=["trade-position"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
LOCAL_ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")


class EvidenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class BindingInput(EvidenceInput):
    basis: PriceBasis
    instrument_id: UUID
    currency: str = Field(pattern=r"^[A-Z]{3}$")

    def to_domain(self) -> PriceBinding:
        return PriceBinding(self.basis, self.instrument_id, self.currency)


class EntryOrderInput(EvidenceInput):
    source_reference: str = Field(min_length=3, max_length=1000)
    execution_ids: list[UUID] = Field(min_length=1, max_length=2000)
    complete: bool = Field(strict=True)

    def to_domain(self) -> EntryOrderEvidence:
        return EntryOrderEvidence(self.source_reference, tuple(self.execution_ids), self.complete)


class UnderlyingTradeInput(EvidenceInput):
    execution_id: UUID
    source_reference: str = Field(min_length=3, max_length=1000)
    price: Decimal = Field(gt=0, allow_inf_nan=False)
    binding: BindingInput
    scale_reference: str = Field(min_length=3, max_length=1000)
    last_trade_verified: bool = Field(strict=True)
    observed_at: AwareDatetime | None = None
    observed_on: date | None = None
    observation_timezone: str | None = None
    price_kind: Literal["TRADE"]

    def to_domain(self) -> UnderlyingTradeEvidence:
        return UnderlyingTradeEvidence(
            execution_id=self.execution_id,
            source_reference=self.source_reference,
            price=self.price,
            binding=self.binding.to_domain(),
            scale_reference=self.scale_reference,
            last_trade_verified=self.last_trade_verified,
            observed_at=self.observed_at,
            observed_on=self.observed_on,
            observation_timezone=self.observation_timezone,
            price_kind=self.price_kind,
        )


class Z1SaleInput(EvidenceInput):
    execution_id: UUID
    source_reference: str = Field(min_length=3, max_length=1000)

    def to_domain(self) -> Z1SaleEvidence:
        return Z1SaleEvidence(self.execution_id, self.source_reference)


class DeclarationInput(EvidenceInput):
    entry_order: EntryOrderInput | None = None
    source_version_id: UUID | None = None
    underlying_trades: list[UnderlyingTradeInput] = Field(default_factory=list, max_length=2000)
    z1_sales: list[Z1SaleInput] = Field(default_factory=list, max_length=2000)
    z1_sales_reviewed: bool = Field(default=False, strict=True)
    source_scale_reference: str | None = Field(default=None, min_length=3, max_length=1000)
    scale_review_status: Literal["UNVERIFIED", "UNCHANGED_VERIFIED", "ADJUSTMENT_REQUIRED"] = (
        "UNVERIFIED"
    )
    scale_review_reference: str | None = Field(default=None, min_length=3, max_length=1000)

    def to_domain(self) -> HebeltraderEvidenceDeclaration:
        return HebeltraderEvidenceDeclaration(
            entry_order=self.entry_order.to_domain() if self.entry_order else None,
            source_version_id=self.source_version_id,
            underlying_trades=tuple(item.to_domain() for item in self.underlying_trades),
            z1_sales=tuple(item.to_domain() for item in self.z1_sales),
            z1_sales_reviewed=self.z1_sales_reviewed,
            source_scale_reference=self.source_scale_reference,
            scale_review_status=self.scale_review_status,
            scale_review_reference=self.scale_review_reference,
        )

    @model_validator(mode="after")
    def validate_declaration(self) -> Self:
        self.to_domain()
        return self


class HebeltraderEvidenceRequest(EvidenceInput):
    position_id: UUID
    request_id: UUID
    supersedes_evidence_id: UUID | None = None
    confirmation: Literal["CONFIRM_HISTORICAL_EVIDENCE"]
    declaration: DeclarationInput


def get_evidence_reader(
    database: Annotated[DatabaseManager, Depends(get_database_manager)],
) -> HebeltraderEvidenceReader:
    return HebeltraderEvidenceReader(database.engine)


def get_evidence_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> HebeltraderEvidenceService:
    return HebeltraderEvidenceService(session)


Reader = Annotated[HebeltraderEvidenceReader, Depends(get_evidence_reader)]


def validate_position_query(request: Request) -> None:
    if len(request.query_params.getlist("position_id")) != 1:
        raise evidence_error(
            "BASELINE_POSITION_INVALID", "Eine eindeutige Positionskennung ist erforderlich."
        )


def read_unavailable() -> Exception:
    return evidence_error(
        "BASELINE_EVIDENCE_READ_UNAVAILABLE",
        "Belegabdeckung konnte nicht gelesen werden. Das bedeutet nicht, dass Belege fehlen.",
        503,
    )


@router.get("/{trade_id}/hebeltrader-evidence")
async def coverage(
    trade_id: UUID, position_id: UUID, reader: Reader, request: Request
) -> HebeltraderCoverage:
    validate_position_query(request)
    try:
        return await reader.read(WORKSPACE_ID, trade_id, position_id)
    except DBAPIError as error:
        raise read_unavailable() from error


@router.get("/{trade_id}/hebeltrader-evidence/history")
async def history(
    trade_id: UUID, position_id: UUID, reader: Reader, request: Request
) -> HebeltraderEvidenceHistory:
    validate_position_query(request)
    try:
        return await reader.history(WORKSPACE_ID, trade_id, position_id)
    except DBAPIError as error:
        raise read_unavailable() from error


@router.post("/{trade_id}/hebeltrader-evidence", status_code=201)
async def record(
    trade_id: UUID,
    body: HebeltraderEvidenceRequest,
    service: Annotated[HebeltraderEvidenceService, Depends(get_evidence_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> HebeltraderEvidenceRevision:
    return await service.record(
        workspace_id=WORKSPACE_ID,
        trade_id=trade_id,
        position_id=body.position_id,
        declaration=body.declaration.to_domain(),
        actor=actor_id or LOCAL_ACTOR_ID,
        request_id=body.request_id,
        supersedes_evidence_id=body.supersedes_evidence_id,
    )
