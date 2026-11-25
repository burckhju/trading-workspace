"""Append-only current-unit evidence, independently revisioned for each listing."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    select,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.features.product.domain.listing_unit_evidence import (
    ListingUnitBinding,
    ListingUnitRevision,
    QualifiedGettexListingSource,
)

BINDING = TypeAdapter(ListingUnitBinding)
SOURCE = TypeAdapter(QualifiedGettexListingSource)


class ListingUnitEvidenceModel(Base):
    __tablename__ = "product_listing_unit_evidence"
    __table_args__ = (
        Index(
            "uq_listing_unit_root",
            "workspace_id",
            "listing_id",
            unique=True,
            postgresql_where=text("previous_revision_id IS NULL"),
            sqlite_where=text("previous_revision_id IS NULL"),
        ),
        Index("uq_listing_unit_successor", "previous_revision_id", unique=True),
        Index(
            "uq_listing_unit_revision", "workspace_id", "listing_id", "revision_number", unique=True
        ),
        Index("uq_listing_unit_request", "workspace_id", "request_id", unique=True),
        Index("ix_listing_unit_history", "workspace_id", "listing_id", "recorded_at"),
        CheckConstraint("revision_number > 0", name="listing_unit_revision_positive"),
        CheckConstraint("id <> previous_revision_id", name="listing_unit_not_self"),
        CheckConstraint(
            "length(request_fingerprint)=64 AND length(kid_document_sha256)=64",
            name="listing_unit_hash_lengths",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="RESTRICT"))
    warrant_id: Mapped[UUID] = mapped_column(ForeignKey("warrants.id", ondelete="RESTRICT"))
    listing_id: Mapped[UUID] = mapped_column(ForeignKey("warrant_listings.id", ondelete="RESTRICT"))
    terms_id: Mapped[UUID] = mapped_column(
        ForeignKey("warrant_terms_versions.id", ondelete="RESTRICT")
    )
    previous_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("product_listing_unit_evidence.id", ondelete="RESTRICT")
    )
    revision_number: Mapped[int] = mapped_column(Integer())
    request_id: Mapped[UUID] = mapped_column(Uuid())
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    kid_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("product_review_documents.id", ondelete="RESTRICT")
    )
    kid_document_sha256: Mapped[str] = mapped_column(String(64))
    product_class: Mapped[str] = mapped_column(String(80))
    binding: Mapped[dict[str, Any]] = mapped_column(JSON())
    source: Mapped[dict[str, Any]] = mapped_column(JSON())
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    review_reference: Mapped[str] = mapped_column(Text())
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_by: Mapped[UUID] = mapped_column(Uuid())


def to_revision(row: ListingUnitEvidenceModel) -> ListingUnitRevision:
    binding = BINDING.validate_python(row.binding)
    source = SOURCE.validate_python(row.source)
    if (
        row.warrant_id != binding.product.warrant_id
        or row.terms_id != binding.product.current_terms_id
        or row.listing_id != binding.route.listing_id
    ):
        raise ValueError("LISTING_UNIT_STORED_BINDING_INVALID")
    return ListingUnitRevision(
        row.id,
        row.workspace_id,
        row.warrant_id,
        row.listing_id,
        row.revision_number,
        row.previous_revision_id,
        row.request_id,
        row.request_fingerprint,
        binding,
        row.kid_revision_id,
        row.kid_document_sha256,
        row.product_class,
        source,
        row.reviewed_at,
        row.review_reference,
        row.recorded_at,
        row.recorded_by,
    )


class ListingUnitEvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def latest(
        self, workspace_id: UUID, warrant_id: UUID, listing_id: UUID, known_at: datetime
    ) -> ListingUnitEvidenceModel | None:
        row: ListingUnitEvidenceModel | None = await self.session.scalar(
            select(ListingUnitEvidenceModel)
            .where(
                ListingUnitEvidenceModel.workspace_id == workspace_id,
                ListingUnitEvidenceModel.warrant_id == warrant_id,
                ListingUnitEvidenceModel.listing_id == listing_id,
                ListingUnitEvidenceModel.recorded_at <= known_at,
            )
            .order_by(ListingUnitEvidenceModel.revision_number.desc())
            .limit(1)
        )
        return row

    async def request(
        self, workspace_id: UUID, request_id: UUID
    ) -> ListingUnitEvidenceModel | None:
        row: ListingUnitEvidenceModel | None = await self.session.scalar(
            select(ListingUnitEvidenceModel).where(
                ListingUnitEvidenceModel.workspace_id == workspace_id,
                ListingUnitEvidenceModel.request_id == request_id,
            )
        )
        return row

    async def add(self, value: ListingUnitRevision) -> None:
        self.session.add(
            ListingUnitEvidenceModel(
                id=value.id,
                workspace_id=value.workspace_id,
                warrant_id=value.warrant_id,
                listing_id=value.listing_id,
                terms_id=value.binding.product.current_terms_id,
                previous_revision_id=value.previous_revision_id,
                revision_number=value.revision_number,
                request_id=value.request_id,
                request_fingerprint=value.request_fingerprint,
                kid_revision_id=value.kid_revision_id,
                kid_document_sha256=value.kid_document_sha256,
                product_class=value.product_class,
                binding=BINDING.dump_python(value.binding, mode="json"),
                source=SOURCE.dump_python(value.source, mode="json"),
                reviewed_at=value.reviewed_at,
                review_reference=value.review_reference,
                recorded_at=value.recorded_at,
                recorded_by=value.recorded_by,
            )
        )
        await self.session.flush()
