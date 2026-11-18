"""Explicit original-file imports and read-only, revision-bound listing-date evidence."""

import hashlib
from dataclasses import asdict
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import TypeAdapter
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.exceptions import ApplicationError
from app.features.product.domain.deadline_listing_terms import (
    PARSER_VERSION,
    VERIFICATION,
    OriginalListingTermsFacts,
    ProductListingTermsRead,
)
from app.features.product.domain.price_scale_evidence import ProductPriceScaleBinding, aware
from app.features.product.persistence.models import WarrantModel, WarrantTermsVersionModel
from app.features.product.persistence.price_scale_evidence import fingerprint
from app.features.product.persistence.review_evidence import ProductReviewDocumentModel
from app.features.product.service.price_scale_evidence import binding_matches, require_warrant
from app.providers.product_listing_terms import parse_original_listing_terms

FACTS = TypeAdapter(OriginalListingTermsFacts)
BINDING = TypeAdapter(ProductPriceScaleBinding)


def listing_terms_error(code: str, message: str, status: int = 422) -> ApplicationError:
    return ApplicationError(code=code, message=message, status_code=status)


async def _latest(
    session: AsyncSession, workspace_id: UUID, warrant_id: UUID, known_at: datetime
) -> ProductReviewDocumentModel | None:
    row: ProductReviewDocumentModel | None = await session.scalar(
        select(ProductReviewDocumentModel)
        .where(
            ProductReviewDocumentModel.workspace_id == workspace_id,
            ProductReviewDocumentModel.warrant_id == warrant_id,
            ProductReviewDocumentModel.kind == "LISTING_TERMS",
            ProductReviewDocumentModel.recorded_at <= known_at,
        )
        .order_by(ProductReviewDocumentModel.revision_number.desc())
        .limit(1)
    )
    return row


async def read_product_listing_terms(
    session: AsyncSession, *, workspace_id: UUID, warrant_id: UUID, known_at: datetime
) -> ProductListingTermsRead:
    """Check immutable original bytes, current Product identity and withdrawal.

    These supplied bytes are not proof of an authenticated live acquisition.
    Receipt clocks describe this import, never a source publication or market
    time. An unsuitable later revision never falls back to an earlier success.
    """
    if not aware(known_at):
        raise ValueError("PRODUCT_LISTING_TERMS_CLOCK_INVALID")
    with session.no_autoflush:
        await require_warrant(session, workspace_id=workspace_id, warrant_id=warrant_id)
        row = await _latest(session, workspace_id, warrant_id, known_at)
        reasons: list[str] = []
        facts = None
        binding = None
        if row is None:
            reasons.append("PRODUCT_LAST_TRADING_DAY_EVIDENCE_MISSING")
        else:
            try:
                binding = BINDING.validate_python(row.binding)
                facts = FACTS.validate_python(row.facts["original_facts"])
                parsed = parse_original_listing_terms(
                    row.document, expected_isin=binding.isin, expected_wkn=facts.wkn
                )
                if (
                    row.warrant_id != binding.warrant_id
                    or row.terms_id != binding.current_terms_id
                    or row.document_sha256 != hashlib.sha256(row.document).hexdigest()
                    or row.parser_version != PARSER_VERSION
                    or parsed != facts
                    or row.source_reference != parsed.source_reference
                    or not isinstance(row.facts["withdrawn"], bool)
                    or row.facts.get("verification") != VERIFICATION
                    or row.facts.get("receipt_time_basis") != "FILE_RECEIVED_AT"
                    or row.retrieved_at > row.recorded_at
                ):
                    raise ValueError("Original listing document integrity")
            except (ValueError, KeyError, TypeError):
                reasons.append("PRODUCT_LISTING_TERMS_CORRUPT")
                facts = None
            if binding is not None and not await binding_matches(
                session, workspace_id=workspace_id, binding=binding, known_at=known_at
            ):
                reasons.append("PRODUCT_LISTING_TERMS_BINDING_CHANGED")
            if facts is not None:
                warrant = await session.get(WarrantModel, warrant_id)
                if warrant is None or (warrant.wkn is not None and warrant.wkn != facts.wkn):
                    reasons.append("PRODUCT_LISTING_TERMS_WKN_CHANGED")
                reasons.extend(facts.issues)
                if row.facts.get("withdrawn") is True:
                    reasons.append("PRODUCT_LISTING_TERMS_WITHDRAWN")
        unique_reasons = tuple(dict.fromkeys(reasons))
        return ProductListingTermsRead(
            workspace_id=workspace_id,
            warrant_id=warrant_id,
            known_at=known_at,
            status="MISSING" if row is None else "UNSUITABLE" if unique_reasons else "AVAILABLE",
            reasons=unique_reasons,
            revision_id=row.id if row else None,
            revision_number=row.revision_number if row else 0,
            recorded_at=row.recorded_at if row else None,
            fingerprint=fingerprint(
                {
                    "revision_id": row.id if row else None,
                    "document_sha256": row.document_sha256 if row else None,
                    "facts": asdict(facts) if facts else None,
                    "binding": asdict(binding) if binding else None,
                    "reasons": unique_reasons,
                }
            ),
            terms_id=binding.current_terms_id if binding else None,
            last_trading_on=facts.last_trading_on if facts else None,
            venue_mic=facts.venue_mic if facts else None,
            source_reference=row.source_reference if row else None,
            document_sha256=row.document_sha256 if row else None,
        )


