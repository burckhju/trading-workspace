"""Explicit original-document imports and passive product-scale evidence reads."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.exceptions import ApplicationError
from app.features.product.domain.price_scale_evidence import (
    ProductPriceScaleBinding,
    ProductPriceScaleCurrent,
    ProductPriceScaleImportCommand,
    ProductPriceScaleManifest,
    ProductPriceScaleRevision,
    ProductPriceScaleSource,
    aware,
)
from app.features.product.persistence.models import (
    WarrantModel,
    WarrantTermsVersionModel,
)
from app.features.product.persistence.price_scale_evidence import (
    SqlAlchemyProductPriceScaleEvidenceRepository,
    fingerprint,
    request_fingerprint,
    validate_originals,
)


def price_scale_error(code: str, message: str, status: int = 422) -> ApplicationError:
    return ApplicationError(code=code, message=message, status_code=status)


def validate_import(
    command: ProductPriceScaleImportCommand, now: datetime
) -> tuple[ProductPriceScaleManifest, bytes]:
    try:
        return validate_originals(command, now)
    except ValueError as error:
        raise price_scale_error(
            "PRODUCT_PRICE_SCALE_INVALID",
            "Das Produktmaßstab-Paket ist ungültig; Originalbelege, Hashes und Zeitangaben prüfen.",
        ) from error


async def require_warrant(
    session: AsyncSession, *, workspace_id: UUID, warrant_id: UUID, lock: bool = False
) -> None:
    query = select(WarrantModel.id).where(
        WarrantModel.workspace_id == workspace_id, WarrantModel.id == warrant_id
    )
    if await session.scalar(query.with_for_update() if lock else query) is None:
        raise price_scale_error(
            "PRODUCT_PRICE_SCALE_SCOPE_NOT_FOUND",
            "Produkt in diesem Workspace nicht gefunden.",
            404,
        )


async def binding_matches(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    binding: ProductPriceScaleBinding,
    known_at: datetime,
) -> bool:
    # The current head is an invalidation guard, not proof of historical validity.
    # Its recorded effective_from is never substituted for the source's interval.
    terms = (
        await session.scalars(
            select(WarrantTermsVersionModel.id)
            .join(WarrantModel, WarrantModel.id == WarrantTermsVersionModel.warrant_id)
            .where(
                WarrantModel.workspace_id == workspace_id,
                WarrantModel.id == binding.warrant_id,
                WarrantModel.isin == binding.isin,
                WarrantModel.issuer_id == binding.issuer_id,
                WarrantModel.underlying_id == binding.underlying_id,
                WarrantTermsVersionModel.effective_to.is_(None),
                WarrantTermsVersionModel.created_at <= known_at,
                WarrantTermsVersionModel.effective_from <= known_at,
            )
            .limit(2)
        )
    ).all()
    return list(terms) == [binding.current_terms_id]


class ProductPriceScaleEvidenceImportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = SqlAlchemyProductPriceScaleEvidenceRepository(session)

    async def record(
        self,
        *,
        workspace_id: UUID,
        warrant_id: UUID,
        actor_id: UUID,
        command: ProductPriceScaleImportCommand,
        now: datetime | None = None,
    ) -> ProductPriceScaleRevision:
        clock = now or datetime.now(UTC)
        manifest, _ = validate_import(command, clock)
        material = request_fingerprint(command, workspace_id, actor_id)
        try:
            await self._session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            with self._session.no_autoflush:
                await require_warrant(
                    self._session,
                    workspace_id=workspace_id,
                    warrant_id=warrant_id,
                    lock=True,
                )
                clock = now or datetime.now(UTC)
                if manifest.binding.warrant_id != warrant_id:
                    raise price_scale_error(
                        "PRODUCT_PRICE_SCALE_BINDING_MISMATCH",
                        "Originalbeleg gehört zu einem anderen Produkt.",
                    )
                replay = await self._repository.find_request(workspace_id, command.request_id)
                if replay is not None:
                    if replay.request_fingerprint != material or replay.recorded_at > clock:
                        raise price_scale_error(
                            "PRODUCT_PRICE_SCALE_REQUEST_CONFLICT",
                            "Die Vorgangskennung gehört zu einem anderen Importpaket.",
                            409,
                        )
                    await self._session.rollback()
                    return replay
                clock = now or datetime.now(UTC)
                current = await self._repository.latest(
                    workspace_id, warrant_id, datetime.max.replace(tzinfo=UTC)
                )
                if command.supersedes_revision_id != (current.id if current else None) or (
                    current is not None and current.recorded_at > clock
                ):
                    raise price_scale_error(
                        "PRODUCT_PRICE_SCALE_REVISION_CONFLICT",
                        "Produktmaßstab wurde geändert; aktuellen Vorgänger erneut lesen.",
                        409,
                    )
                if not await binding_matches(
                    self._session,
                    workspace_id=workspace_id,
                    binding=manifest.binding,
                    known_at=clock,
                ):
                    raise price_scale_error(
                        "PRODUCT_PRICE_SCALE_BINDING_MISMATCH",
                        "Produktidentität oder aktueller Bedingungsstand passen nicht zum Beleg.",
                    )
                source = ProductPriceScaleSource(
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
                revision = ProductPriceScaleRevision(
                    id=uuid4(),
                    workspace_id=workspace_id,
                    warrant_id=warrant_id,
                    revision_number=current.revision_number + 1 if current else 1,
                    supersedes_revision_id=command.supersedes_revision_id,
                    request_id=command.request_id,
                    request_fingerprint=material,
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
            raise price_scale_error(
                "PRODUCT_PRICE_SCALE_REVISION_CONFLICT",
                "Produktmaßstab gleichzeitig geändert oder widersprüchlich.",
                409,
            ) from error
        except Exception:
            await self._session.rollback()
            raise


class ProductPriceScaleEvidenceReader:
    """Caller owns one snapshot; no flush, commit, source fetch or older-good fallback."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = SqlAlchemyProductPriceScaleEvidenceRepository(session)

    async def current(
        self, *, workspace_id: UUID, warrant_id: UUID, known_at: datetime
    ) -> ProductPriceScaleCurrent:
        if not aware(known_at):
            raise price_scale_error(
                "PRODUCT_PRICE_SCALE_INVALID", "Wissenszeit benötigt eine Zeitzone."
            )
        try:
            with self._session.no_autoflush:
                await require_warrant(
                    self._session, workspace_id=workspace_id, warrant_id=warrant_id
                )
                revision = await self._repository.latest(workspace_id, warrant_id, known_at)
                reasons: list[str] = []
                if revision is None:
                    reasons.append("PRODUCT_PRICE_SCALE_EVIDENCE_MISSING")
                else:
                    if not await binding_matches(
                        self._session,
                        workspace_id=workspace_id,
                        binding=revision.manifest.binding,
                        known_at=known_at,
                    ):
                        reasons.append("PRODUCT_PRICE_SCALE_BINDING_CHANGED")
                    if revision.manifest.status != "UNCHANGED_ORIGINAL":
                        reasons.append(f"PRODUCT_PRICE_SCALE_{revision.manifest.status}")
                manifest = revision.manifest if revision else None
                source = revision.source if revision else None
                material = {
                    "workspace_id": workspace_id,
                    "warrant_id": warrant_id,
                    "known_at": known_at,
                    "revision_id": revision.id if revision else None,
                    "supersedes_revision_id": (
                        revision.supersedes_revision_id if revision else None
                    ),
                    "revision_number": revision.revision_number if revision else None,
                    "recorded_at": revision.recorded_at if revision else None,
                    "request_fingerprint": (revision.request_fingerprint if revision else None),
                    "manifest": asdict(manifest) if manifest else None,
                    "source": asdict(source) if source else None,
                    "reasons": reasons,
                }
                return ProductPriceScaleCurrent(
                    workspace_id=workspace_id,
                    warrant_id=warrant_id,
                    known_at=known_at,
                    revision_id=revision.id if revision else None,
                    supersedes_revision_id=(revision.supersedes_revision_id if revision else None),
                    revision_number=revision.revision_number if revision else None,
                    manifest=manifest,
                    binding=manifest.binding if manifest else None,
                    source=source,
                    recorded_at=revision.recorded_at if revision else None,
                    read_at=datetime.now(UTC),
                    status=(
                        "MISSING" if revision is None else "UNSUITABLE" if reasons else "AVAILABLE"
                    ),
                    reasons=tuple(reasons),
                    fingerprint=fingerprint(material),
                )
        except (ValueError, DBAPIError) as error:
            raise price_scale_error(
                "PRODUCT_PRICE_SCALE_READ_UNAVAILABLE",
                "Produktmaßstab konnte nicht sicher gelesen werden; dies ist keine Beleglücke.",
                503,
            ) from error

    async def revision(
        self, *, workspace_id: UUID, warrant_id: UUID, revision_id: UUID
    ) -> ProductPriceScaleRevision:
        try:
            with self._session.no_autoflush:
                await require_warrant(
                    self._session, workspace_id=workspace_id, warrant_id=warrant_id
                )
                revision = await self._repository.get(workspace_id, warrant_id, revision_id)
                if revision is None:
                    raise price_scale_error(
                        "PRODUCT_PRICE_SCALE_SCOPE_NOT_FOUND",
                        "Produktmaßstab-Revision nicht gefunden.",
                        404,
                    )
                return revision
        except (ValueError, DBAPIError) as error:
            raise price_scale_error(
                "PRODUCT_PRICE_SCALE_READ_UNAVAILABLE",
                "Originalbeleg konnte nicht sicher gelesen werden; dies ist keine Beleglücke.",
                503,
            ) from error


