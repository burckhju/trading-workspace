"""Explicit current-unit imports and passive reads within the Product owner."""

import hashlib
import re
from dataclasses import asdict
from datetime import UTC, datetime
from io import BytesIO
from typing import BinaryIO
from uuid import UUID, uuid4

from pypdf import PdfReader
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ApplicationError
from app.features.market.persistence.models import CurrencyModel, TradingVenueModel
from app.features.product.domain.listing_unit_evidence import (
    ListingUnitBinding,
    ListingUnitImportCommand,
    ListingUnitImportPreview,
    ListingUnitRead,
    ListingUnitRevision,
    ListingUnitRoute,
    ListingUnitRuleOriginal,
    ListingUnitRuleSet,
    ListingUnitRuleSource,
    QualifiedGettexListingSource,
)
from app.features.product.domain.models import WarrantLifecycle
from app.features.product.domain.price_scale_evidence import aware, reference, sha256_text
from app.features.product.persistence.listing_unit_evidence import (
    ListingUnitEvidenceModel,
    ListingUnitEvidenceRepository,
    to_revision,
)
from app.features.product.persistence.models import WarrantListingModel, WarrantModel
from app.features.product.persistence.price_scale_evidence import fingerprint
from app.features.product.persistence.review_evidence import ProductReviewDocumentModel
from app.features.product.service.listing_unit_sources import (
    MAX_PRETRADE_BYTES,
    MAX_RULE_DOCUMENT_BYTES,
    MAX_RULE_DOCUMENTS_BYTES,
    SUPPORTED_RULE_SETS,
    ListingUnitSourceError,
    require_stream_qualified,
    validate_qualified_source,
)
from app.features.product.service.listing_unit_sources import (
    qualify_gettex_listing_source as _qualify_source,
)
from app.features.product.service.price_scale_evidence import require_warrant
from app.features.product.service.review_evidence import ProductReviewEvidenceReader

__all__ = [
    "MAX_PRETRADE_BYTES",
    "MAX_RULE_DOCUMENTS_BYTES",
    "MAX_RULE_DOCUMENT_BYTES",
    "SUPPORTED_RULE_SETS",
    "ListingUnitEvidenceReader",
    "ListingUnitImportService",
    "ListingUnitSourceError",
    "qualify_gettex_listing_source",
]


def listing_unit_error(code: str, status: int = 422) -> ApplicationError:
    return ApplicationError(
        code=code,
        message="Listing-Einheitenbeleg ist nicht verwendbar; gebundene Originale prüfen.",
        status_code=status,
    )


def qualify_gettex_listing_source(
    *,
    source: BinaryIO,
    file_name: str,
    target_isin: str,
    rules: tuple[ListingUnitRuleOriginal, ...],
    known_at: datetime,
    retrieved_at: datetime | None = None,
    registry: tuple[ListingUnitRuleSet, ...] | None = None,
) -> QualifiedGettexListingSource:
    return _qualify_source(
        source=source,
        file_name=file_name,
        target_isin=target_isin,
        rules=rules,
        known_at=known_at,
        retrieved_at=retrieved_at,
        registry=SUPPORTED_RULE_SETS if registry is None else registry,
    )


def _route(route: ListingUnitRoute) -> None:
    if (
        not isinstance(route.listing_id, UUID)
        or route.provider != "GETTEX_DELAYED"
        or route.venue_mic != "MUND"
        or route.currency != "EUR"
    ):
        raise listing_unit_error("LISTING_UNIT_ROUTE_UNSUPPORTED")


def _clock(value: datetime, known_at: datetime) -> None:
    if not aware(value) or value > known_at:
        raise listing_unit_error("LISTING_UNIT_CLOCK_INVALID")


def _kid_class(row: ProductReviewDocumentModel) -> str:
    """Only the observed product heading, never debt form or an arbitrary word hit."""
    try:
        if hashlib.sha256(row.document).hexdigest() != row.document_sha256:
            raise ValueError("integrity")
        original = PdfReader(BytesIO(row.document))
        if not 1 <= len(original.pages) <= 12:
            raise ValueError("page limit")
        heading = " ".join((original.pages[0].extract_text() or "").split())
        if (
            re.search(r"\bPRODUKT\s+Call Optionsschein bezogen auf eine Aktie\s+ISIN\b", heading)
            is None
        ):
            raise ValueError("unsupported product heading")
    except Exception as error:
        # PDF implementations raise several malformed-object exception classes;
        # no untrusted PDF text or exception body crosses this boundary.
        raise listing_unit_error("LISTING_UNIT_PRODUCT_CLASS_UNPROVEN") from error
    return "CALL_WARRANT_ON_EQUITY"


