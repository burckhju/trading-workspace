"""Synthetic original product evidence, real SQL reads and immutable source references."""

import base64
import hashlib
import json
from dataclasses import asdict, replace
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session
from tests.unit.backend.features.market_data.test_session_evidence_service import (
    SqlSession,
)

from app.core.exceptions import ApplicationError
from app.features.market.persistence.models import WorkspaceModel
from app.features.product.domain.models import OptionDirection, WarrantLifecycle
from app.features.product.domain.price_scale_evidence import (
    ProductPriceScaleImportCommand,
)
from app.features.product.persistence.models import (
    WarrantModel,
    WarrantTermsVersionModel,
)
from app.features.product.persistence.price_scale_evidence import (
    ProductPriceScaleEvidenceModel,
    SqlAlchemyProductPriceScaleEvidenceRepository,
)
from app.features.product.service.price_scale_evidence import (
    ProductPriceScaleEvidenceImportService,
    ProductPriceScaleEvidenceReader,
)

WORKSPACE = UUID(int=300)
ACTOR = UUID(int=301)
WARRANT = UUID(int=302)
ISSUER = UUID(int=303)
UNDERLYING = UUID(int=304)
TERMS = UUID(int=305)
NOW = datetime(2026, 11, 16, 10, tzinfo=UTC)
DOCUMENT = b"Synthetic original product unit document; currency per warrant, no adjustment.\n"


def digest(value):
    return hashlib.sha256(value).hexdigest()


def manifest(**overrides):
    value = {
        "schema_version": "product-price-scale-evidence-v1",
        "scale_id": "synthetic-original-warrant-units",
        "source_version": "synthetic-final-terms-v1",
        "binding": {
            "warrant_id": str(WARRANT),
            "isin": "DE000VH2LU21",
            "issuer_id": str(ISSUER),
            "underlying_id": str(UNDERLYING),
            "current_terms_id": str(TERMS),
        },
        "axis": "WARRANT",
        "currency": "EUR",
        "unit": "CURRENCY_PER_WARRANT",
        "valid_from": "2026-10-01T00:00:00+02:00",
        "valid_until": "2026-12-01T00:00:00+01:00",
        "status": "UNCHANGED_ORIGINAL",
        "source_publisher": "Synthetic Issuer",
        "source_reference": "https://example.invalid/synthetic/final-terms#price-unit",
        "source_document_sha256": digest(DOCUMENT),
        "source_published_on": "2026-09-30",
    }
    value.update(overrides)
    return value


def command(value=None, **overrides):
    original = json.dumps(manifest() if value is None else value, indent=2) + "\n"
    values = dict(
        request_id=uuid4(),
        supersedes_revision_id=None,
        manifest_json=original,
        manifest_sha256=digest(original.encode()),
        document_filename="synthetic-product-units.txt",
        document_media_type="text/plain",
        document_base64=base64.b64encode(DOCUMENT).decode(),
        document_sha256=digest(DOCUMENT),
        reviewed_at=NOW - timedelta(hours=1),
        review_reference="Synthetic review / original page 1",
        retrieved_at=NOW - timedelta(hours=2),
    )
    values.update(overrides)
    return ProductPriceScaleImportCommand(**values)


@pytest.fixture(autouse=True)
def no_provider_access(monkeypatch):
    asynchronous = AsyncMock(side_effect=AssertionError("Product evidence cannot fetch sources"))
    synchronous = Mock(side_effect=AssertionError("Product evidence cannot fetch sources"))
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", asynchronous)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", synchronous)
    yield
    asynchronous.assert_not_awaited()
    synchronous.assert_not_called()


@pytest.fixture
def context(tmp_path):
    # This uniquely named disposable SQLite file never touches a real installation.
    url = f"sqlite:///{tmp_path}/synthetic-product-scale-{uuid4()}.db"
    engine = create_engine(url)
    for model in (
        WorkspaceModel,
        WarrantModel,
        WarrantTermsVersionModel,
        ProductPriceScaleEvidenceModel,
    ):
        model.__table__.create(engine)
    # The existing Terms model declares its partial predicate only for PostgreSQL.
    # Reproduce that exact production uniqueness in this disposable SQLite fixture.
    with engine.begin() as connection:
        connection.execute(text("DROP INDEX uq_warrant_terms_versions_open"))
        connection.execute(
            text(
                "CREATE UNIQUE INDEX uq_warrant_terms_versions_open "
                "ON warrant_terms_versions (warrant_id) WHERE effective_to IS NULL"
            )
        )
    with Session(engine, expire_on_commit=False) as session:
        session.add_all(
            [
                WorkspaceModel(id=WORKSPACE, name="Synthetic scale evidence", created_at=NOW),
                WarrantModel(
                    id=WARRANT,
                    workspace_id=WORKSPACE,
                    issuer_id=ISSUER,
                    underlying_id=UNDERLYING,
                    display_name="Synthetic warrant",
                    isin="DE000VH2LU21",
                    wkn="VH2LU2",
                    lifecycle_status=WarrantLifecycle.ACTIVE,
                    created_at=NOW - timedelta(days=1),
                    updated_at=NOW,
                    version=1,
                ),
                WarrantTermsVersionModel(
                    id=TERMS,
                    warrant_id=WARRANT,
                    version_no=1,
                    effective_from=NOW - timedelta(days=1),
                    effective_to=None,
                    option_direction=OptionDirection.CALL,
                    strike=100,
                    ratio="0.1",
                    maturity_date=date(2027, 6, 1),
                    strike_currency_code="EUR",
                    created_at=NOW - timedelta(days=1),
                ),
            ]
        )
        session.commit()
        adapter = SqlSession(session)
        yield SimpleNamespace(
            sql=session,
            session=adapter,
            engine=engine,
            url=url,
            service=ProductPriceScaleEvidenceImportService(adapter),
            reader=ProductPriceScaleEvidenceReader(adapter),
        )
    engine.dispose()


async def record(context, value=None, **overrides):
    arguments = dict(
        workspace_id=WORKSPACE,
        warrant_id=WARRANT,
        actor_id=ACTOR,
        command=command() if value is None else value,
        now=NOW,
    )
    arguments.update(overrides)
    return await context.service.record(**arguments)


async def current(context, **overrides):
    arguments = dict(workspace_id=WORKSPACE, warrant_id=WARRANT, known_at=NOW)
    arguments.update(overrides)
    return await context.reader.current(**arguments)


def rows(context):
    return context.sql.scalars(
        select(ProductPriceScaleEvidenceModel).order_by(
            ProductPriceScaleEvidenceModel.revision_number
        )
    ).all()


@pytest.mark.asyncio
async def test_original_bytes_revision_clocks_and_source_interval_survive_restart(
    context,
):
    imported = command()
    first = await record(context, imported)
    result = await current(context)
    assert result.status == "AVAILABLE" and result.revision_id == first.id
    assert result.manifest.valid_from < context.sql.get(
        WarrantTermsVersionModel, TERMS
    ).created_at.replace(tzinfo=UTC)
    assert result.manifest.valid_until > NOW  # Explicit finite source claim, never a guarantee.
    assert result.verification == "MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION"
    assert result.source.reviewed_at == imported.reviewed_at
    assert result.source.retrieved_at == imported.retrieved_at
    assert result.recorded_at == NOW
    assert "document_base64" not in asdict(result) and "manifest_json" not in asdict(result)
    context.sql.close()
    context.engine.dispose()
    restarted = create_engine(context.url)
    with Session(restarted) as session:
        reader = ProductPriceScaleEvidenceReader(SqlSession(session))
        saved = await reader.current(workspace_id=WORKSPACE, warrant_id=WARRANT, known_at=NOW)
        original = await reader.revision(
            workspace_id=WORKSPACE, warrant_id=WARRANT, revision_id=first.id
        )
        assert saved.fingerprint == result.fingerprint
        assert original == first
        assert original.manifest_json == imported.manifest_json
        assert original.document_base64 == imported.document_base64
        assert base64.b64decode(original.document_base64) == DOCUMENT
    restarted.dispose()


@pytest.mark.asyncio
async def test_request_replay_does_not_append_and_actor_is_part_of_identity(context):
    imported = command()
    first = await record(context, imported)
    assert await record(context, imported, now=NOW + timedelta(days=2)) == first
    for changed in (
        replace(imported, review_reference="Different review"),
        replace(imported, supersedes_revision_id=first.id),
    ):
        with pytest.raises(ApplicationError) as captured:
            await record(context, changed)
        assert captured.value.code == "PRODUCT_PRICE_SCALE_REQUEST_CONFLICT"
    with pytest.raises(ApplicationError) as captured:
        await record(context, imported, actor_id=uuid4())
    assert captured.value.status_code == 409
    assert len(rows(context)) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["ADJUSTMENT_REQUIRED", "WITHDRAWN"])
