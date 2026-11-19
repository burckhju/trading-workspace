"""Product-owned deadline composition over synthetic originals and disposable SQL.

Only this fixture's invented documents, choices and owner records are written.
The actual component readers run; no prices, costs, execution records or provider
access are available. PostgreSQL isolation and append-only guards have separate
integration coverage.
"""

import hashlib
from dataclasses import replace
from datetime import date, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import event
from tests.unit.backend.features.product.test_product_review_evidence_reader import (
    ISIN,
    ISSUER,
    NOW,
    TERMS,
    UNDERLYING,
    UNDERLYING_ISIN,
    WARRANT,
    WORKSPACE,
)
from tests.unit.backend.features.product.test_product_review_evidence_reader import (
    context as product_owner_fixture,
)
from tests.unit.backend.providers.product_review_document_fixture import synthetic_kid_pdf

from app.core.exceptions import ApplicationError
from app.features.market.persistence.models import CurrencyModel, IssuerModel, TradingVenueModel
from app.features.product.domain.deadline_listing_terms import PARSER_VERSION, VERIFICATION
from app.features.product.domain.models import WarrantLifecycle
from app.features.product.domain.price_scale_evidence import ProductPriceScaleBinding
from app.features.product.persistence.deadline_choice import ProductDeadlineExitChoiceModel
from app.features.product.persistence.models import WarrantListingModel, WarrantTermsVersionModel
from app.features.product.persistence.review_evidence import ProductReviewDocumentModel
from app.features.product.service import review_evidence as module
from app.features.product.service.deadline_listing_terms import FACTS as LISTING_FACTS
from app.features.product.service.review_evidence import BINDING, record_original_kid
from app.providers.product_listing_terms import parse_original_listing_terms

VENUE, LISTING, ACTOR = (UUID(int=value) for value in range(950, 953))
MATURITY = date(2027, 1, 15)
LAST_TRADING = date(2027, 1, 14)
KID_URL = f"https://kid.bnpparibas.com/{ISIN}_DE.pdf"
LISTING_URL = (
    "https://www.boerse-stuttgart.de/de-de/produkte/hebelprodukte/"
    "optionsscheine/stuttgart/test12/"
)
product_owner_context = product_owner_fixture


@pytest.fixture(autouse=True)
def no_external_requests(monkeypatch):
    asynchronous = AsyncMock(side_effect=AssertionError("Deadline evidence cannot fetch providers"))
    synchronous = Mock(side_effect=AssertionError("Deadline evidence cannot fetch providers"))
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", asynchronous)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", synchronous)
    yield
    asynchronous.assert_not_awaited()
    synchronous.assert_not_called()


@pytest.fixture
def deadline_context(product_owner_context):
    context = product_owner_context
    for model in (
        IssuerModel,
        CurrencyModel,
        TradingVenueModel,
        WarrantListingModel,
    ):
        model.__table__.create(context.sql.get_bind())
    clock = NOW - timedelta(days=2)
    context.venue = TradingVenueModel(
        id=VENUE,
        mic="XSTU",
        name="Synthetic Stuttgart",
        country_code="DE",
        timezone="Europe/Berlin",
        is_active=True,
        reference_version="synthetic-v1",
        version=1,
        created_at=clock,
        updated_at=clock,
    )
    context.listing = WarrantListingModel(
        id=LISTING,
        workspace_id=WORKSPACE,
        warrant_id=WARRANT,
        trading_venue_id=VENUE,
        symbol=None,
        quotation_currency_code="EUR",
        lifecycle_status=WarrantLifecycle.ACTIVE,
        version=1,
        created_at=clock,
        updated_at=clock,
    )
    context.sql.add_all(
        [
            IssuerModel(
                id=ISSUER,
                legal_name="BNP Paribas",
                display_name="Synthetic issuer",
                is_active=True,
                version=1,
                created_at=clock,
                updated_at=clock,
            ),
            CurrencyModel(
                code="EUR",
                name="Synthetic EUR",
                minor_unit=2,
                is_active=True,
                reference_version="synthetic-v1",
                created_at=clock,
                updated_at=clock,
            ),
            context.venue,
            context.listing,
        ]
    )
    context.sql.commit()
    context.choices = []
    return context


async def kid(context, *, recorded_at=None, maturity=True, price_fields=True, underlying=True):
    recorded_at = recorded_at or NOW - timedelta(hours=3)
    document = synthetic_kid_pdf(
        f"Synthetisches Basisinformationsblatt Optionsschein {ISIN} "
        + (f"Basiswert {UNDERLYING_ISIN} " if underlying else "")
        + ("Währung des Produkts: EUR Kursnotierung: Stücknotiz " if price_fields else "")
        + ("Bewertungstag Der Ausübungstag bzw. der 15.01.2027" if maturity else "")
    )
    identifier = await record_original_kid(
        context.session,
        workspace_id=WORKSPACE,
        warrant_id=WARRANT,
        source_reference=KID_URL,
        document=document,
        retrieved_at=recorded_at,
        now=recorded_at,
    )
    row = context.sql.get(ProductReviewDocumentModel, identifier)
    context.rows.append(row)
    context.sql.commit()
    return row


def listing_terms(context, *, revision_number=1, recorded_at=None, withdrawn=False):
    recorded_at = recorded_at or NOW - timedelta(hours=2)
    document = (
        "<html><head><title>Synthetic TEST12 - Börse Stuttgart (XSTU)</title>"
        f'<link rel="canonical" href="{LISTING_URL}"></head><body>'
        f"<section><h1>Synthetic warrant</h1>WKN TEST12 ISIN {ISIN}</section>"
        f'<div id="MasterDataBlock-synthetic">WKN TEST12 ISIN {ISIN}'
        "<table><tr><td>Letzter Börsenhandelstag</td><td>14.01.2027</td></tr></table>"
        "</div></body></html>"
    ).encode()
    facts = parse_original_listing_terms(document, expected_isin=ISIN, expected_wkn="TEST12")
    binding = ProductPriceScaleBinding(WARRANT, ISIN, ISSUER, UNDERLYING, TERMS)
    row = ProductReviewDocumentModel(
        id=uuid4(),
        workspace_id=WORKSPACE,
        warrant_id=WARRANT,
        terms_id=TERMS,
        kind="LISTING_TERMS",
        revision_number=revision_number,
        recorded_at=recorded_at,
        retrieved_at=recorded_at,
        source_reference=LISTING_URL,
        document_sha256=hashlib.sha256(document).hexdigest(),
        document=document,
        binding=BINDING.dump_python(binding, mode="json"),
        facts={
            "original_facts": LISTING_FACTS.dump_python(facts, mode="json"),
            "withdrawn": withdrawn,
            "withdrawal_reason": "Synthetic withdrawal" if withdrawn else None,
            "verification": VERIFICATION,
            "receipt_time_basis": "FILE_RECEIVED_AT",
            "recorded_by": str(ACTOR),
        },
        parser_version=PARSER_VERSION,
    )
    context.sql.add(row)
    context.sql.commit()
    context.rows.append(row)
    return row


def exit_choice(context, *, recorded_at=None, withdrawn=False, venue=None, listing=None):
    venue, listing = venue or context.venue, listing or context.listing
    previous = context.choices[-1] if context.choices else None
    row = ProductDeadlineExitChoiceModel(
        id=uuid4(),
        workspace_id=WORKSPACE,
        warrant_id=WARRANT,
        previous_revision_id=previous.id if previous else None,
        revision_number=previous.revision_number + 1 if previous else 1,
        terms_id=TERMS,
        listing_id=None if withdrawn else listing.id,
        listing_version=None if withdrawn else listing.version,
        trading_venue_id=None if withdrawn else venue.id,
        venue_mic=None if withdrawn else venue.mic,
        venue_version=None if withdrawn else venue.version,
        quotation_currency_code=None if withdrawn else listing.quotation_currency_code,
        recorded_at=recorded_at or NOW - timedelta(hours=1),
        recorded_by=ACTOR,
    )
    context.sql.add(row)
    context.sql.commit()
    context.choices.append(row)
    return row


async def ready(context, *, omit=None, **kid_options):
    original = None if omit == "kid" else await kid(context, **kid_options)
    listing = None if omit == "listing" else listing_terms(context)
    choice = None if omit == "choice" else exit_choice(context)
    return original, listing, choice


async def read(context, **overrides):
    return await context.reader.deadline_for_review(
        **{"workspace_id": WORKSPACE, "warrant_id": WARRANT, "known_at": NOW, **overrides}
    )