async def _current_context(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    warrant_id: UUID,
    route: ListingUnitRoute,
    known_at: datetime,
    expected_kid_revision_id: UUID | None = None,
) -> tuple[ListingUnitBinding, ProductReviewDocumentModel, str]:
    _route(route)
    await require_warrant(session, workspace_id=workspace_id, warrant_id=warrant_id)
    warrant = await session.get(WarrantModel, warrant_id)
    listing = await session.get(WarrantListingModel, route.listing_id)
    venue = (
        await session.get(TradingVenueModel, listing.trading_venue_id)
        if listing is not None
        else None
    )
    currency = await session.get(CurrencyModel, route.currency)
    if warrant is None or warrant.lifecycle_status != WarrantLifecycle.ACTIVE:
        raise listing_unit_error("LISTING_UNIT_PRODUCT_INACTIVE")
    if (
        listing is None
        or listing.workspace_id != workspace_id
        or listing.warrant_id != warrant_id
        or listing.lifecycle_status != WarrantLifecycle.ACTIVE
        or listing.quotation_currency_code != route.currency
        or venue is None
        or not venue.is_active
        or venue.mic != route.venue_mic
        or currency is None
        or not currency.is_active
    ):
        raise listing_unit_error("LISTING_UNIT_CURRENT_BINDING_MISMATCH")
    for row_time in (warrant.updated_at, listing.updated_at, venue.updated_at, currency.updated_at):
        _clock(row_time, known_at)
    # Same Product-owner original facts, deliberately not current_for_review:
    # that composer may call this reader and must retain its own KID provenance.
    kid, product, facts, problems = await ProductReviewEvidenceReader(session)._facts(
        workspace_id=workspace_id, warrant_id=warrant_id, known_at=known_at
    )
    if problems:
        raise listing_unit_error(problems[0])
    if kid is None or product is None or facts is None:
        raise listing_unit_error("PRODUCT_REVIEW_DOCUMENT_MISSING")
    if expected_kid_revision_id is not None and kid.id != expected_kid_revision_id:
        raise listing_unit_error("LISTING_UNIT_IMPORT_KID_CHANGED", 409)
    if facts.currency != route.currency:
        raise listing_unit_error("LISTING_UNIT_KID_CURRENCY_MISMATCH")
    if facts.unit not in {None, "CURRENCY_PER_WARRANT"}:
        raise listing_unit_error("LISTING_UNIT_KID_UNIT_CONFLICT")
    product_class = _kid_class(kid)
    return (
        ListingUnitBinding(product, route, listing.version, venue.id, venue.version),
        kid,
        product_class,
    )


def _validated_source(
    source: QualifiedGettexListingSource,
    *,
    known_at: datetime,
    registry: tuple[ListingUnitRuleSet, ...],
) -> ListingUnitRuleSet:
    try:
        return validate_qualified_source(source, known_at=known_at, registry=registry)
    except ListingUnitSourceError as error:
        raise listing_unit_error(error.code) from error


def _command(command: ListingUnitImportCommand, now: datetime) -> None:
    if not aware(now):
        raise listing_unit_error("LISTING_UNIT_CLOCK_INVALID")
    _clock(command.reviewed_at, now)
    _route(command.route)
    try:
        reference(command.review_reference)
    except ValueError as error:
        raise listing_unit_error("LISTING_UNIT_REVIEW_REFERENCE_INVALID") from error


def _request_fingerprint(
    command: ListingUnitImportCommand,
    source: QualifiedGettexListingSource,
    workspace_id: UUID,
    warrant_id: UUID,
    actor_id: UUID,
) -> str:
    return fingerprint(
        {
            "command": asdict(command),
            "source_fingerprint": source.fingerprint,
            "workspace_id": workspace_id,
            "warrant_id": warrant_id,
            "actor_id": actor_id,
        }
    )


