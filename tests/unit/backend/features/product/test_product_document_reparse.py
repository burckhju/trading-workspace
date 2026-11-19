"""Synthetic original-date roles and local parser upgrades, with no provider access."""

import hashlib
from copy import deepcopy
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from tests.unit.backend.features.product.test_product_deadline_evidence import (
    deadline_context as original_deadline_context,
)
from tests.unit.backend.features.product.test_product_deadline_evidence import (
    product_owner_context as original_product_owner_context,
)
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
from tests.unit.backend.providers.product_review_document_fixture import (
    synthetic_kid_pdf,
)

from app.features.product.domain.price_scale_evidence import ProductPriceScaleBinding
from app.features.product.persistence.models import WarrantTermsVersionModel
from app.features.product.persistence.review_evidence import (
    ProductReviewAcquisitionModel,
    ProductReviewDocumentModel,
)
from app.features.product.service import review_acquisition as acquisition
from app.features.product.service.review_evidence import (
    BINDING,
    ProductReviewEvidenceReader,
    record_original_kid,
    reparse_saved_original_kid,
)
from app.providers.product_review_documents import PARSER_VERSION

product_owner_context = original_product_owner_context
END, PAYMENT = date(2031, 5, 16), date(2031, 5, 23)
SOURCE = f"https://kid.bnpparibas.com/{ISIN}_DE.pdf"
TRADE, POSITION = UUID(int=1201), UUID(int=1202)


@pytest.fixture(autouse=True)
def no_external_requests(monkeypatch):
    client = httpx.AsyncClient

    def no_http(_request):
        raise AssertionError("Synthetic readiness tests must not make HTTP requests")

    def isolated_client(**kwargs):
        return client(**kwargs, trust_env=False, transport=httpx.MockTransport(no_http))

    asynchronous = AsyncMock(side_effect=AssertionError("No live provider access"))
    synchronous = Mock(side_effect=AssertionError("No live provider access"))
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", asynchronous)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", synchronous)
    monkeypatch.setattr(acquisition.httpx, "AsyncClient", isolated_client)
    yield
    asynchronous.assert_not_awaited()
    synchronous.assert_not_called()


@pytest.fixture
def context(product_owner_context, monkeypatch):
    context = original_deadline_context.__wrapped__(product_owner_context)
    ProductReviewAcquisitionModel.__table__.create(context.sql.get_bind())
    context.terms.maturity_date = PAYMENT
    context.sql.commit()

    def stage(row):
        # Retain ORM instances so this SQLite fixture preserves aware datetime objects.
        # Actual PostgreSQL timestamps, locking and immutable history have a separate test.
        context.rows.append(row)
        context.sql.add(row)

    context.session.add.side_effect = stage

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW

    monkeypatch.setattr(acquisition, "datetime", Clock)
    monkeypatch.setattr(
        acquisition,
        "OpenPositionReader",
        lambda _session: SimpleNamespace(
            read=AsyncMock(return_value=SimpleNamespace(position_id=POSITION, warrant_id=WARRANT))
        ),
    )
    context.readiness = acquisition.ProductReviewReadiness(
        SimpleNamespace(session_context=lambda: context.session)
    )
    return context


def document(*, end=END, payment=PAYMENT, underlying=UNDERLYING_ISIN):
    return synthetic_kid_pdf(
        f"Synthetisches Basisinformationsblatt Optionsschein {ISIN} Basiswert {underlying} "
        "Währung des Produkts: EUR Kursnotierung: Stücknotiz "
        "Referenzstelle: New York Stock Exchange "
        + (f"Bewertungstag Der Ausübungstag bzw. der {end:%d.%m.%Y} " if end else "")
        + (f"Fälligkeitstag {payment:%d.%m.%Y}" if payment else "")
    )


