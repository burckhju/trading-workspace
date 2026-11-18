"""Synthetic Product facts in a uniquely named disposable database; passive reader only."""

import hashlib
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session
from tests.unit.backend.features.market_data.test_session_evidence_service import SqlSession
from tests.unit.backend.providers.product_review_document_fixture import synthetic_kid_pdf

from app.features.market.domain.enums import (
    DataOrigin,
    LifecycleStatus,
    QualityStatus,
    UnderlyingType,
)
from app.features.market.persistence.models import UnderlyingModel, WorkspaceModel
from app.features.product.domain.models import OptionDirection, WarrantLifecycle
from app.features.product.domain.price_scale_evidence import ProductPriceScaleBinding
from app.features.product.domain.review_evidence import ExtractedProductFacts
from app.features.product.persistence.models import WarrantModel, WarrantTermsVersionModel
from app.features.product.persistence.review_evidence import ProductReviewDocumentModel
from app.features.product.service.review_evidence import BINDING, FACTS, ProductReviewEvidenceReader
from app.providers.product_review_documents import PARSER_VERSION

WORKSPACE, WARRANT, ISSUER, UNDERLYING, TERMS = (UUID(int=value) for value in range(901, 906))
ISIN, UNDERLYING_ISIN = "DE000TEST124", "US00SYNTH011"
NOW = datetime(2026, 11, 18, 16, tzinfo=UTC)
DOCUMENT = synthetic_kid_pdf(
    f"Synthetisches Basisinformationsblatt Optionsschein {ISIN} Basiswert {UNDERLYING_ISIN} "
    "Währung des Produkts: EUR Kursnotierung: Stücknotiz Referenzstelle: New York Stock Exchange "
    "Bewertungstag Der Ausübungstag bzw. der 15.01.2027"
)


@pytest.fixture(autouse=True)
def no_provider_access(monkeypatch):
    asynchronous = AsyncMock(side_effect=AssertionError("Evidence read cannot fetch sources"))
    synchronous = Mock(side_effect=AssertionError("Evidence read cannot fetch sources"))
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", asynchronous)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", synchronous)
    yield
    asynchronous.assert_not_awaited()
    synchronous.assert_not_called()


@pytest.fixture
def context(tmp_path):
    # All writes are confined to this synthetic, disposable SQLite file.
    engine = create_engine(f"sqlite:///{tmp_path}/synthetic-product-review-{uuid4()}.db")
    for model in (
        WorkspaceModel,
        UnderlyingModel,
        WarrantModel,
        WarrantTermsVersionModel,
        ProductReviewDocumentModel,
    ):
        model.__table__.create(engine)
    # Match the existing PostgreSQL partial uniqueness in the disposable SQLite fixture.
    with engine.begin() as connection:
        connection.execute(text("DROP INDEX uq_warrant_terms_versions_open"))
        connection.execute(
            text(
                "CREATE UNIQUE INDEX uq_warrant_terms_versions_open ON warrant_terms_versions "
                "(warrant_id) WHERE effective_to IS NULL"
            )
        )
    with Session(engine, expire_on_commit=False) as sql:
        underlying = UnderlyingModel(
            id=UNDERLYING,
            workspace_id=WORKSPACE,
            type=UnderlyingType.STOCK,
            name="Synthetic underlying",
            isin=UNDERLYING_ISIN,
            lifecycle_status=LifecycleStatus.ACTIVE,
            quality_status=QualityStatus.VERIFIED,
            version=1,
            created_at=NOW - timedelta(days=60),
            updated_at=NOW,
            data_origin=DataOrigin.MANUAL,
        )
        warrant = WarrantModel(
            id=WARRANT,
            workspace_id=WORKSPACE,
            issuer_id=ISSUER,
            underlying_id=UNDERLYING,
            display_name="Synthetic warrant",
            isin=ISIN,
            wkn="TEST12",
            lifecycle_status=WarrantLifecycle.ACTIVE,
            created_at=NOW - timedelta(days=60),
            updated_at=NOW,
            version=1,
        )
        terms = WarrantTermsVersionModel(
            id=TERMS,
            warrant_id=WARRANT,
            version_no=1,
            effective_from=NOW - timedelta(days=60),
            effective_to=None,
            option_direction=OptionDirection.CALL,
            strike=100,
            ratio="0.1",
            maturity_date=date(2027, 1, 15),
            strike_currency_code="USD",
            created_at=NOW - timedelta(days=60),
        )
        sql.add_all(
            [
                WorkspaceModel(id=WORKSPACE, name="Synthetic review only", created_at=NOW),
                underlying,
                warrant,
                terms,
            ]
        )
        sql.commit()
        adapter = SqlSession(sql)
        yield SimpleNamespace(
            sql=sql,
            session=adapter,
            reader=ProductReviewEvidenceReader(adapter),
            warrant=warrant,
            underlying=underlying,
            terms=terms,
            rows=[],
        )
    engine.dispose()


