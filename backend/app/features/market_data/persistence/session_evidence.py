"""Append-only calendar manifests with original source documents."""

import base64
import hashlib
from datetime import UTC, datetime
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
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    select,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.features.market_data.domain.session_evidence import (
    InstrumentKind,
    SessionEvidenceRevision,
    SessionManifest,
    SessionSourceProvenance,
)

MANIFEST_ADAPTER = TypeAdapter(SessionManifest)
SOURCE_ADAPTER = TypeAdapter(SessionSourceProvenance)


class SessionEvidenceModel(Base):
    __tablename__ = "market_session_evidence"
    __table_args__ = (
        UniqueConstraint("workspace_id", "request_id", name="uq_session_evidence_request"),
        UniqueConstraint("supersedes_revision_id", name="uq_session_evidence_successor"),
        UniqueConstraint(
            "workspace_id",
            "instrument_kind",
            "instrument_id",
            "revision_number",
            name="uq_session_evidence_revision",
        ),
        Index(
            "uq_session_evidence_root",
            "workspace_id",
            "instrument_kind",
            "instrument_id",
            unique=True,
            postgresql_where=text("supersedes_revision_id IS NULL"),
            sqlite_where=text("supersedes_revision_id IS NULL"),
        ),
        Index(
            "ix_session_evidence_history",
            "workspace_id",
            "instrument_kind",
            "instrument_id",
            "recorded_at",
        ),
        CheckConstraint("revision_number >= 1", name="session_evidence_revision_positive"),
        CheckConstraint("id <> supersedes_revision_id", name="session_evidence_not_self"),
        CheckConstraint(
            "(instrument_kind = 'UNDERLYING' AND underlying_id = instrument_id "
            "AND underlying_id IS NOT NULL AND listing_id IS NOT NULL "
            "AND warrant_id IS NULL AND warrant_listing_id IS NULL) OR "
            "(instrument_kind = 'WARRANT' AND warrant_id = instrument_id "
            "AND warrant_id IS NOT NULL AND warrant_listing_id IS NOT NULL "
            "AND underlying_id IS NULL AND listing_id IS NULL)",
            name="session_evidence_owner_matches_kind",
        ),
        CheckConstraint(
            "length(manifest_sha256) = 64 AND length(document_sha256) = 64 "
            "AND length(request_fingerprint) = 64",
            name="session_evidence_hash_lengths",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="RESTRICT"))
    instrument_kind: Mapped[str] = mapped_column(String(16))
    instrument_id: Mapped[UUID] = mapped_column(Uuid())
    underlying_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("underlyings.id", ondelete="RESTRICT")
    )
    warrant_id: Mapped[UUID | None] = mapped_column(ForeignKey("warrants.id", ondelete="RESTRICT"))
    listing_id: Mapped[UUID | None] = mapped_column(ForeignKey("listings.id", ondelete="RESTRICT"))
    warrant_listing_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("warrant_listings.id", ondelete="RESTRICT")
    )
    trading_venue_id: Mapped[UUID] = mapped_column(
        ForeignKey("trading_venues.id", ondelete="RESTRICT")
    )
    revision_number: Mapped[int] = mapped_column(Integer())
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("market_session_evidence.id", ondelete="RESTRICT")
    )
    request_id: Mapped[UUID] = mapped_column(Uuid())
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    recorded_by: Mapped[UUID] = mapped_column(Uuid())
    manifest_json: Mapped[str] = mapped_column(Text())
    manifest_sha256: Mapped[str] = mapped_column(String(64))
    document_bytes: Mapped[bytes] = mapped_column(LargeBinary())
    document_sha256: Mapped[str] = mapped_column(String(64))
    source: Mapped[dict[str, Any]] = mapped_column(JSON())