class ProductPriceScaleEvidenceReadService:
    """Public current reads use a server clock and a separate read-only snapshot."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    @asynccontextmanager
    async def _snapshot(self) -> AsyncIterator[AsyncSession]:
        async with AsyncSession(self._engine, expire_on_commit=False, autoflush=False) as session:
            try:
                await session.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                )
                await session.execute(text("SET LOCAL statement_timeout = '10000ms'"))
                yield session
            except (DBAPIError, ValueError) as error:
                raise price_scale_error(
                    "PRODUCT_PRICE_SCALE_READ_UNAVAILABLE",
                    "Produktmaßstab konnte nicht sicher gelesen werden; dies ist keine Beleglücke.",
                    503,
                ) from error
            finally:
                await session.rollback()

    async def current(self, *, workspace_id: UUID, warrant_id: UUID) -> ProductPriceScaleCurrent:
        clock = datetime.now(UTC)
        async with self._snapshot() as session:
            return await ProductPriceScaleEvidenceReader(session).current(
                workspace_id=workspace_id, warrant_id=warrant_id, known_at=clock
            )

    async def revision(
        self, *, workspace_id: UUID, warrant_id: UUID, revision_id: UUID
    ) -> ProductPriceScaleRevision:
        async with self._snapshot() as session:
            return await ProductPriceScaleEvidenceReader(session).revision(
                workspace_id=workspace_id,
                warrant_id=warrant_id,
                revision_id=revision_id,
            )