@pytest.mark.asyncio
async def test_dates_compose_from_three_bound_owners_without_price_unit_or_underlying(
    deadline_context,
):
    context = deadline_context
    original, listing, choice = await ready(context, price_fields=False, underlying=False)
    price_evidence = await context.reader.current_for_review(
        workspace_id=WORKSPACE, warrant_id=WARRANT, known_at=NOW
    )
    assert price_evidence.status == "MISSING"
    assert "PRODUCT_REVIEW_UNIT_UNPROVEN" in price_evidence.reasons
    report = await read(context)
    assert report.status == "AVAILABLE" and report.reasons == ()
    assert report.maturity_on == MATURITY and report.last_trading_on == LAST_TRADING
    assert report.exit_listing_id == LISTING and report.exit_venue_mic == "XSTU"
    assert report.recorded_at == choice.recorded_at
    assert report.product_document_revision_id == original.id
    assert report.listing_terms_revision_id == listing.id
    assert report.exit_choice_revision_id == choice.id
    assert report.source_reference == LISTING_URL
    assert report.product_document_source_reference == KID_URL
    assert report.verification.endswith("NOT_INDEPENDENT_VERIFICATION")
    assert (
        await read(context, known_at=NOW + timedelta(minutes=1))
    ).fingerprint == report.fingerprint


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "omit,reason",
    [
        ("kid", "PRODUCT_REVIEW_DOCUMENT_MISSING"),
        ("listing", "PRODUCT_LAST_TRADING_DAY_EVIDENCE_MISSING"),
        ("choice", "PRODUCT_EXIT_LISTING_MISSING"),
    ],
)
async def test_missing_component_cannot_be_replaced_by_dates_or_existing_listing(
    deadline_context, omit, reason
):
    await ready(deadline_context, omit=omit)
    report = await read(deadline_context)
    assert report.status == "MISSING" and reason in report.reasons
    if omit == "choice":
        assert report.exit_listing_id is None and report.exit_venue_mic is None
    if omit == "listing":
        assert report.last_trading_on is None


@pytest.mark.asyncio
@pytest.mark.parametrize("component", ["kid", "listing", "choice"])
async def test_later_unsuitable_component_does_not_rewrite_history_or_fall_back(
    deadline_context, component
):
    context = deadline_context
    original, listing, choice = await ready(context)
    before = await read(context)
    later = NOW + timedelta(hours=1)
    if component == "kid":
        changed = await kid(context, recorded_at=later, maturity=False)
        revision_field = "product_document_revision_id"
        reason = "PRODUCT_MATURITY_EVIDENCE_MISSING"
    elif component == "listing":
        changed = listing_terms(context, revision_number=2, recorded_at=later, withdrawn=True)
        revision_field = "listing_terms_revision_id"
        reason = "PRODUCT_LISTING_TERMS_WITHDRAWN"
    else:
        changed = exit_choice(context, recorded_at=later, withdrawn=True)
        revision_field = "exit_choice_revision_id"
        reason = "PRODUCT_EXIT_LISTING_WITHDRAWN"
    historical = await read(context)
    assert historical == before
    after = await read(context, known_at=later + timedelta(minutes=1))
    assert after.status != "AVAILABLE" and reason in after.reasons
    assert getattr(after, revision_field) == changed.id
    assert after.fingerprint != before.fingerprint and after.recorded_at == later
    assert context.sql.get(ProductReviewDocumentModel, original.id) is original
    assert context.sql.get(ProductReviewDocumentModel, listing.id) is listing
    assert context.sql.get(ProductDeadlineExitChoiceModel, choice.id) is choice


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "owner,reason",
    [
        ("listing", "PRODUCT_EXIT_LISTING_CHANGED"),
        ("venue", "PRODUCT_EXIT_VENUE_CHANGED"),
        ("product", "PRODUCT_REVIEW_BINDING_CHANGED"),
        ("terms", "PRODUCT_DEADLINE_TERMS_MISMATCH"),
    ],
)
async def test_relevant_owner_change_invalidates_composed_dates(deadline_context, owner, reason):
    context = deadline_context
    await ready(context)
    before = await read(context)
    if owner == "listing":
        context.listing.version += 1
    elif owner == "venue":
        context.venue.mic = "XBER"
    elif owner == "product":
        context.warrant.isin = "DE000TEST132"
    else:
        context.terms.effective_to = NOW - timedelta(minutes=1)
        context.sql.flush()
        context.current_terms = WarrantTermsVersionModel(
            id=uuid4(),
            warrant_id=WARRANT,
            version_no=2,
            effective_from=NOW - timedelta(minutes=1),
            effective_to=None,
            option_direction=context.terms.option_direction,
            strike=context.terms.strike,
            ratio=context.terms.ratio,
            maturity_date=context.terms.maturity_date,
            strike_currency_code=context.terms.strike_currency_code,
            created_at=NOW - timedelta(minutes=1),
        )
        context.sql.add(context.current_terms)
    context.sql.commit()
    report = await read(context)
    assert report.status == "UNSUITABLE" and reason in report.reasons
    assert report.fingerprint != before.fingerprint
    assert report.product_document_revision_id == before.product_document_revision_id


@pytest.mark.asyncio
async def test_explicit_other_exit_venue_cannot_reuse_stuttgart_listing_date(deadline_context):
    context = deadline_context
    await ready(context, omit="choice")
    other_venue = TradingVenueModel(
        id=uuid4(),
        mic="XBER",
        name="Synthetic alternative",
        country_code="DE",
        timezone="Europe/Berlin",
        is_active=True,
        reference_version="synthetic-v1",
        version=1,
        created_at=NOW - timedelta(days=2),
        updated_at=NOW - timedelta(days=2),
    )
    other_listing = WarrantListingModel(
        id=uuid4(),
        workspace_id=WORKSPACE,
        warrant_id=WARRANT,
        trading_venue_id=other_venue.id,
        symbol=None,
        quotation_currency_code="EUR",
        lifecycle_status=WarrantLifecycle.ACTIVE,
        version=1,
        created_at=NOW - timedelta(days=2),
        updated_at=NOW - timedelta(days=2),
    )
    context.sql.add_all([other_venue, other_listing])
    context.sql.commit()
    exit_choice(context, venue=other_venue, listing=other_listing)
    report = await read(context)
    assert report.status == "UNSUITABLE"
    assert report.reasons == ("PRODUCT_LAST_TRADING_DAY_EXIT_VENUE_MISMATCH",)
    assert report.exit_listing_id == other_listing.id


@pytest.mark.asyncio
@pytest.mark.parametrize("scope", [{"workspace_id": UUID(int=999)}, {"warrant_id": UUID(int=998)}])
async def test_actual_owner_lookup_refuses_another_workspace_or_product(deadline_context, scope):
    await ready(deadline_context)
    with pytest.raises(ApplicationError) as error:
        await read(deadline_context, **scope)
    assert error.value.code == "PRODUCT_EXIT_WARRANT_NOT_FOUND"


@pytest.mark.asyncio
@pytest.mark.parametrize("component", ["choice", "listing"])
@pytest.mark.parametrize(
    "change",
    [
        {"workspace_id": UUID(int=999)},
        {"warrant_id": UUID(int=998)},
        {"known_at": NOW + timedelta(minutes=1)},
        {"recorded_at": NOW + timedelta(minutes=1)},
    ],
)
async def test_component_scope_or_future_clock_cannot_be_composed(
    deadline_context, monkeypatch, component, change
):
    context = deadline_context
    await ready(context)
    name = (
        "read_product_deadline_exit_choice"
        if component == "choice"
        else "read_product_listing_terms"
    )
    original_reader = getattr(module, name)

    async def mismatched(*args, **kwargs):
        return replace(await original_reader(*args, **kwargs), **change)

    monkeypatch.setattr(module, name, mismatched)
    report = await read(context)
    assert report.status == "UNSUITABLE"
    assert "PRODUCT_DEADLINE_COMPONENT_SCOPE_MISMATCH" in report.reasons


@pytest.mark.asyncio
async def test_composition_has_no_flush_commit_or_fetch_even_with_pending_owner_edit(
    deadline_context,
):
    context = deadline_context
    await ready(context)
    context.session.add.reset_mock()
    context.session.flush.reset_mock()
    context.session.commit.reset_mock()
    context.warrant.display_name = "Synthetic pending display edit"
    start = len(context.session.statements)
    forbidden_flush = Mock(side_effect=AssertionError("Passive read must not flush pending edits"))
    event.listen(context.sql, "before_flush", forbidden_flush)
    try:
        report = await read(context)
    finally:
        event.remove(context.sql, "before_flush", forbidden_flush)
    assert report.status == "AVAILABLE"
    assert context.warrant in context.sql.dirty
    forbidden_flush.assert_not_called()
    context.session.add.assert_not_called()
    context.session.flush.assert_not_awaited()
    context.session.commit.assert_not_awaited()
    assert all(statement.is_select for statement in context.session.statements[start:])
    assert len(context.rows) == 2