async def test_new_revision_replaces_current_without_old_good_fallback(context, status):
    first = await record(context)
    second = await record(
        context,
        command(manifest(status=status), supersedes_revision_id=first.id),
        now=NOW + timedelta(seconds=1),
    )
    result = await current(context, known_at=NOW + timedelta(seconds=2))
    assert result.status == "UNSUITABLE" and result.revision_id == second.id
    assert result.reasons == (f"PRODUCT_PRICE_SCALE_{status}",)
    assert (
        await current(context)
    ).revision_id == first.id  # Knowledge cutoff, not a mutable product reconstruction.
    assert (
        await context.reader.revision(
            workspace_id=WORKSPACE, warrant_id=WARRANT, revision_id=first.id
        )
        == first
    )
    with pytest.raises(ApplicationError) as captured:
        await record(
            context,
            command(supersedes_revision_id=first.id),
            now=NOW + timedelta(seconds=3),
        )
    assert captured.value.code == "PRODUCT_PRICE_SCALE_REVISION_CONFLICT"
    assert len(rows(context)) == 2


@pytest.mark.asyncio
async def test_more_than_twenty_revisions_are_not_truncated_and_old_original_remains_accessible(
    context,
):
    previous = first = await record(context)
    for number in range(1, 23):
        previous = await record(
            context,
            command(
                manifest(source_version=f"synthetic-v{number}"),
                supersedes_revision_id=previous.id,
            ),
            now=NOW + timedelta(seconds=number),
        )
    result = await current(context, known_at=NOW + timedelta(minutes=1))
    assert result.revision_number == 23 and result.revision_id == previous.id
    assert (
        await context.reader.revision(
            workspace_id=WORKSPACE, warrant_id=WARRANT, revision_id=first.id
        )
    ).manifest.source_version == "synthetic-final-terms-v1"


@pytest.mark.asyncio
async def test_absence_and_old_knowledge_boundary_are_explicit(context):
    empty = await current(context)
    assert empty.status == "MISSING" and empty.reasons == ("PRODUCT_PRICE_SCALE_EVIDENCE_MISSING",)
    assert empty.manifest is empty.source is empty.binding is empty.revision_id is None
    await record(context)
    assert (await current(context, known_at=NOW - timedelta(microseconds=1))).status == "MISSING"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,value",
    [
        ("isin", "DE000VH4VNA6"),
        ("issuer_id", UUID(int=900)),
        ("underlying_id", UUID(int=901)),
    ],
)
async def test_current_identity_changes_invalidate_instead_of_rebinding_original(
    context, field, value
):
    first = await record(context)
    setattr(context.sql.get(WarrantModel, WARRANT), field, value)
    context.sql.commit()
    result = await current(context)
    assert result.status == "UNSUITABLE" and result.reasons == (
        "PRODUCT_PRICE_SCALE_BINDING_CHANGED",
    )
    assert result.binding == first.manifest.binding
    assert (
        await context.reader.revision(
            workspace_id=WORKSPACE, warrant_id=WARRANT, revision_id=first.id
        )
    ) == first


@pytest.mark.asyncio
async def test_new_terms_head_invalidates_even_identical_ratio_and_does_not_move_source_validity(
    context,
):
    first = await record(context)
    context.sql.get(WarrantTermsVersionModel, TERMS).effective_to = NOW
    newer = WarrantTermsVersionModel(
        id=uuid4(),
        warrant_id=WARRANT,
        version_no=2,
        effective_from=NOW,
        effective_to=None,
        option_direction=OptionDirection.CALL,
        strike=100,
        ratio="0.1",
        maturity_date=date(2027, 6, 1),
        strike_currency_code="EUR",
        created_at=NOW,
    )
    context.sql.add(newer)
    context.sql.commit()
    result = await current(context)
    assert result.status == "UNSUITABLE"
    assert result.manifest.valid_from == first.manifest.valid_from
    assert result.binding.current_terms_id == TERMS
    assert result.reasons == ("PRODUCT_PRICE_SCALE_BINDING_CHANGED",)


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["isin", "issuer_id", "underlying_id", "current_terms_id"])
async def test_foreign_document_binding_cannot_be_imported(context, field):
    binding = manifest()["binding"] | {field: "DE000VH4VNA6" if field == "isin" else str(uuid4())}
    with pytest.raises(ApplicationError) as captured:
        await record(context, command(manifest(binding=binding)))
    assert captured.value.code == "PRODUCT_PRICE_SCALE_BINDING_MISMATCH"
    assert rows(context) == []