def legacy(context):
    original = document()
    row = ProductReviewDocumentModel(
        id=uuid4(),
        workspace_id=WORKSPACE,
        warrant_id=WARRANT,
        terms_id=TERMS,
        kind="KID",
        revision_number=1,
        recorded_at=NOW - timedelta(hours=2),
        retrieved_at=NOW - timedelta(hours=3),
        source_reference=SOURCE,
        document_sha256=hashlib.sha256(original).hexdigest(),
        document=original,
        binding=BINDING.dump_python(
            ProductPriceScaleBinding(WARRANT, ISIN, ISSUER, UNDERLYING, TERMS),
            mode="json",
        ),
        facts={
            "isin": ISIN,
            "underlying_isin": UNDERLYING_ISIN,
            "currency": "EUR",
            "unit": "CURRENCY_PER_WARRANT",
            "reference_venue_mic": "XNYS",
            "maturity_on": END.isoformat(),
            "last_trading_on": None,
            "last_trading_venue_mic": None,
            "issues": ["PRODUCT_DOCUMENT_CURRENT_TERMS_MISMATCH"],
        },
        parser_version="current-product-document-v1",
    )
    context.rows.append(row)
    context.sql.add(row)
    context.sql.commit()
    return row


def attempt(context, *, hours=24):
    row = ProductReviewAcquisitionModel(
        workspace_id=WORKSPACE,
        warrant_id=WARRANT,
        attempted_at=NOW - timedelta(minutes=10),
        next_attempt_at=NOW + timedelta(hours=hours),
        outcome="AVAILABLE" if hours == 24 else "REVIEW_READINESS_PARTIAL",
        problems=[] if hours == 24 else ["XSTU:REVIEW_CALENDAR_ACQUISITION_FAILED"],
    )
    context.rows.append(row)
    context.sql.add(row)
    context.sql.commit()
    return row


async def record(context, original):
    identifier = await record_original_kid(
        context.session,
        workspace_id=WORKSPACE,
        warrant_id=WARRANT,
        source_reference=SOURCE,
        document=original,
        retrieved_at=NOW - timedelta(minutes=1),
        now=NOW,
    )
    context.sql.commit()
    return context.sql.get(ProductReviewDocumentModel, identifier)


async def read(context):
    return await ProductReviewEvidenceReader(context.session).current_for_review(
        workspace_id=WORKSPACE, warrant_id=WARRANT, known_at=NOW
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(("terms_date", "role"), [(END, "PRODUCT_END"), (PAYMENT, "PAYMENT")])
async def test_exact_document_role_explains_existing_terms_without_rewriting_them(
    context, terms_date, role
):
    context.terms.maturity_date = terms_date
    context.sql.commit()
    row = await record(context, document())
    report = await read(context)
    assert report.status == "AVAILABLE" and report.reasons == ()
    assert row.facts["current_terms_date_role"] == role
    assert report.maturity_on == report.product_end_on == END
    assert report.payment_on == PAYMENT and report.current_terms_date_role == role
    assert context.terms.maturity_date == terms_date and context.terms.id == TERMS


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("terms_date", "underlying", "reason"),
    [
        (
            PAYMENT + timedelta(days=1),
            UNDERLYING_ISIN,
            "PRODUCT_DOCUMENT_CURRENT_TERMS_MISMATCH",
        ),
        (PAYMENT, "US00SYNTH029", "PRODUCT_DOCUMENT_UNDERLYING_MISMATCH"),
    ],
)
async def test_real_terms_and_underlying_contradictions_remain_hard(
    context, terms_date, underlying, reason
):
    context.terms.maturity_date = terms_date
    context.sql.commit()
    await record(context, document(underlying=underlying))
    report = await read(context)
    assert report.status == "UNSUITABLE" and reason in report.reasons


@pytest.mark.asyncio
async def test_payment_date_alone_never_becomes_the_deadline_product_end(context):
    await record(context, document(end=None))
    price = await read(context)
    assert price.status == "AVAILABLE" and price.payment_on == PAYMENT
    deadline = await context.reader.deadline_for_review(
        workspace_id=WORKSPACE, warrant_id=WARRANT, known_at=NOW
    )
    assert deadline.maturity_on is deadline.product_end_on is None
    assert "PRODUCT_MATURITY_EVIDENCE_MISSING" in deadline.reasons


@pytest.mark.asyncio
async def test_payment_before_end_cannot_qualify_a_matching_terms_role(context):
    context.terms.maturity_date = END - timedelta(days=1)
    context.sql.commit()
    row = await record(context, document(payment=context.terms.maturity_date))
    report = await read(context)
    assert row.facts["current_terms_date_role"] is None
    assert report.status == "UNSUITABLE"
    assert "PRODUCT_DOCUMENT_PAYMENT_BEFORE_END" in report.reasons


@pytest.mark.asyncio
async def test_local_parser_upgrade_appends_history_and_preserves_receipt_and_owner_facts(
    context,
):
    old = legacy(context)
    old_facts = deepcopy(old.facts)
    assert (await read(context)).status == "UNSUITABLE"
    identifier = await reparse_saved_original_kid(
        context.session, workspace_id=WORKSPACE, warrant_id=WARRANT, now=NOW
    )
    context.sql.commit()
    new = context.sql.get(ProductReviewDocumentModel, identifier)
    assert new.id != old.id and new.revision_number == 2
    assert new.parser_version == PARSER_VERSION
    assert new.document == old.document and new.document_sha256 == old.document_sha256
    assert new.source_reference == old.source_reference
    assert new.retrieved_at == old.retrieved_at and new.recorded_at == NOW
    assert new.binding == old.binding and new.terms_id == old.terms_id
    assert old.facts == old_facts and old.parser_version == "current-product-document-v1"
    assert (await read(context)).status == "AVAILABLE"
    assert context.terms.maturity_date == PAYMENT and context.terms.version_no == 1
    assert (
        await reparse_saved_original_kid(
            context.session,
            workspace_id=WORKSPACE,
            warrant_id=WARRANT,
            now=NOW + timedelta(minutes=1),
        )
        is None
    )
    assert context.sql.scalar(select(func.count()).select_from(ProductReviewDocumentModel)) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("fault", "reason"),
    [
        ("bytes", "PRODUCT_REVIEW_DOCUMENT_CORRUPT"),
        ("binding", "PRODUCT_REVIEW_DOCUMENT_CORRUPT"),
        ("source", "PRODUCT_DOCUMENT_SOURCE_BINDING_MISMATCH"),
        ("future_parser", "PRODUCT_DOCUMENT_PARSER_UNSUPPORTED"),
    ],
)
async def test_untrusted_originals_and_newer_parsers_cannot_be_locally_reinterpreted(
    context, fault, reason
):
    old = legacy(context)
    if fault == "bytes":
        old.document = b"%PDF-synthetic-corruption"
    elif fault == "binding":
        old.binding = {**old.binding, "current_terms_id": str(uuid4())}
    elif fault == "source":
        old.source_reference = "https://example.invalid/foreign-original.pdf"
    else:
        old.parser_version = "current-product-document-v999"
    context.sql.commit()
    with pytest.raises(ValueError, match=reason):
        await reparse_saved_original_kid(
            context.session, workspace_id=WORKSPACE, warrant_id=WARRANT, now=NOW
        )
    assert context.sql.scalar(select(func.count()).select_from(ProductReviewDocumentModel)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("hours", [1, 24])
async def test_active_readiness_upgrades_before_network_backoff_without_changing_it(
    context, monkeypatch, hours
):
    old = legacy(context)
    budget = attempt(context, hours=hours)
    before = (
        budget.attempted_at,
        budget.next_attempt_at,
        budget.outcome,
        list(budget.problems),
    )
    fetch = AsyncMock(side_effect=AssertionError("Backoff prohibits network work"))
    monkeypatch.setattr(acquisition, "fetch_original", fetch)
    await context.readiness.prepare_for_review(
        workspace_id=WORKSPACE, trade_id=TRADE, position_id=POSITION
    )
    fetch.assert_not_awaited()
    assert (
        budget.attempted_at,
        budget.next_attempt_at,
        budget.outcome,
        budget.problems,
    ) == before
    report = await read(context)
    assert report.status == "AVAILABLE" and report.revision_id != old.id
    assert context.session.commit.await_count == 1


@pytest.mark.asyncio
async def test_network_failure_cannot_undo_the_already_committed_local_upgrade(
    context, monkeypatch
):
    old = legacy(context)
    budget = attempt(context, hours=-1)

    async def failed_fetch(*_args):
        with Session(context.sql.get_bind()) as observer:
            assert (
                observer.scalar(select(func.count()).select_from(ProductReviewDocumentModel)) == 2
            )
        raise httpx.ReadTimeout("Synthetic offline provider")

    monkeypatch.setattr(acquisition, "fetch_original", failed_fetch)
    monkeypatch.setattr(acquisition, "acquire_nyse_calendar", AsyncMock())
    monkeypatch.setattr(acquisition, "acquire_xstu_day_calendar", AsyncMock())
    await context.readiness.prepare_for_review(
        workspace_id=WORKSPACE, trade_id=TRADE, position_id=POSITION
    )
    assert budget.outcome == "PRODUCT_DOCUMENT_ACQUISITION_FAILED"
    report = await read(context)
    new = context.sql.get(ProductReviewDocumentModel, report.revision_id)
    assert report.status == "AVAILABLE" and new.retrieved_at == old.retrieved_at


@pytest.mark.asyncio
async def test_changed_terms_require_normal_acquisition_instead_of_local_rebinding(
    context, monkeypatch
):
    old = legacy(context)
    context.terms.effective_to = NOW - timedelta(minutes=1)
    context.sql.flush()
    newer = WarrantTermsVersionModel(
        id=uuid4(),
        warrant_id=WARRANT,
        version_no=2,
        effective_from=NOW - timedelta(minutes=1),
        effective_to=None,
        option_direction=context.terms.option_direction,
        strike=context.terms.strike,
        ratio=context.terms.ratio,
        strike_currency_code=context.terms.strike_currency_code,
        maturity_date=PAYMENT,
        created_at=NOW - timedelta(minutes=1),
    )
    context.sql.add(newer)
    context.sql.commit()
    assert (
        await reparse_saved_original_kid(
            context.session, workspace_id=WORKSPACE, warrant_id=WARRANT, now=NOW
        )
        is None
    )
    assert "PRODUCT_REVIEW_BINDING_CHANGED" in (await read(context)).reasons
    attempt(context, hours=-1)
    fetch = AsyncMock(return_value=old.document)
    monkeypatch.setattr(acquisition, "fetch_original", fetch)
    monkeypatch.setattr(acquisition, "acquire_nyse_calendar", AsyncMock())
    monkeypatch.setattr(acquisition, "acquire_xstu_day_calendar", AsyncMock())
    await context.readiness.prepare_for_review(
        workspace_id=WORKSPACE, trade_id=TRADE, position_id=POSITION
    )
    fetch.assert_awaited_once()
    report = await read(context)
    assert report.status == "AVAILABLE" and report.binding.current_terms_id == newer.id
    assert old.terms_id == TERMS


@pytest.mark.asyncio
async def test_due_network_work_cannot_downgrade_a_future_parser(context, monkeypatch):
    old = legacy(context)
    old.parser_version = "current-product-document-v999"
    context.sql.commit()
    attempt(context, hours=-1)
    fetch = AsyncMock(side_effect=AssertionError("No downgrade through reacquisition"))
    monkeypatch.setattr(acquisition, "fetch_original", fetch)
    with pytest.raises(ValueError, match="PRODUCT_DOCUMENT_PARSER_UNSUPPORTED"):
        await context.readiness.prepare_for_review(
            workspace_id=WORKSPACE, trade_id=TRADE, position_id=POSITION
        )
    fetch.assert_not_awaited()
    assert (await read(context)).reasons == ("PRODUCT_DOCUMENT_PARSER_UNSUPPORTED",)
    # A concurrent/newer application can advance the head during an ordinary
    # network fetch, so the writer must also reject a direct late v2 result.
    with pytest.raises(ValueError, match="PRODUCT_DOCUMENT_PARSER_UNSUPPORTED"):
        await record(context, document())
    assert context.sql.scalar(select(func.count()).select_from(ProductReviewDocumentModel)) == 1