class ProductListingTermsReader:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def read(self, *, workspace_id: UUID, warrant_id: UUID) -> ProductListingTermsRead:
        async with AsyncSession(self._engine, expire_on_commit=False, autoflush=False) as session:
            try:
                await session.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                )
                await session.execute(text("SET LOCAL statement_timeout = '10000ms'"))
                return await read_product_listing_terms(
                    session,
                    workspace_id=workspace_id,
                    warrant_id=warrant_id,
                    known_at=datetime.now(UTC),
                )
            finally:
                await session.rollback()


class ProductListingTermsImportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self, *, workspace_id: UUID, warrant_id: UUID, actor_id: UUID, document: bytes
    ) -> ProductListingTermsRead:
        session = self._session
        try:
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            await session.execute(text("SET LOCAL statement_timeout = '10000ms'"))
            await require_warrant(
                session, workspace_id=workspace_id, warrant_id=warrant_id, lock=True
            )
            warrant = await session.get(WarrantModel, warrant_id)
            terms = await session.scalar(
                select(WarrantTermsVersionModel).where(
                    WarrantTermsVersionModel.warrant_id == warrant_id,
                    WarrantTermsVersionModel.effective_to.is_(None),
                )
            )
            if warrant is None or warrant.isin is None or terms is None:
                raise listing_terms_error(
                    "PRODUCT_LISTING_TERMS_BINDING_MISSING",
                    "Produktidentität oder Bedingungen fehlen.",
                )
            try:
                facts = parse_original_listing_terms(
                    document, expected_isin=warrant.isin, expected_wkn=warrant.wkn
                )
            except ValueError as error:
                raise listing_terms_error(
                    "PRODUCT_LISTING_TERMS_ORIGINAL_INVALID",
                    "Originaldatei lässt sich dem exakten Stuttgart-Produkt nicht zuordnen.",
                ) from error
            now = datetime.now(UTC)
            previous = await _latest(
                session, workspace_id, warrant_id, datetime.max.replace(tzinfo=UTC)
            )
            if previous is not None and previous.recorded_at > now:
                raise listing_terms_error(
                    "PRODUCT_LISTING_TERMS_CLOCK_INVALID", "Zeitkonflikt.", 409
                )
            binding = BINDING.dump_python(
                ProductPriceScaleBinding(
                    warrant_id, warrant.isin, warrant.issuer_id, warrant.underlying_id, terms.id
                ),
                mode="json",
            )
            payload = {
                "original_facts": FACTS.dump_python(facts, mode="json"),
                "verification": VERIFICATION,
                "receipt_time_basis": "FILE_RECEIVED_AT",
                "withdrawn": False,
                "withdrawal_reason": None,
                "recorded_by": str(actor_id),
            }
            digest = hashlib.sha256(document).hexdigest()
            if not (
                previous is not None
                and previous.document_sha256 == digest
                and previous.binding == binding
                and previous.facts.get("original_facts") == payload["original_facts"]
                and previous.facts.get("withdrawn") is False
                and previous.parser_version == PARSER_VERSION
            ):
                session.add(
                    ProductReviewDocumentModel(
                        id=uuid4(),
                        workspace_id=workspace_id,
                        warrant_id=warrant_id,
                        terms_id=terms.id,
                        kind="LISTING_TERMS",
                        revision_number=previous.revision_number + 1 if previous else 1,
                        recorded_at=now,
                        retrieved_at=now,
                        source_reference=facts.source_reference,
                        document_sha256=digest,
                        document=document,
                        binding=binding,
                        facts=payload,
                        parser_version=PARSER_VERSION,
                    )
                )
                await session.flush()
            result = await read_product_listing_terms(
                session,
                workspace_id=workspace_id,
                warrant_id=warrant_id,
                known_at=datetime.now(UTC),
            )
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise

    async def withdraw(
        self,
        *,
        workspace_id: UUID,
        warrant_id: UUID,
        actor_id: UUID,
        expected_revision_number: int,
        reason: str,
    ) -> ProductListingTermsRead:
        session = self._session
        try:
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            await session.execute(text("SET LOCAL statement_timeout = '10000ms'"))
            await require_warrant(
                session, workspace_id=workspace_id, warrant_id=warrant_id, lock=True
            )
            now = datetime.now(UTC)
            previous = await _latest(
                session, workspace_id, warrant_id, datetime.max.replace(tzinfo=UTC)
            )
            if previous is None or previous.recorded_at > now:
                raise listing_terms_error(
                    "PRODUCT_LISTING_TERMS_REVISION_MISSING", "Beleg fehlt.", 409
                )
            if previous.facts.get("withdrawn") is not True:
                if previous.revision_number != expected_revision_number:
                    raise listing_terms_error(
                        "PRODUCT_LISTING_TERMS_REVISION_CHANGED",
                        "Originalbeleg wurde geändert.",
                        409,
                    )
                session.add(
                    ProductReviewDocumentModel(
                        id=uuid4(),
                        workspace_id=workspace_id,
                        warrant_id=warrant_id,
                        terms_id=previous.terms_id,
                        kind="LISTING_TERMS",
                        revision_number=previous.revision_number + 1,
                        recorded_at=now,
                        retrieved_at=previous.retrieved_at,
                        source_reference=previous.source_reference,
                        document_sha256=previous.document_sha256,
                        document=previous.document,
                        binding=previous.binding,
                        facts={
                            **previous.facts,
                            "withdrawn": True,
                            "withdrawal_reason": reason,
                            "recorded_by": str(actor_id),
                        },
                        parser_version=previous.parser_version,
                    )
                )
                await session.flush()
            result = await read_product_listing_terms(
                session,
                workspace_id=workspace_id,
                warrant_id=warrant_id,
                known_at=datetime.now(UTC),
            )
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise
