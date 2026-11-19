"""Explicit exit-listing choice, server-generated revisions and passive reuse."""

from dataclasses import asdict
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.core.exceptions import ApplicationError
from app.features.market.persistence.models import CurrencyModel, TradingVenueModel
from app.features.product.domain.deadline_choice import (
    ProductDeadlineChoiceReport,
    ProductDeadlineExitChoice,
    ProductDeadlineListingOption,
)
from app.features.product.domain.models import WarrantLifecycle
from app.features.product.persistence.deadline_choice import ProductDeadlineExitChoiceModel
from app.features.product.persistence.models import (
    WarrantListingModel,
    WarrantModel,
    WarrantTermsVersionModel,
)
from app.features.product.persistence.price_scale_evidence import fingerprint


def choice_error(code: str, message: str, status: int = 422) -> ApplicationError:
    return ApplicationError(code=code, message=message, status_code=status)


async def _warrant(
    session: AsyncSession, workspace_id: UUID, warrant_id: UUID, *, lock: bool = False
) -> WarrantModel:
    query = select(WarrantModel).where(
        WarrantModel.workspace_id == workspace_id, WarrantModel.id == warrant_id
    )
    warrant = await session.scalar(query.with_for_update() if lock else query)
    if warrant is None:
        raise choice_error("PRODUCT_EXIT_WARRANT_NOT_FOUND", "Produkt nicht gefunden.", 404)
    return warrant


async def _current_terms(session: AsyncSession, warrant_id: UUID) -> WarrantTermsVersionModel:
    terms = await session.scalar(
        select(WarrantTermsVersionModel).where(
            WarrantTermsVersionModel.warrant_id == warrant_id,
            WarrantTermsVersionModel.effective_to.is_(None),
        )
    )
    if terms is None:
        raise choice_error(
            "PRODUCT_EXIT_TERMS_MISSING", "Aktueller Produktbedingungsstand fehlt.", 409
        )
    return terms


async def _latest(
    session: AsyncSession, workspace_id: UUID, warrant_id: UUID, known_at: datetime
) -> ProductDeadlineExitChoiceModel | None:
    row: ProductDeadlineExitChoiceModel | None = await session.scalar(
        select(ProductDeadlineExitChoiceModel)
        .where(
            ProductDeadlineExitChoiceModel.workspace_id == workspace_id,
            ProductDeadlineExitChoiceModel.warrant_id == warrant_id,
            ProductDeadlineExitChoiceModel.recorded_at <= known_at,
        )
        .order_by(ProductDeadlineExitChoiceModel.revision_number.desc())
        .limit(1)
    )
    return row


async def read_product_deadline_exit_choice(
    session: AsyncSession, *, workspace_id: UUID, warrant_id: UUID, known_at: datetime
) -> ProductDeadlineExitChoice:
    """Reuse only the explicit choice, invalidating relevant owner changes.

    No first/primary/quoted listing, venue from a source document or calendar can
    substitute for a personal choice. A later term/listing/MIC change is exposed
    as an exception; a display-name-only venue revision does not require repeat
    confirmation of an unchanged choice.
    """
    if known_at.utcoffset() is None:
        raise ValueError("Product exit choice requires an aware knowledge clock")
    with session.no_autoflush:
        warrant = await _warrant(session, workspace_id, warrant_id)
        terms = await _current_terms(session, warrant_id)
        row = await _latest(session, workspace_id, warrant_id, known_at)
        reasons: list[str] = []
        if warrant.lifecycle_status != WarrantLifecycle.ACTIVE:
            reasons.append("PRODUCT_EXIT_WARRANT_INACTIVE")
        if terms.created_at > known_at or terms.effective_from > known_at:
            reasons.append("PRODUCT_EXIT_TERMS_AFTER_KNOWLEDGE")
        if row is None:
            reasons.append("PRODUCT_EXIT_LISTING_MISSING")
        elif row.terms_id != terms.id:
            reasons.append("PRODUCT_EXIT_TERMS_CHANGED")
        if row is not None:
            if row.listing_id is None:
                reasons.append("PRODUCT_EXIT_LISTING_WITHDRAWN")
            else:
                listing = await session.get(WarrantListingModel, row.listing_id)
                venue = (
                    await session.get(TradingVenueModel, row.trading_venue_id)
                    if row.trading_venue_id is not None
                    else None
                )
                if (
                    listing is None
                    or listing.workspace_id != workspace_id
                    or listing.warrant_id != warrant_id
                    or listing.version != row.listing_version
                    or listing.trading_venue_id != row.trading_venue_id
                    or listing.quotation_currency_code != row.quotation_currency_code
                    or listing.lifecycle_status != WarrantLifecycle.ACTIVE
                    or listing.updated_at > known_at
                ):
                    reasons.append("PRODUCT_EXIT_LISTING_CHANGED")
                if (
                    venue is None
                    or venue.mic != row.venue_mic
                    or not venue.is_active
                    or venue.updated_at > known_at
                ):
                    reasons.append("PRODUCT_EXIT_VENUE_CHANGED")
        read = ProductDeadlineExitChoice(
            workspace_id=workspace_id,
            warrant_id=warrant_id,
            known_at=known_at,
            status="MISSING" if row is None else ("UNSUITABLE" if reasons else "AVAILABLE"),
            reasons=tuple(reasons),
            revision_id=row.id if row else None,
            revision_number=row.revision_number if row else 0,
            recorded_at=row.recorded_at if row else None,
            terms_id=row.terms_id if row else terms.id,
            current_terms_id=terms.id,
            exit_listing_id=row.listing_id if row else None,
            exit_listing_version=row.listing_version if row else None,
            trading_venue_id=row.trading_venue_id if row else None,
            exit_venue_mic=row.venue_mic if row else None,
            venue_version=row.venue_version if row else None,
            quotation_currency_code=row.quotation_currency_code if row else None,
            fingerprint="",
        )
        material = {
            key: value
            for key, value in asdict(read).items()
            if key not in {"known_at", "fingerprint"}
        }
        return ProductDeadlineExitChoice(**{**asdict(read), "fingerprint": fingerprint(material)})


async def _report(
    session: AsyncSession, workspace_id: UUID, warrant_id: UUID, now: datetime
) -> ProductDeadlineChoiceReport:
    choice = await read_product_deadline_exit_choice(
        session, workspace_id=workspace_id, warrant_id=warrant_id, known_at=now
    )
    rows = (
        await session.execute(
            select(WarrantListingModel, TradingVenueModel)
            .join(TradingVenueModel, TradingVenueModel.id == WarrantListingModel.trading_venue_id)
            .join(CurrencyModel, CurrencyModel.code == WarrantListingModel.quotation_currency_code)
            .where(
                WarrantListingModel.workspace_id == workspace_id,
                WarrantListingModel.warrant_id == warrant_id,
                WarrantListingModel.lifecycle_status == WarrantLifecycle.ACTIVE,
                TradingVenueModel.is_active.is_(True),
                CurrencyModel.is_active.is_(True),
            )
            .order_by(TradingVenueModel.mic, WarrantListingModel.id)
        )
    ).all()
    return ProductDeadlineChoiceReport(
        warrant_id=warrant_id,
        status=choice.status,
        reasons=choice.reasons,
        revision_number=choice.revision_number,
        selected_listing_id=choice.exit_listing_id,
        selected_venue_mic=choice.exit_venue_mic,
        terms_id=choice.current_terms_id,
        recorded_at=choice.recorded_at,
        available_listings=tuple(
            ProductDeadlineListingOption(
                listing.id,
                listing.version,
                venue.name,
                venue.mic,
                venue.version,
                listing.quotation_currency_code,
                listing.symbol,
            )
            for listing, venue in rows
        ),
    )


class ProductDeadlineChoiceReader:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def read(self, *, workspace_id: UUID, warrant_id: UUID) -> ProductDeadlineChoiceReport:
        async with AsyncSession(self._engine, expire_on_commit=False, autoflush=False) as session:
            try:
                await session.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                )
                await session.execute(text("SET LOCAL statement_timeout = '10000ms'"))
                return await _report(session, workspace_id, warrant_id, datetime.now(UTC))
            finally:
                await session.rollback()


class ProductDeadlineChoiceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def choose(
        self,
        *,
        workspace_id: UUID,
        warrant_id: UUID,
        actor_id: UUID,
        listing_id: UUID | None,
        expected_revision_number: int,
        expected_terms_id: UUID,
        expected_listing_version: int | None,
        expected_venue_version: int | None,
    ) -> ProductDeadlineChoiceReport:
        session = self._session
        try:
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            await session.execute(text("SET LOCAL statement_timeout = '10000ms'"))
            warrant = await _warrant(session, workspace_id, warrant_id, lock=True)
            terms = await _current_terms(session, warrant_id)
            now = datetime.now(UTC)
            if terms.id != expected_terms_id:
                raise choice_error(
                    "PRODUCT_EXIT_TERMS_CHANGED", "Produktbedingungen wurden geändert.", 409
                )
            listing = venue = None
            if listing_id is not None:
                listing = await session.scalar(
                    select(WarrantListingModel)
                    .where(
                        WarrantListingModel.id == listing_id,
                        WarrantListingModel.workspace_id == workspace_id,
                        WarrantListingModel.warrant_id == warrant_id,
                    )
                    .with_for_update()
                )
                venue = (
                    await session.scalar(
                        select(TradingVenueModel)
                        .where(TradingVenueModel.id == listing.trading_venue_id)
                        .with_for_update()
                    )
                    if listing is not None
                    else None
                )
                currency = (
                    await session.get(CurrencyModel, listing.quotation_currency_code)
                    if listing is not None
                    else None
                )
                if (
                    warrant.lifecycle_status != WarrantLifecycle.ACTIVE
                    or listing is None
                    or listing.lifecycle_status != WarrantLifecycle.ACTIVE
                    or venue is None
                    or not venue.is_active
                    or currency is None
                    or not currency.is_active
                ):
                    raise choice_error(
                        "PRODUCT_EXIT_LISTING_UNAVAILABLE",
                        "Nur ein bestehendes aktives Listing dieses Produkts kann gewählt werden.",
                    )
                if (
                    listing.version != expected_listing_version
                    or venue.version != expected_venue_version
                ):
                    raise choice_error(
                        "PRODUCT_EXIT_LISTING_CHANGED",
                        "Listing oder Handelsplatz wurde geändert.",
                        409,
                    )
            elif expected_listing_version is not None or expected_venue_version is not None:
                raise choice_error(
                    "PRODUCT_EXIT_CHOICE_INVALID", "Rücknahme benötigt keine Listingversion."
                )
            now = datetime.now(UTC)
            previous = await _latest(session, workspace_id, warrant_id, now)
            same = previous is not None and (
                previous.terms_id == terms.id
                and previous.listing_id == listing_id
                and previous.listing_version == (listing.version if listing else None)
                and previous.trading_venue_id == (venue.id if venue else None)
                and previous.venue_mic == (venue.mic if venue else None)
                and previous.quotation_currency_code
                == (listing.quotation_currency_code if listing else None)
            )
            if not same:
                if expected_revision_number != (previous.revision_number if previous else 0):
                    raise choice_error(
                        "PRODUCT_EXIT_CHOICE_CHANGED",
                        "Die gespeicherte Auswahl wurde geändert.",
                        409,
                    )
                if previous is None and listing_id is None:
                    # An already empty representation is an idempotent no-op,
                    # not a manufactured first withdrawal event.
                    report = await _report(session, workspace_id, warrant_id, now)
                    await session.rollback()
                    return report
                session.add(
                    ProductDeadlineExitChoiceModel(
                        id=uuid4(),
                        workspace_id=workspace_id,
                        warrant_id=warrant_id,
                        previous_revision_id=previous.id if previous else None,
                        revision_number=previous.revision_number + 1 if previous else 1,
                        terms_id=terms.id,
                        listing_id=listing_id,
                        listing_version=listing.version if listing else None,
                        trading_venue_id=venue.id if venue else None,
                        venue_mic=venue.mic if venue else None,
                        venue_version=venue.version if venue else None,
                        quotation_currency_code=(
                            listing.quotation_currency_code if listing else None
                        ),
                        recorded_at=now,
                        recorded_by=actor_id,
                    )
                )
                await session.flush()
            report = await _report(session, workspace_id, warrant_id, datetime.now(UTC))
            await session.commit()
            return report
        except Exception:
            await session.rollback()
            raise
