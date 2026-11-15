"""Explicit session manifest imports and provider-free saved evidence reads."""

import base64
import binascii
import hashlib
import json
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ApplicationError
from app.features.market.persistence.models import ListingModel, TradingVenueModel, UnderlyingModel
from app.features.market_data.domain.session_evidence import (
    MAX_DOCUMENT_BYTES,
    MAX_MANIFEST_BYTES,
    MAX_SESSION_DAYS,
    InstrumentKind,
    SessionBinding,
    SessionDay,
    SessionEvidenceCurrent,
    SessionEvidenceImportCommand,
    SessionEvidenceRead,
    SessionEvidenceRevision,
    SessionManifest,
    SessionReadStatus,
    SessionSourceProvenance,
    aware,
    reference,
)
from app.features.market_data.persistence.session_evidence import (
    MANIFEST_ADAPTER,
    SqlAlchemySessionEvidenceRepository,
)
from app.features.product.persistence.models import WarrantListingModel, WarrantModel


def session_error(code: str, message: str, status: int = 422) -> ApplicationError:
    return ApplicationError(code=code, message=message, status_code=status)


def fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


def _distinct_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError(f"Non-JSON numeric constant: {value}")


def validate_import(
    command: SessionEvidenceImportCommand, now: datetime
) -> tuple[SessionManifest, bytes]:
    """Validate actual original bytes; no URL or provider is consulted."""
    try:
        manifest_bytes = command.manifest_json.encode("utf-8")
        if not 0 < len(manifest_bytes) <= MAX_MANIFEST_BYTES:
            raise ValueError("Manifest size limit")
        if len(command.document_base64) > ((MAX_DOCUMENT_BYTES + 2) // 3) * 4:
            raise ValueError("Source document size limit")
        document = base64.b64decode(command.document_base64, validate=True)
        if not 0 < len(document) <= MAX_DOCUMENT_BYTES:
            raise ValueError("Empty or oversized original source document")
        if (
            hashlib.sha256(manifest_bytes).hexdigest() != command.manifest_sha256
            or hashlib.sha256(document).hexdigest() != command.document_sha256
        ):
            raise ValueError("Original bytes do not match their declared SHA256")
        reference(command.document_filename, maximum=255)
        if any(char in command.document_filename for char in ("/", "\\", "\x00")):
            raise ValueError("Source document filename must not contain a path")
        if command.document_media_type not in {
            "application/pdf",
            "application/json",
            "text/csv",
            "text/plain",
            "text/html",
        }:
            raise ValueError("Unsupported original source document media type")
        reference(command.review_reference)
        if not aware(now) or not aware(command.reviewed_at) or command.reviewed_at > now:
            raise ValueError("Document review needs a known, non-future instant")
        if command.retrieved_at is not None and (
            not aware(command.retrieved_at) or command.retrieved_at > now
        ):
            raise ValueError("Document retrieval must retain its known, non-future instant")
        raw = json.loads(
            command.manifest_json,
            object_pairs_hook=_distinct_object,
            parse_constant=_invalid_constant,
        )
        manifest = MANIFEST_ADAPTER.validate_python(raw)
        if manifest.source_document_sha256 != command.document_sha256:
            raise ValueError("Manifest must name this exact original source document")
        if manifest.source_published_at is not None and (
            manifest.source_published_at > command.reviewed_at
        ):
            raise ValueError("Document cannot be reviewed before its known publication instant")
        if manifest.source_published_on is not None and (
            manifest.source_published_on
            > (command.reviewed_at.astimezone(UTC) + timedelta(hours=14)).date()
        ):
            raise ValueError("Document publication date is definitely later than its review")
        return manifest, document
    except (ValueError, TypeError, RecursionError, binascii.Error, UnicodeError) as error:
        raise session_error(
            "SESSION_EVIDENCE_INVALID",
            "Das Sitzungspaket ist ungültig; Originalbelege, Hashes und Zeitangaben prüfen.",
        ) from error


async def require_instrument(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    instrument_kind: InstrumentKind,
    instrument_id: UUID,
    lock: bool = False,
) -> None:
    if instrument_kind == "UNDERLYING":
        query = select(UnderlyingModel.id).where(
            UnderlyingModel.id == instrument_id, UnderlyingModel.workspace_id == workspace_id
        )
    elif instrument_kind == "WARRANT":
        query = select(WarrantModel.id).where(
            WarrantModel.id == instrument_id, WarrantModel.workspace_id == workspace_id
        )
    else:
        raise session_error("SESSION_EVIDENCE_INVALID", "Unbekannte Instrumentart.")
    found = await session.scalar(query.with_for_update() if lock else query)
    if found is None:
        raise session_error(
            "SESSION_EVIDENCE_SCOPE_NOT_FOUND",
            "Instrument in diesem Workspace nicht gefunden.",
            404,
        )


async def binding_matches(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    binding: SessionBinding,
) -> bool:
    if binding.instrument_kind == "UNDERLYING":
        query = select(ListingModel.id).where(
            ListingModel.id == binding.listing_id,
            ListingModel.workspace_id == workspace_id,
            ListingModel.underlying_id == binding.instrument_id,
            ListingModel.trading_venue_id == binding.trading_venue_id,
        )
    else:
        query = select(WarrantListingModel.id).where(
            WarrantListingModel.id == binding.listing_id,
            WarrantListingModel.workspace_id == workspace_id,
            WarrantListingModel.warrant_id == binding.instrument_id,
            WarrantListingModel.trading_venue_id == binding.trading_venue_id,
        )
    venue = await session.scalar(
        select(TradingVenueModel.id).where(
            TradingVenueModel.id == binding.trading_venue_id,
            TradingVenueModel.mic == binding.venue_mic,
        )
    )
    # Current reference clocks are not historical timezone evidence. The source
    # explicitly binds its historical zone and validity; never replace that zone.
    return venue is not None and await session.scalar(query) is not None


class SessionEvidenceImportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = SqlAlchemySessionEvidenceRepository(session)

    async def record(
        self,
        *,
        workspace_id: UUID,
        actor_id: UUID,
        command: SessionEvidenceImportCommand,
        now: datetime | None = None,
    ) -> SessionEvidenceRevision:
        clock = now or datetime.now(UTC)
        manifest, _document = validate_import(command, clock)
        binding = manifest.binding
        request_fingerprint = fingerprint(
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
        try:
            await self._session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            with self._session.no_autoflush:
                await require_instrument(
                    self._session,
                    workspace_id=workspace_id,
                    instrument_kind=binding.instrument_kind,
                    instrument_id=binding.instrument_id,
                    lock=True,
                )
                replay = await self._repository.find_request(workspace_id, command.request_id)
                if replay is not None:
                    if replay.request_fingerprint != request_fingerprint:
                        raise session_error(
                            "SESSION_EVIDENCE_REQUEST_CONFLICT",
                            "Die Vorgangskennung gehört zu einem anderen Importpaket.",
                            409,
                        )
                    await self._session.rollback()
                    return replay
                clock = now or datetime.now(UTC)
                current = await self._repository.latest(
                    workspace_id,
                    binding.instrument_kind,
                    binding.instrument_id,
                    datetime.max.replace(tzinfo=UTC),
                )
                if command.supersedes_revision_id != (current.id if current else None) or (
                    current is not None and current.recorded_at > clock
                ):
                    raise session_error(
                        "SESSION_EVIDENCE_REVISION_CONFLICT",
                        "Die Sitzungsevidenz wurde geändert; aktuellen Vorgänger erneut lesen.",
                        409,
                    )
                if not await binding_matches(
                    self._session, workspace_id=workspace_id, binding=binding
                ):
                    raise session_error(
                        "SESSION_EVIDENCE_BINDING_MISMATCH",
                        "Instrument, Listing und Handelsplatz passen nicht zusammen.",
                    )
                source = SessionSourceProvenance(
                    manifest_sha256=command.manifest_sha256,
                    document_sha256=command.document_sha256,
                    document_filename=command.document_filename,
                    document_media_type=command.document_media_type,
                    publisher=manifest.source_publisher,
                    reference=manifest.source_reference,
                    published_at=manifest.source_published_at,
                    published_on=manifest.source_published_on,
                    retrieved_at=command.retrieved_at,
                    reviewed_at=command.reviewed_at,
                    review_reference=command.review_reference,
                    recorded_by=actor_id,
                )
                revision = SessionEvidenceRevision(
                    id=uuid4(),
                    workspace_id=workspace_id,
                    instrument_kind=binding.instrument_kind,
                    instrument_id=binding.instrument_id,
                    revision_number=current.revision_number + 1 if current else 1,
                    supersedes_revision_id=command.supersedes_revision_id,
                    request_id=command.request_id,
                    request_fingerprint=request_fingerprint,
                    recorded_at=clock,
                    manifest=manifest,
                    source=source,
                    manifest_json=command.manifest_json,
                    document_base64=command.document_base64,
                )
            await self._repository.add(revision)
            await self._session.commit()
            return revision
        except IntegrityError as error:
            await self._session.rollback()
            raise session_error(
                "SESSION_EVIDENCE_REVISION_CONFLICT", "Sitzungsevidenz gleichzeitig geändert.", 409
            ) from error
        except Exception:
            await self._session.rollback()
            raise


class SessionEvidenceReader:
    """The caller supplies one snapshot; no flush, transaction, provider or writes."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = SqlAlchemySessionEvidenceRepository(session)

    async def _selected(
        self,
        *,
        workspace_id: UUID,
        instrument_kind: InstrumentKind,
        instrument_id: UUID,
        known_at: datetime,
        expected_listing_id: UUID | None,
    ) -> tuple[SessionEvidenceRevision | None, tuple[str, ...]]:
        if not aware(known_at):
            raise session_error("SESSION_EVIDENCE_INVALID", "Wissenszeit benötigt eine Zeitzone.")
        with self._session.no_autoflush:
            await require_instrument(
                self._session,
                workspace_id=workspace_id,
                instrument_kind=instrument_kind,
                instrument_id=instrument_id,
            )
            revision = await self._repository.latest(
                workspace_id,
                instrument_kind,
                instrument_id,
                known_at,
            )
            if revision is None:
                return None, ("SESSION_EVIDENCE_MISSING",)
            reasons: list[str] = []
            if (
                expected_listing_id is not None
                and revision.manifest.binding.listing_id != expected_listing_id
            ):
                reasons.append("SESSION_LISTING_BINDING_MISMATCH")
            if not await binding_matches(
                self._session, workspace_id=workspace_id, binding=revision.manifest.binding
            ):
                reasons.append("SESSION_OWNER_BINDING_CHANGED")
            if revision.manifest.evidence_status == "WITHDRAWN":
                reasons.append("SESSION_EVIDENCE_WITHDRAWN")
            return revision, tuple(reasons)

    async def current(
        self,
        *,
        workspace_id: UUID,
        instrument_kind: InstrumentKind,
        instrument_id: UUID,
        known_at: datetime,
        expected_listing_id: UUID | None = None,
    ) -> SessionEvidenceCurrent:
        revision, reasons = await self._selected(
            workspace_id=workspace_id,
            instrument_kind=instrument_kind,
            instrument_id=instrument_id,
            known_at=known_at,
            expected_listing_id=expected_listing_id,
        )
        manifest = revision.manifest if revision else None
        return SessionEvidenceCurrent(
            workspace_id=workspace_id,
            instrument_kind=instrument_kind,
            instrument_id=instrument_id,
            known_at=known_at,
            revision_id=revision.id if revision else None,
            supersedes_revision_id=revision.supersedes_revision_id if revision else None,
            revision_number=revision.revision_number if revision else None,
            calendar_id=manifest.calendar_id if manifest else None,
            calendar_version=manifest.calendar_version if manifest else None,
            binding=manifest.binding if manifest else None,
            coverage_start=manifest.coverage_start if manifest else None,
            coverage_end=manifest.coverage_end if manifest else None,
            evidence_status=manifest.evidence_status if manifest else None,
            source=revision.source if revision else None,
            recorded_at=revision.recorded_at if revision else None,
            read_at=datetime.now(UTC),
            status="MISSING" if revision is None else "UNSUITABLE" if reasons else "AVAILABLE",
            reasons=reasons,
        )

    async def read(
        self,
        *,
        workspace_id: UUID,
        instrument_kind: InstrumentKind,
        instrument_id: UUID,
        start_date: date,
        end_date: date,
        known_at: datetime,
        expected_listing_id: UUID | None = None,
    ) -> SessionEvidenceRead:
        if start_date > end_date or end_date == date.max:
            raise session_error("SESSION_EVIDENCE_INVALID", "Ungültiger Sitzungsausschnitt.")
        revision, selection_reasons = await self._selected(
            workspace_id=workspace_id,
            instrument_kind=instrument_kind,
            instrument_id=instrument_id,
            known_at=known_at,
            expected_listing_id=expected_listing_id,
        )
        manifest = revision.manifest if revision else None
        reasons = list(selection_reasons)
        days: tuple[SessionDay, ...] = ()
        missing: tuple[date, ...] = ()
        status: SessionReadStatus
        if (end_date - start_date).days >= MAX_SESSION_DAYS:
            status = "LIMIT_EXCEEDED"
            reasons.append("SESSION_RANGE_LIMIT_EXCEEDED")
        else:
            dates = tuple(
                start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)
            )
            days = (
                tuple(day for day in manifest.days if start_date <= day.session_date <= end_date)
                if manifest
                else ()
            )
            indexed = {day.session_date: day for day in days}
            missing = tuple(day for day in dates if day not in indexed)
            if manifest is None:
                status = "MISSING"
            elif selection_reasons:
                status = "UNSUITABLE"
            else:
                if (
                    start_date < manifest.binding.valid_from
                    or end_date > manifest.binding.valid_through
                ):
                    reasons.append("SESSION_BINDING_VALIDITY_GAP")
                if start_date < manifest.coverage_start or end_date > manifest.coverage_end:
                    reasons.append("SESSION_COVERAGE_RANGE_GAP")
                if missing:
                    reasons.append("SESSION_DAY_EVIDENCE_GAP")
                if any(day.status == "UNKNOWN" for day in days):
                    reasons.append("SESSION_DAY_EVIDENCE_UNKNOWN")
                status = "INCOMPLETE" if reasons else "COMPLETE"
        material = {
            "workspace_id": workspace_id,
            "instrument_kind": instrument_kind,
            "instrument_id": instrument_id,
            "revision_id": revision.id if revision else None,
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
            "reasons": reasons,
        }
        return SessionEvidenceRead(
            workspace_id=workspace_id,
            instrument_kind=instrument_kind,
            instrument_id=instrument_id,
            start_date=start_date,
            end_date=end_date,
            known_at=known_at,
            revision_id=revision.id if revision else None,
            supersedes_revision_id=revision.supersedes_revision_id if revision else None,
            revision_number=revision.revision_number if revision else None,
            calendar_id=manifest.calendar_id if manifest else None,
            calendar_version=manifest.calendar_version if manifest else None,
            binding=manifest.binding if manifest else None,
            coverage_start=manifest.coverage_start if manifest else None,
            coverage_end=manifest.coverage_end if manifest else None,
            evidence_status=manifest.evidence_status if manifest else None,
            days=days,
            status=status,
            reasons=tuple(reasons),
            missing_dates=missing,
            source=revision.source if revision else None,
            fingerprint=fingerprint(material),
            recorded_at=revision.recorded_at if revision else None,
            read_at=datetime.now(UTC),
        )