@pytest.mark.asyncio
async def test_scope_and_query_clock_errors_are_not_missing_evidence(context):
    first = await record(context)
    for scope in ({"workspace_id": uuid4()}, {"warrant_id": uuid4()}):
        with pytest.raises(ApplicationError) as captured:
            await current(context, **scope)
        assert captured.value.status_code == 404
    with pytest.raises(ApplicationError) as captured:
        await current(context, known_at=NOW.replace(tzinfo=None))
    assert captured.value.status_code == 422
    for scope in (
        {"workspace_id": uuid4()},
        {"warrant_id": uuid4()},
        {"revision_id": uuid4()},
    ):
        arguments = dict(workspace_id=WORKSPACE, warrant_id=WARRANT, revision_id=first.id) | scope
        with pytest.raises(ApplicationError) as captured:
            await context.reader.revision(**arguments)
        assert captured.value.status_code == 404


@pytest.mark.asyncio
async def test_reads_never_flush_pending_changes_write_or_erase_drafts(context):
    first = await record(context)
    pending = context.sql.get(WarrantModel, WARRANT)
    pending.display_name = "Unsaved user draft"
    context.session.add.reset_mock()
    context.session.commit.reset_mock()
    context.session.flush.reset_mock()
    context.session.rollback.reset_mock()
    result = await current(context)
    assert result.revision_id == first.id and result.status == "AVAILABLE"
    assert pending.display_name == "Unsaved user draft" and pending in context.sql.dirty
    for method in (
        context.session.commit,
        context.session.flush,
        context.session.rollback,
    ):
        method.assert_not_awaited()
    context.session.add.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fault",
    [
        "document",
        "manifest",
        "source_publisher",
        "source_actor",
        "request_hash",
        "terms_id",
        "revision",
    ],
)
async def test_corrupt_stored_originals_are_read_failures_not_missing_or_old_fallback(
    context, fault
):
    first = await record(context)
    row = rows(context)[0]
    if fault == "document":
        row.document_bytes += b"changed"
    elif fault == "manifest":
        row.manifest_json += " "
    elif fault == "source_publisher":
        row.source = row.source | {"publisher": "Different source"}
    elif fault == "source_actor":
        row.source = row.source | {"recorded_by": str(uuid4())}
    elif fault == "request_hash":
        row.request_fingerprint = "0" * 64
    elif fault == "terms_id":
        row.terms_id = uuid4()
    else:
        row.revision_number = 2
    context.sql.commit()  # SQLite-only corruption fixture; production trigger forbids UPDATE.
    for action in (
        current(context),
        context.reader.revision(workspace_id=WORKSPACE, warrant_id=WARRANT, revision_id=first.id),
    ):
        with pytest.raises(ApplicationError) as captured:
            await action
        assert captured.value.status_code == 503
        assert captured.value.code == "PRODUCT_PRICE_SCALE_READ_UNAVAILABLE"


@pytest.mark.asyncio
async def test_database_errors_and_write_races_remain_explicit(context, monkeypatch):
    monkeypatch.setattr(
        context.reader._repository,
        "latest",
        AsyncMock(side_effect=DBAPIError("SELECT", {}, Exception("synthetic unavailable"))),
    )
    with pytest.raises(ApplicationError) as captured:
        await current(context)
    assert captured.value.status_code == 503
    monkeypatch.setattr(
        context.service._repository,
        "add",
        AsyncMock(side_effect=IntegrityError("INSERT", {}, Exception("synthetic race"))),
    )
    with pytest.raises(ApplicationError) as captured:
        await record(context)
    assert captured.value.status_code == 409
    assert rows(context) == []


@pytest.mark.asyncio
async def test_repository_does_not_return_an_original_from_another_product(context):
    first = await record(context)
    repository = SqlAlchemyProductPriceScaleEvidenceRepository(context.session)
    assert await repository.get(WORKSPACE, uuid4(), first.id) is None
    assert await repository.get(uuid4(), WARRANT, first.id) is None
