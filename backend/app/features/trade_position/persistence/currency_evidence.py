"""Append-only reviewed source history with bounded deterministic reads."""

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.features.trade_position.domain.currency_evidence import (
    CurrencyEvidence,
    CurrencyEvidenceKind,
    CurrencyEvidenceLimitExceeded,
    CurrencyListingEvidence,
)


class CurrencyEvidenceModel(Base):
    __tablename__ = "currency_source_evidence"
    __table_args__ = (
        UniqueConstraint("workspace_id", "request_id", name="uq_currency_evidence_request"),
        UniqueConstraint("supersedes_evidence_id", name="uq_currency_evidence_successor"),
        Index(
            "ix_currency_evidence_product_time",
            "workspace_id",
            "product_id",
            "recorded_at",
        ),
        CheckConstraint(
            "kind IN ('EXECUTION_DOCUMENT','HISTORICAL_LISTINGS')",
            name="currency_evidence_kind",
        ),
        CheckConstraint(
            "verification = 'USER_VERIFIED_SOURCE'",
            name="currency_evidence_verification",
        ),
        CheckConstraint(
            "length(trim(source_reference)) BETWEEN 3 AND 1000",
            name="currency_evidence_reference",
        ),
        CheckConstraint("id <> supersedes_evidence_id", name="currency_evidence_not_self"),
        CheckConstraint(
            "request_fingerprint ~ '^[0-9a-f]{64}$'",
            name="currency_evidence_fingerprint",
        ),
        CheckConstraint(
            "(kind = 'EXECUTION_DOCUMENT' AND trade_id IS NOT NULL AND execution_id IS NOT NULL "
            "AND (currency_code IS NOT NULL OR trading_venue_id IS NOT NULL) "
            "AND valid_from IS NULL AND valid_to IS NULL AND NOT complete_listing_set) OR "
            "(kind = 'HISTORICAL_LISTINGS' AND trade_id IS NULL AND execution_id IS NULL "
            "AND currency_code IS NULL AND trading_venue_id IS NULL AND valid_from IS NOT NULL "
            "AND valid_to IS NOT NULL AND valid_from < valid_to)",
            name="currency_evidence_shape",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="RESTRICT"))
    product_id: Mapped[UUID] = mapped_column(ForeignKey("warrants.id", ondelete="RESTRICT"))
    kind: Mapped[CurrencyEvidenceKind] = mapped_column(String(32))
    source_reference: Mapped[str] = mapped_column(String(1000))
    verification: Mapped[Literal["USER_VERIFIED_SOURCE"]] = mapped_column(String(32))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_by: Mapped[UUID] = mapped_column(Uuid())
    supersedes_evidence_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("currency_source_evidence.id", ondelete="RESTRICT")
    )
    request_id: Mapped[UUID] = mapped_column(Uuid())
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    revoked: Mapped[bool] = mapped_column(Boolean())
    trade_id: Mapped[UUID | None] = mapped_column(ForeignKey("trades.id", ondelete="RESTRICT"))
    execution_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("execution_records.id", ondelete="RESTRICT")
    )
    currency_code: Mapped[str | None] = mapped_column(
        ForeignKey("currencies.code", ondelete="RESTRICT")
    )
    trading_venue_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("trading_venues.id", ondelete="RESTRICT")
    )
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    listings: Mapped[list[dict[str, Any]]] = mapped_column(JSON())
    complete_listing_set: Mapped[bool] = mapped_column(Boolean())


class CurrencyEvidenceListingReferenceModel(Base):
    """Database-populated reference protection, never an independent source fact."""

    __tablename__ = "currency_source_evidence_listing_refs"
    evidence_id: Mapped[UUID] = mapped_column(
        ForeignKey("currency_source_evidence.id", ondelete="RESTRICT"), primary_key=True
    )
    trading_venue_id: Mapped[UUID] = mapped_column(
        ForeignKey("trading_venues.id", ondelete="RESTRICT"), primary_key=True
    )
    currency_code: Mapped[str | None] = mapped_column(
        ForeignKey("currencies.code", ondelete="RESTRICT")
    )


