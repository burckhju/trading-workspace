"""One append-only, product-scoped evidence chain; original bytes stay auditable."""

import base64
import binascii
import hashlib
import json
import re
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
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
from app.features.product.domain.price_scale_evidence import (
    MAX_DOCUMENT_BYTES,
    MAX_MANIFEST_BYTES,
    ProductPriceScaleImportCommand,
    ProductPriceScaleManifest,
    ProductPriceScaleRevision,
    ProductPriceScaleSource,
    aware,
    reference,
    sha256_text,
)

MANIFEST_ADAPTER = TypeAdapter(ProductPriceScaleManifest)
SOURCE_ADAPTER = TypeAdapter(ProductPriceScaleSource)


def fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def _distinct_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key in original manifest")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError(f"Non-JSON numeric constant: {value}")


def validate_originals(
    command: ProductPriceScaleImportCommand, now: datetime
) -> tuple[ProductPriceScaleManifest, bytes]:
    """The same byte, temporal and schema validation guards imports and stored reads."""
    try:
        manifest_bytes = command.manifest_json.encode("utf-8")
        if not 0 < len(manifest_bytes) <= MAX_MANIFEST_BYTES:
            raise ValueError("Manifest size limit")
        if len(command.document_base64) > ((MAX_DOCUMENT_BYTES + 2) // 3) * 4:
            raise ValueError("Source document size limit")
        document = base64.b64decode(command.document_base64, validate=True)
        if not 0 < len(document) <= MAX_DOCUMENT_BYTES:
            raise ValueError("Empty or oversized source document")
        sha256_text(command.manifest_sha256)
        sha256_text(command.document_sha256)
        if (
            hashlib.sha256(manifest_bytes).hexdigest() != command.manifest_sha256
            or hashlib.sha256(document).hexdigest() != command.document_sha256
        ):
            raise ValueError("Original bytes disagree with their declared SHA256")
        reference(command.document_filename, 255)
        if any(character in command.document_filename for character in ("/", "\\", "\x00")):
            raise ValueError("Source filename must not contain a path")
        if command.document_media_type not in {
            "application/pdf",
            "application/json",
            "text/csv",
            "text/plain",
            "text/html",
        }:
            raise ValueError("Unsupported original document media type")
        reference(command.review_reference)
        if not aware(now) or not aware(command.reviewed_at) or command.reviewed_at > now:
            raise ValueError("Review needs an explicit non-future instant")
        if command.retrieved_at is not None and (
            not aware(command.retrieved_at) or command.retrieved_at > now
        ):
            raise ValueError("Retrieval needs its known non-future instant")
        raw = json.loads(
            command.manifest_json,
            object_pairs_hook=_distinct_object,
            parse_constant=_invalid_constant,
        )
        if not isinstance(raw, dict):
            raise ValueError("Manifest must be a JSON object")
        for field in ("valid_from", "valid_until", "source_published_at"):
            value = raw.get(field)
            if field == "source_published_at" and value is None:
                continue
            if (
                not isinstance(value, str)
                or re.search(r"(?:Z|[+-][0-9]{2}:[0-9]{2})$", value) is None
                or not aware(datetime.fromisoformat(value))
            ):
                raise ValueError("Original clocks require explicit ISO text with an offset")
        published_on = raw.get("source_published_on")
        if published_on is not None and (
            not isinstance(published_on, str)
            or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", published_on) is None
            or date.fromisoformat(published_on).isoformat() != published_on
        ):
            raise ValueError("Original publication date requires exact YYYY-MM-DD text")
        manifest = MANIFEST_ADAPTER.validate_python(raw)
        if manifest.source_document_sha256 != command.document_sha256:
            raise ValueError("Manifest must identify this exact original document")
        if manifest.source_published_at is not None and (
            manifest.source_published_at > command.reviewed_at
        ):
            raise ValueError("A source cannot be reviewed before its publication")
        if manifest.source_published_on is not None and (
            manifest.source_published_on
            > (command.reviewed_at.astimezone(UTC) + timedelta(hours=14)).date()
        ):
            raise ValueError("Source publication date is definitely later than its review")
        return manifest, document
    except (TypeError, RecursionError, binascii.Error, UnicodeError) as error:
        raise ValueError("Invalid original evidence encoding") from error


def request_fingerprint(
    command: ProductPriceScaleImportCommand, workspace_id: UUID, actor_id: UUID
) -> str:
    return fingerprint(
        {
            "workspace_id": workspace_id,
            "actor_id": actor_id,
            **{
                key: value
                for key, value in asdict(command).items()
                if key not in {"manifest_json", "document_base64"}
            },
        }
    )


class ProductPriceScaleEvidenceModel(Base):
    __tablename__ = "product_price_scale_evidence"
    __table_args__ = (
        UniqueConstraint("workspace_id", "request_id", name="uq_product_price_scale_request"),
        UniqueConstraint("supersedes_revision_id", name="uq_product_price_scale_successor"),
        UniqueConstraint(
            "workspace_id",
            "warrant_id",
            "revision_number",
            name="uq_product_price_scale_revision",
        ),
        Index(
            "uq_product_price_scale_root",
            "workspace_id",
            "warrant_id",
            unique=True,
            postgresql_where=text("supersedes_revision_id IS NULL"),
            sqlite_where=text("supersedes_revision_id IS NULL"),
        ),
        Index(
            "ix_product_price_scale_history",
            "workspace_id",
            "warrant_id",
            "recorded_at",
        ),
        CheckConstraint("revision_number >= 1", name="product_price_scale_revision_positive"),
        CheckConstraint("id <> supersedes_revision_id", name="product_price_scale_not_self"),
        CheckConstraint(
            "length(manifest_sha256) = 64 AND length(document_sha256) = 64 "
            "AND length(request_fingerprint) = 64",
            name="product_price_scale_hash_lengths",
        ),
    )
    id: Mapped[UUID] = mapped_column(Uuid(), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="RESTRICT"))
    warrant_id: Mapped[UUID] = mapped_column(ForeignKey("warrants.id", ondelete="RESTRICT"))
    terms_id: Mapped[UUID] = mapped_column(
        ForeignKey("warrant_terms_versions.id", ondelete="RESTRICT")
    )
    revision_number: Mapped[int] = mapped_column(Integer())
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("product_price_scale_evidence.id", ondelete="RESTRICT")
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