class ListingUnitImportService:
    def __init__(
        self, session: AsyncSession, *, registry: tuple[ListingUnitRuleSet, ...] | None = None
    ) -> None:
        self.session = session
        self.registry = SUPPORTED_RULE_SETS if registry is None else registry
        self.repository = ListingUnitEvidenceRepository(session)

    async def preview(
        self,
        *,
        workspace_id: UUID,
        warrant_id: UUID,
        command: ListingUnitImportCommand,
        source: QualifiedGettexListingSource,
        now: datetime | None = None,
    ) -> ListingUnitImportPreview:
        """Caller owns a read-only snapshot; no source IO, lock, flush or commit."""
        clock = now or datetime.now(UTC)
        _command(command, clock)
        try:
            require_stream_qualified(source)
        except ListingUnitSourceError as error:
            raise listing_unit_error(error.code) from error
        spec = _validated_source(source, known_at=clock, registry=self.registry)
        with self.session.no_autoflush:
            binding, kid, product_class = await _current_context(
                self.session,
                workspace_id=workspace_id,
                warrant_id=warrant_id,
                route=command.route,
                known_at=clock,
                expected_kid_revision_id=command.kid_revision_id,
            )
            if (
                source.pretrade.isin != binding.product.isin
                or source.pretrade.venue_mic != binding.route.venue_mic
                or source.pretrade.currency != binding.route.currency
                or product_class != spec.product_class
            ):
                raise listing_unit_error("LISTING_UNIT_SOURCE_PRODUCT_MISMATCH")
            previous = await self.repository.latest(
                workspace_id,
                warrant_id,
                command.route.listing_id,
                datetime.max.replace(tzinfo=UTC),
            )
            if previous is not None and previous.recorded_at > clock:
                raise listing_unit_error("LISTING_UNIT_CLOCK_INVALID")
            if command.expected_revision_id != (previous.id if previous else None):
                raise listing_unit_error("LISTING_UNIT_REVISION_CONFLICT", 409)
            material = {
                "workspace_id": workspace_id,
                "warrant_id": warrant_id,
                "binding": asdict(binding),
                "kid_revision_id": kid.id,
                "kid_document_sha256": kid.document_sha256,
                "product_class": product_class,
                "current_revision_id": previous.id if previous else None,
                "next_revision_number": previous.revision_number + 1 if previous else 1,
                "source_fingerprint": source.fingerprint,
            }
            return ListingUnitImportPreview(
                workspace_id,
                warrant_id,
                binding,
                kid.id,
                kid.document_sha256,
                product_class,
                previous.id if previous else None,
                previous.revision_number + 1 if previous else 1,
                source.fingerprint,
                fingerprint(material),
            )

    async def record(
        self,
        *,
        workspace_id: UUID,
        warrant_id: UUID,
        actor_id: UUID,
        command: ListingUnitImportCommand,
        source: QualifiedGettexListingSource,
        expected_preview_fingerprint: str,
        now: datetime | None = None,
    ) -> ListingUnitRevision:
        clock = now or datetime.now(UTC)
        _command(command, clock)
        _validated_source(source, known_at=clock, registry=self.registry)
        try:
            require_stream_qualified(source)
            sha256_text(expected_preview_fingerprint)
        except ValueError as error:
            raise listing_unit_error("LISTING_UNIT_PREVIEW_REQUIRED") from error
        material = _request_fingerprint(command, source, workspace_id, warrant_id, actor_id)
        try:
            await self.session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            await self.session.execute(text("SET LOCAL statement_timeout = '10000ms'"))
            await self.session.execute(text("SET LOCAL lock_timeout = '3000ms'"))
            with self.session.no_autoflush:
                await require_warrant(
                    self.session, workspace_id=workspace_id, warrant_id=warrant_id, lock=True
                )
                replay = await self.repository.request(workspace_id, command.request_id)
                if replay is not None:
                    if replay.request_fingerprint != material or replay.recorded_at > clock:
                        raise listing_unit_error("LISTING_UNIT_REQUEST_CONFLICT", 409)
                    result = to_revision(replay)
                    await self.session.rollback()
                    return result
                preview = await self.preview(
                    workspace_id=workspace_id,
                    warrant_id=warrant_id,
                    command=command,
                    source=source,
                    now=clock,
                )
                if preview.fingerprint != expected_preview_fingerprint:
                    raise listing_unit_error("LISTING_UNIT_PREVIEW_CHANGED", 409)
                result = ListingUnitRevision(
                    uuid4(),
                    workspace_id,
                    warrant_id,
                    command.route.listing_id,
                    preview.next_revision_number,
                    preview.current_revision_id,
                    command.request_id,
                    material,
                    preview.binding,
                    preview.kid_revision_id,
                    preview.kid_document_sha256,
                    preview.product_class,
                    source,
                    command.reviewed_at,
                    command.review_reference,
                    clock,
                    actor_id,
                )
            await self.repository.add(result)
            await self.session.commit()
            return result
        except IntegrityError as error:
            await self.session.rollback()
            raise listing_unit_error("LISTING_UNIT_REVISION_CONFLICT", 409) from error
        except Exception:
            await self.session.rollback()
            raise