def revision(context, *, revision_number=1, recorded_at=NOW, **facts_overrides):
    facts = ExtractedProductFacts(
        **{
            "isin": ISIN,
            "underlying_isin": UNDERLYING_ISIN,
            "currency": "EUR",
            "unit": "CURRENCY_PER_WARRANT",
            "reference_venue_mic": "XNYS",
            "maturity_on": date(2027, 1, 15),
            **facts_overrides,
        }
    )
    binding = ProductPriceScaleBinding(WARRANT, ISIN, ISSUER, UNDERLYING, TERMS)
    row = ProductReviewDocumentModel(
        id=uuid4(),
        workspace_id=WORKSPACE,
        warrant_id=WARRANT,
        terms_id=TERMS,
        kind="KID",
        revision_number=revision_number,
        recorded_at=recorded_at,
        retrieved_at=recorded_at - timedelta(minutes=1),
        source_reference=f"https://kid.bnpparibas.com/{ISIN}_DE.pdf",
        document_sha256=hashlib.sha256(DOCUMENT).hexdigest(),
        document=DOCUMENT,
        binding=BINDING.dump_python(binding, mode="json"),
        facts=FACTS.dump_python(facts, mode="json"),
        parser_version=PARSER_VERSION,
    )
    context.sql.add(row)
    context.sql.commit()
    context.rows.append(row)
    return row


async def current(context, **overrides):
    return await context.reader.current_for_review(
        **{
            "workspace_id": WORKSPACE,
            "warrant_id": WARRANT,
            "known_at": NOW,
            **overrides,
        }
    )


@pytest.mark.asyncio
async def test_current_unit_can_be_used_only_with_the_explicit_history_assumption(context):
    row = revision(context)
    report = await current(context)
    assert report.status == "AVAILABLE" and report.reasons == ()
    assert report.quality == "CURRENT_UNIT_HISTORY_ASSUMED"
    assert report.verification == "ORIGINAL_DOCUMENT_EXTRACTION_NOT_HISTORICAL_VERIFICATION"
    assert report.currency == "EUR" and report.unit == "CURRENCY_PER_WARRANT"
    assert report.revision_id == row.id and report.binding.warrant_id == WARRANT
    assert report.source_document_sha256 == hashlib.sha256(DOCUMENT).hexdigest()
    assert report.reference_venue_mic == "XNYS"
    assert report.maturity_on == date(2027, 1, 15)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scope", [{}, {"workspace_id": UUID(int=999)}, {"warrant_id": UUID(int=998)}]
)
async def test_absent_or_foreign_document_does_not_reuse_another_products_facts(context, scope):
    if scope:
        revision(context)
    report = await current(context, **scope)
    assert report.status == "MISSING"
    assert report.reasons == ("PRODUCT_REVIEW_DOCUMENT_MISSING",)
    assert report.revision_id is None and report.currency is None and report.binding is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"currency": None}, "PRODUCT_REVIEW_CURRENCY_UNPROVEN"),
        ({"unit": None}, "PRODUCT_REVIEW_UNIT_UNPROVEN"),
        ({"unit": "PERCENT_OF_NOMINAL"}, "PRODUCT_REVIEW_UNIT_UNPROVEN"),
        (
            {"underlying_isin": None, "issues": ("PRODUCT_DOCUMENT_UNDERLYING_AMBIGUOUS",)},
            "PRODUCT_DOCUMENT_UNDERLYING_AMBIGUOUS",
        ),
    ],
)
async def test_partial_facts_do_not_silently_fill_missing_price_scale_information(
    context, changes, reason
):
    revision(context, **changes)
    report = await current(context)
    assert report.status == "MISSING" and reason in report.reasons


@pytest.mark.asyncio
async def test_reference_market_remains_independently_readable_when_currency_and_unit_are_missing(
    context,
):
    row = revision(context, currency=None, unit=None)
    report = await current(context)
    assert report.status == "MISSING"
    stored, binding, facts, reasons = await context.reader.reference_market_for_review(
        workspace_id=WORKSPACE,
        warrant_id=WARRANT,
        known_at=NOW,
    )
    assert stored.id == row.id and binding.warrant_id == WARRANT
    assert facts.reference_venue_mic == "XNYS" and reasons == ()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "problem", ["PRODUCT_DOCUMENT_CURRENT_TERMS_MISMATCH", "PRODUCT_DOCUMENT_UNDERLYING_MISMATCH"]
)
async def test_known_contradictions_block_instead_of_downgrading_to_a_usable_assumption(
    context, problem
):
    revision(context, issues=(problem, problem))
    report = await current(context)
    assert report.status == "UNSUITABLE" and report.reasons.count(problem) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("corrupt", ["document", "binding", "facts"])
async def test_corrupt_latest_revision_does_not_fall_back_to_an_older_good_document(
    context, corrupt
):
    first = revision(context)
    latest = revision(context, revision_number=2, recorded_at=NOW + timedelta(minutes=1))
    if corrupt == "document":
        latest.document = b"Synthetic tampered original"
    elif corrupt == "binding":
        latest.binding = {**latest.binding, "warrant_id": "invalid-uuid"}
    else:
        latest.facts = {**latest.facts, "maturity_on": "not-a-date"}
    context.sql.commit()
    earlier = await current(context)
    assert earlier.status == "AVAILABLE" and earlier.revision_id == first.id
    current_report = await current(context, known_at=NOW + timedelta(minutes=1))
    assert current_report.status == "UNSUITABLE" and current_report.revision_id == latest.id
    assert current_report.reasons == ("PRODUCT_REVIEW_DOCUMENT_CORRUPT",)
    assert current_report.currency is None and current_report.binding is None