def to_revision(row: ProductPriceScaleEvidenceModel) -> ProductPriceScaleRevision:
    clock = (
        row.recorded_at.replace(tzinfo=UTC)
        if row.recorded_at.utcoffset() is None
        else row.recorded_at
    )
    source = SOURCE_ADAPTER.validate_python(row.source)
    encoded = base64.b64encode(row.document_bytes).decode("ascii")
    command = ProductPriceScaleImportCommand(
        request_id=row.request_id,
        supersedes_revision_id=row.supersedes_revision_id,
        manifest_json=row.manifest_json,
        manifest_sha256=row.manifest_sha256,
        document_filename=source.document_filename,
        document_media_type=source.document_media_type,
        document_base64=encoded,
        document_sha256=row.document_sha256,
        reviewed_at=source.reviewed_at,
        review_reference=source.review_reference,
        retrieved_at=source.retrieved_at,
    )
    manifest, _ = validate_originals(command, clock)
    if (
        manifest.binding.warrant_id != row.warrant_id
        or manifest.binding.current_terms_id != row.terms_id
        or source.recorded_by != row.recorded_by
        or source.manifest_sha256 != row.manifest_sha256
        or source.document_sha256 != row.document_sha256
        or source.publisher != manifest.source_publisher
        or source.reference != manifest.source_reference
        or source.published_at != manifest.source_published_at
        or source.published_on != manifest.source_published_on
        or row.revision_number < 1
        or (row.revision_number == 1) != (row.supersedes_revision_id is None)
        or row.id == row.supersedes_revision_id
        or row.request_fingerprint
        != request_fingerprint(command, row.workspace_id, row.recorded_by)
    ):
        raise ValueError("Stored product scale evidence violates its scope or provenance")
    return ProductPriceScaleRevision(
        id=row.id,
        workspace_id=row.workspace_id,
        warrant_id=row.warrant_id,
        revision_number=row.revision_number,
        supersedes_revision_id=row.supersedes_revision_id,
        request_id=row.request_id,
        request_fingerprint=row.request_fingerprint,
        recorded_at=clock,
        manifest=manifest,
        source=source,
        manifest_json=row.manifest_json,
        document_base64=encoded,
    )


class SqlAlchemyProductPriceScaleEvidenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def latest(
        self, workspace_id: UUID, warrant_id: UUID, known_at: datetime
    ) -> ProductPriceScaleRevision | None:
        row = await self._session.scalar(
            select(ProductPriceScaleEvidenceModel)
            .where(
                ProductPriceScaleEvidenceModel.workspace_id == workspace_id,
                ProductPriceScaleEvidenceModel.warrant_id == warrant_id,
                ProductPriceScaleEvidenceModel.recorded_at <= known_at,
            )
            .order_by(ProductPriceScaleEvidenceModel.revision_number.desc())
            .limit(1)
        )
        return to_revision(row) if row is not None else None

    async def get(
        self, workspace_id: UUID, warrant_id: UUID, revision_id: UUID
    ) -> ProductPriceScaleRevision | None:
        row = await self._session.scalar(
            select(ProductPriceScaleEvidenceModel).where(
                ProductPriceScaleEvidenceModel.workspace_id == workspace_id,
                ProductPriceScaleEvidenceModel.warrant_id == warrant_id,
                ProductPriceScaleEvidenceModel.id == revision_id,
            )
        )
        return to_revision(row) if row is not None else None

    async def find_request(
        self, workspace_id: UUID, request_id: UUID
    ) -> ProductPriceScaleRevision | None:
        row = await self._session.scalar(
            select(ProductPriceScaleEvidenceModel).where(
                ProductPriceScaleEvidenceModel.workspace_id == workspace_id,
                ProductPriceScaleEvidenceModel.request_id == request_id,
            )
        )
        return to_revision(row) if row is not None else None

    async def add(self, revision: ProductPriceScaleRevision) -> None:
        self._session.add(
            ProductPriceScaleEvidenceModel(
                id=revision.id,
                workspace_id=revision.workspace_id,
                warrant_id=revision.warrant_id,
                terms_id=revision.manifest.binding.current_terms_id,
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