def to_revision(row: SessionEvidenceModel) -> SessionEvidenceRevision:
    manifest = MANIFEST_ADAPTER.validate_json(row.manifest_json)
    source = SOURCE_ADAPTER.validate_python(row.source)
    if (
        hashlib.sha256(row.manifest_json.encode("utf-8")).hexdigest() != row.manifest_sha256
        or hashlib.sha256(row.document_bytes).hexdigest() != row.document_sha256
        or manifest.source_document_sha256 != row.document_sha256
        or manifest.binding.instrument_kind != row.instrument_kind
        or manifest.binding.instrument_id != row.instrument_id
        or manifest.binding.listing_id != (row.listing_id or row.warrant_listing_id)
        or manifest.binding.trading_venue_id != row.trading_venue_id
        or source.recorded_by != row.recorded_by
        or source.manifest_sha256 != row.manifest_sha256
        or source.document_sha256 != row.document_sha256
    ):
        raise ValueError("Stored session evidence disagrees with its owner scope")
    return SessionEvidenceRevision(
        id=row.id,
        workspace_id=row.workspace_id,
        instrument_kind=manifest.binding.instrument_kind,
        instrument_id=row.instrument_id,
        revision_number=row.revision_number,
        supersedes_revision_id=row.supersedes_revision_id,
        request_id=row.request_id,
        request_fingerprint=row.request_fingerprint,
        recorded_at=(
            row.recorded_at.replace(tzinfo=UTC)
            if row.recorded_at.utcoffset() is None
            else row.recorded_at
        ),
        manifest=manifest,
        source=source,
        manifest_json=row.manifest_json,
        document_base64=base64.b64encode(row.document_bytes).decode("ascii"),
    )


class SqlAlchemySessionEvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def latest(
        self,
        workspace_id: UUID,
        instrument_kind: InstrumentKind,
        instrument_id: UUID,
        known_at: datetime,
    ) -> SessionEvidenceRevision | None:
        row = await self._session.scalar(
            select(SessionEvidenceModel)
            .where(
                SessionEvidenceModel.workspace_id == workspace_id,
                SessionEvidenceModel.instrument_kind == instrument_kind,
                SessionEvidenceModel.instrument_id == instrument_id,
                SessionEvidenceModel.recorded_at <= known_at,
            )
            .order_by(SessionEvidenceModel.revision_number.desc())
            .limit(1)
        )
        return to_revision(row) if row is not None else None

    async def get(self, workspace_id: UUID, revision_id: UUID) -> SessionEvidenceRevision | None:
        row = await self._session.scalar(
            select(SessionEvidenceModel).where(
                SessionEvidenceModel.workspace_id == workspace_id,
                SessionEvidenceModel.id == revision_id,
            )
        )
        return to_revision(row) if row is not None else None

    async def find_request(
        self, workspace_id: UUID, request_id: UUID
    ) -> SessionEvidenceRevision | None:
        row = await self._session.scalar(
            select(SessionEvidenceModel).where(
                SessionEvidenceModel.workspace_id == workspace_id,
                SessionEvidenceModel.request_id == request_id,
            )
        )
        return to_revision(row) if row is not None else None

    async def add(self, revision: SessionEvidenceRevision) -> None:
        binding = revision.manifest.binding
        underlying = binding.instrument_kind == "UNDERLYING"
        self._session.add(
            SessionEvidenceModel(
                id=revision.id,
                workspace_id=revision.workspace_id,
                instrument_kind=revision.instrument_kind,
                instrument_id=revision.instrument_id,
                underlying_id=binding.instrument_id if underlying else None,
                warrant_id=None if underlying else binding.instrument_id,
                listing_id=binding.listing_id if underlying else None,
                warrant_listing_id=None if underlying else binding.listing_id,
                trading_venue_id=binding.trading_venue_id,
                revision_number=revision.revision_number,
                supersedes_revision_id=revision.supersedes_revision_id,
                request_id=revision.request_id,
                request_fingerprint=revision.request_fingerprint,
                recorded_at=revision.recorded_at,
                recorded_by=revision.source.recorded_by,
                manifest_json=revision.manifest_json,
                manifest_sha256=revision.source.manifest_sha256,
                document_bytes=base64.b64decode(revision.document_base64, validate=True),
                document_sha256=revision.source.document_sha256,
                source=SOURCE_ADAPTER.dump_python(revision.source, mode="json"),
            )
        )
        await self._session.flush()