class ListingUnitEvidenceReader:
    """One caller-owned snapshot, never source fetching or latest-good substitution."""

    def __init__(
        self, session: AsyncSession, *, registry: tuple[ListingUnitRuleSet, ...] | None = None
    ) -> None:
        self.session = session
        self.registry = SUPPORTED_RULE_SETS if registry is None else registry
        self.repository = ListingUnitEvidenceRepository(session)

    async def current(
        self,
        *,
        workspace_id: UUID,
        warrant_id: UUID,
        route: ListingUnitRoute,
        known_at: datetime,
        event_at: datetime | None = None,
    ) -> ListingUnitRead:
        if not aware(known_at):
            raise listing_unit_error("LISTING_UNIT_CLOCK_INVALID")
        event = event_at or known_at
        _clock(event, known_at)
        _route(route)
        try:
            with self.session.no_autoflush:
                await require_warrant(
                    self.session, workspace_id=workspace_id, warrant_id=warrant_id
                )
                row = await self.repository.latest(
                    workspace_id, warrant_id, route.listing_id, known_at
                )
                return await self._read(
                    row,
                    workspace_id=workspace_id,
                    warrant_id=warrant_id,
                    route=route,
                    known_at=known_at,
                    event_at=event,
                )
        except DBAPIError as error:
            raise listing_unit_error("LISTING_UNIT_READ_UNAVAILABLE", 503) from error

    async def _read(
        self,
        row: ListingUnitEvidenceModel | None,
        *,
        workspace_id: UUID,
        warrant_id: UUID,
        route: ListingUnitRoute,
        known_at: datetime,
        event_at: datetime,
    ) -> ListingUnitRead:
        reasons: list[str] = []
        revision = None
        current_kid = None
        if row is None:
            reasons.append("LISTING_UNIT_EVIDENCE_MISSING")
            if not self.registry:
                reasons.append("LISTING_UNIT_RULE_ORIGINALS_UNQUALIFIED")
        else:
            try:
                revision = to_revision(row)
                spec = _validated_source(revision.source, known_at=known_at, registry=self.registry)
                _clock(revision.reviewed_at, revision.recorded_at)
                _clock(revision.source.qualified_at, revision.recorded_at)
                if spec.effective_from is not None and event_at < spec.effective_from:
                    reasons.append("LISTING_UNIT_RULE_NOT_EFFECTIVE_AT_EVENT")
                elif spec.effective_from is None and event_at < spec.observed_at:
                    # This is an engineering qualification boundary, never an
                    # invented legal publication/effective clock or BUY history.
                    reasons.append("LISTING_UNIT_RULE_NOT_OBSERVED_AT_EVENT")
                binding, current_kid, product_class = await _current_context(
                    self.session,
                    workspace_id=workspace_id,
                    warrant_id=warrant_id,
                    route=route,
                    known_at=known_at,
                )
                if binding != revision.binding or revision.product_class != product_class:
                    reasons.append("LISTING_UNIT_CURRENT_BINDING_MISMATCH")
                original_kid = await self.session.get(
                    ProductReviewDocumentModel, revision.kid_revision_id
                )
                if (
                    original_kid is None
                    or original_kid.workspace_id != workspace_id
                    or original_kid.warrant_id != warrant_id
                    or original_kid.terms_id != revision.binding.product.current_terms_id
                    or original_kid.kind != "KID"
                    or original_kid.document_sha256 != revision.kid_document_sha256
                    or original_kid.recorded_at > revision.recorded_at
                    or _kid_class(original_kid) != revision.product_class
                    or revision.source.pretrade.isin != revision.binding.product.isin
                    or revision.source.pretrade.venue_mic != route.venue_mic
                    or revision.source.pretrade.currency != route.currency
                    or spec.product_class != revision.product_class
                ):
                    reasons.append("LISTING_UNIT_ORIGINAL_BINDING_INVALID")
            except ApplicationError as error:
                reasons.append(error.code)
            except (ValueError, TypeError, AttributeError):
                reasons.append("LISTING_UNIT_EVIDENCE_CORRUPT")
        unique = tuple(dict.fromkeys(reasons))
        rule_sources = (
            tuple(
                ListingUnitRuleSource(
                    item.role, item.source_reference, item.document_sha256, item.retrieved_at
                )
                for item in revision.source.rule_originals
            )
            if revision
            else ()
        )
        result = ListingUnitRead(
            workspace_id,
            warrant_id,
            route,
            known_at,
            event_at,
            "MISSING" if row is None else "UNSUITABLE" if unique else "AVAILABLE",
            unique,
            row.id if row else None,
            row.revision_number if row else 0,
            row.recorded_at if row else None,
            revision.binding if revision else None,
            "CURRENCY_PER_WARRANT" if revision else None,
            revision.binding.route.currency if revision else None,
            revision.product_class if revision else None,
            revision.kid_revision_id if revision else None,
            revision.kid_document_sha256 if revision else None,
            current_kid.id if current_kid else None,
            revision.source.rule_set_version if revision else None,
            rule_sources,
            revision.source.pretrade.file_name if revision else None,
            revision.source.pretrade.file_sha256 if revision else None,
            revision.source.pretrade.row_sha256 if revision else None,
            revision.source.pretrade.observed_at if revision else None,
            "",
        )
        material = {
            key: value
            for key, value in asdict(result).items()
            if key not in {"fingerprint", "known_at", "event_at"}
        }
        from dataclasses import replace

        return replace(result, fingerprint=fingerprint(material))