def to_domain(row: CurrencyEvidenceModel) -> CurrencyEvidence:
    return CurrencyEvidence(
        id=row.id,
        workspace_id=row.workspace_id,
        product_id=row.product_id,
        kind=row.kind,
        source_reference=row.source_reference,
        verification=row.verification,
        recorded_at=(
            row.recorded_at.replace(tzinfo=UTC)
            if row.recorded_at.utcoffset() is None
            else row.recorded_at
        ),
        recorded_by=row.recorded_by,
        supersedes_evidence_id=row.supersedes_evidence_id,
        request_id=row.request_id,
        request_fingerprint=row.request_fingerprint,
        revoked=row.revoked,
        trade_id=row.trade_id,
        execution_id=row.execution_id,
        currency_code=row.currency_code,
        trading_venue_id=row.trading_venue_id,
        valid_from=(
            row.valid_from.replace(tzinfo=UTC)
            if row.valid_from is not None and row.valid_from.utcoffset() is None
            else row.valid_from
        ),
        valid_to=(
            row.valid_to.replace(tzinfo=UTC)
            if row.valid_to is not None and row.valid_to.utcoffset() is None
            else row.valid_to
        ),
        listings=tuple(
            CurrencyListingEvidence(UUID(item["trading_venue_id"]), item["currency_code"])
            for item in row.listings
        ),
        complete_listing_set=row.complete_listing_set,
    )


class SqlAlchemyCurrencyEvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, evidence: CurrencyEvidence) -> None:
        self._session.add(
            CurrencyEvidenceModel(
                **{
                    field: getattr(evidence, field)
                    for field in CurrencyEvidence.__dataclass_fields__
                    if field != "listings"
                },
                listings=[
                    {
                        "trading_venue_id": str(item.trading_venue_id),
                        "currency_code": item.currency_code,
                    }
                    for item in evidence.listings
                ],
            )
        )
        await self._session.flush()

    async def find_request(self, workspace_id: UUID, request_id: UUID) -> CurrencyEvidence | None:
        row = await self._session.scalar(
            select(CurrencyEvidenceModel).where(
                CurrencyEvidenceModel.workspace_id == workspace_id,
                CurrencyEvidenceModel.request_id == request_id,
            )
        )
        return None if row is None else to_domain(row)

    async def get(self, workspace_id: UUID, evidence_id: UUID) -> CurrencyEvidence | None:
        row = await self._session.scalar(
            select(CurrencyEvidenceModel).where(
                CurrencyEvidenceModel.workspace_id == workspace_id,
                CurrencyEvidenceModel.id == evidence_id,
            )
        )
        return None if row is None else to_domain(row)

    async def has_successor(self, evidence_id: UUID) -> bool:
        return (
            await self._session.scalar(
                select(CurrencyEvidenceModel.id).where(
                    CurrencyEvidenceModel.supersedes_evidence_id == evidence_id
                )
            )
            is not None
        )

    async def list_for_product(
        self, workspace_id: UUID, product_id: UUID, limit: int = 1000
    ) -> tuple[CurrencyEvidence, ...]:
        return await self._list(workspace_id, product_id, limit)

    async def list_for_workspace(
        self, workspace_id: UUID, limit: int
    ) -> tuple[CurrencyEvidence, ...]:
        return await self._list(workspace_id, None, limit)

    async def _list(
        self, workspace_id: UUID, product_id: UUID | None, limit: int
    ) -> tuple[CurrencyEvidence, ...]:
        if limit < 1:
            raise ValueError("Evidence limit must be positive")
        query = select(CurrencyEvidenceModel).where(
            CurrencyEvidenceModel.workspace_id == workspace_id
        )
        if product_id is not None:
            query = query.where(CurrencyEvidenceModel.product_id == product_id)
        rows = tuple(
            await self._session.scalars(
                query.order_by(CurrencyEvidenceModel.recorded_at, CurrencyEvidenceModel.id).limit(
                    limit + 1
                )
            )
        )
        if len(rows) > limit:
            raise CurrencyEvidenceLimitExceeded("Currency source history exceeds read bound")
        return tuple(to_domain(row) for row in rows)