@pytest.mark.asyncio
async def test_changed_product_binding_invalidates_current_document_without_hiding_its_identity(
    context,
):
    row = revision(context)
    context.warrant.isin = "US00SYNTH029"
    context.sql.commit()
    report = await current(context)
    assert report.status == "UNSUITABLE"
    assert "PRODUCT_REVIEW_BINDING_CHANGED" in report.reasons
    assert report.revision_id == row.id


@pytest.mark.asyncio
async def test_underlying_identity_change_is_a_separate_hard_conflict(context):
    revision(context)
    context.underlying.isin = "US00SYNTH029"
    context.sql.commit()
    report = await current(context)
    assert report.status == "UNSUITABLE"
    assert "PRODUCT_DOCUMENT_UNDERLYING_MISMATCH" in report.reasons


@pytest.mark.asyncio
async def test_maturity_alone_does_not_invent_last_trading_day_or_personal_exit_listing(context):
    revision(context)
    report = await context.reader.deadline_for_review(
        workspace_id=WORKSPACE,
        warrant_id=WARRANT,
        known_at=NOW,
    )
    assert report.status == "UNSUITABLE"
    assert report.maturity_on == date(2027, 1, 15)
    assert report.last_trading_on is None and report.exit_listing_id is None
    assert "PRODUCT_EXIT_LISTING_MISSING" in report.reasons
    assert "PRODUCT_LAST_TRADING_DAY_UNVERIFIED" in report.reasons


@pytest.mark.asyncio
async def test_reader_never_fetches_flushes_commits_or_rewrites_pending_owner_facts(context):
    revision(context)
    context.warrant.display_name = "Uncommitted synthetic draft"
    flushes = []
    event.listen(context.sql, "before_flush", lambda *_args: flushes.append(True))
    report = await current(context)
    assert report.status == "AVAILABLE"
    assert context.warrant in context.sql.dirty and flushes == []
    context.session.flush.assert_not_awaited()
    context.session.commit.assert_not_awaited()
    context.session.add.assert_not_called()
    assert all(
        str(statement).lstrip().startswith("SELECT") for statement in context.session.statements
    )


@pytest.mark.asyncio
async def test_requires_an_original_aware_knowledge_clock_before_reading(context):
    with pytest.raises(ValueError, match="PRODUCT_DOCUMENT_CLOCK_INVALID"):
        await current(context, known_at=NOW.replace(tzinfo=None))
    assert context.session.statements == []


@pytest.mark.asyncio
@pytest.mark.parametrize("mismatch", ["facts_isin", "terms_id", "bound_product"])
async def test_persisted_identity_must_match_both_the_binding_and_requested_product(
    context, mismatch
):
    row = revision(context)
    if mismatch == "facts_isin":
        row.facts = {**row.facts, "isin": "US00SYNTH029"}
    else:
        foreign_warrant, foreign_terms = UUID(int=990), UUID(int=991)
        if mismatch == "bound_product":
            context.sql.add(
                WarrantModel(
                    id=foreign_warrant,
                    workspace_id=WORKSPACE,
                    issuer_id=ISSUER,
                    underlying_id=UNDERLYING,
                    display_name="Other synthetic warrant",
                    isin="US00SYNTH029",
                    wkn="SYNTH2",
                    lifecycle_status=WarrantLifecycle.ACTIVE,
                    created_at=NOW - timedelta(days=60),
                    updated_at=NOW,
                    version=1,
                )
            )
        context.sql.add(
            WarrantTermsVersionModel(
                id=foreign_terms,
                warrant_id=foreign_warrant if mismatch == "bound_product" else WARRANT,
                version_no=2,
                effective_from=NOW - timedelta(days=90),
                effective_to=None if mismatch == "bound_product" else NOW - timedelta(days=60),
                option_direction=OptionDirection.CALL,
                strike=100,
                ratio="0.1",
                maturity_date=date(2027, 1, 15),
                strike_currency_code="USD",
                created_at=NOW - timedelta(days=90),
            )
        )
        row.terms_id = foreign_terms
        if mismatch == "bound_product":
            row.binding = BINDING.dump_python(
                ProductPriceScaleBinding(
                    foreign_warrant,
                    "US00SYNTH029",
                    ISSUER,
                    UNDERLYING,
                    foreign_terms,
                ),
                mode="json",
            )
            row.facts = {**row.facts, "isin": "US00SYNTH029"}
    context.sql.commit()
    result = await current(context)
    assert result.status == "UNSUITABLE"
    assert result.reasons == ("PRODUCT_REVIEW_DOCUMENT_CORRUPT",)
    assert result.currency is None and result.binding is None
