"""Document-backed session imports and reads with synthetic owner facts only."""

import base64
import hashlib
import json
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.exceptions import ApplicationError
from app.features.market.domain.enums import DataOrigin, LifecycleStatus, UnderlyingType
from app.features.market.domain.enums import QualityStatus as ReferenceQuality
from app.features.market.persistence import top_down_models as _top_down_models  # noqa: F401
from app.features.market.persistence.models import (
    ListingModel,
    TradingVenueModel,
    UnderlyingModel,
    WorkspaceModel,
)
from app.features.market_data.domain.session_evidence import (
    MAX_DOCUMENT_BYTES,
    MAX_MANIFEST_BYTES,
    MAX_SESSION_DAYS,
    SessionEvidenceImportCommand,
)
from app.features.market_data.persistence.session_evidence import SessionEvidenceModel
from app.features.product.persistence.models import WarrantListingModel, WarrantModel

WORKSPACE = UUID(int=100)
ACTOR = UUID(int=101)
INSTRUMENT = UUID(int=102)
LISTING = UUID(int=103)
VENUE = UUID(int=104)
NOW = datetime(2026, 11, 15, 10, tzinfo=UTC)
START = date(2026, 11, 9)
END = date(2026, 11, 11)
DOCUMENT = (
    b"Synthetic original exchange document, no real source or provider.\n"
    b"2026-11-09 09:00-17:30 Europe/Berlin; 2026-11-10 09:00-17:30 Europe/Berlin.\n"
    b"2026-11-11: documented full-day closure.\n"
)


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def manifest(**overrides):
    value = {
        "schema_version": "session-evidence-manifest-v1",
        "calendar_id": "synthetic-exchange-regular-equities",
        "calendar_version": "synthetic-v1",
        "binding": {
            "instrument_kind": "UNDERLYING",
            "instrument_id": str(INSTRUMENT),
            "listing_id": str(LISTING),
            "trading_venue_id": str(VENUE),
            "venue_mic": "XETR",
            "timezone": "Europe/Berlin",
            "market_segment": "Synthetic regular equity sessions",
            "valid_from": "2026-11-01",
            "valid_through": "2026-11-30",
        },
        "coverage_start": START.isoformat(),
        "coverage_end": END.isoformat(),
        "days": [
            {
                "session_date": day,
                "status": "SESSION",
                "intervals": [
                    {
                        "opens_at": f"{day}T09:00:00+01:00",
                        "closes_at": f"{day}T17:30:00+01:00",
                    }
                ],
                "source_reference": "Synthetic original document / page 1",
            }
            for day in ("2026-11-09", "2026-11-10")
        ]
        + [
            {
                "session_date": "2026-11-11",
                "status": "CLOSED",
                "intervals": [],
                "source_reference": "Synthetic original document / documented closure",
            }
        ],
        "source_publisher": "Synthetic Exchange",
        "source_reference": "https://example.invalid/synthetic/official-calendar",
        "source_document_sha256": digest(DOCUMENT),
        "source_published_at": None,
        "source_published_on": "2026-11-01",
    }
    value.update(overrides)
    return value


def command(value=None, **overrides):
    # Preserve actual caller whitespace: the original is not a normalized reserialization.
    original = json.dumps(manifest() if value is None else value, indent=2) + "\n"
    values = {
        "request_id": uuid4(),
        "supersedes_revision_id": None,
        "manifest_json": original,
        "manifest_sha256": digest(original.encode()),
        "document_filename": "synthetic-original-session-source.txt",
        "document_media_type": "text/plain",
        "document_base64": base64.b64encode(DOCUMENT).decode(),
        "document_sha256": digest(DOCUMENT),
        "reviewed_at": NOW - timedelta(hours=1),
        "review_reference": "Synthetic explicit review against full original document / page 1",
        "retrieved_at": NOW - timedelta(hours=2),
    }
    values.update(overrides)
    return SessionEvidenceImportCommand(**values)


@pytest.fixture(autouse=True)
def no_provider_access(monkeypatch):
    asynchronous = AsyncMock(side_effect=AssertionError("Session evidence cannot fetch sources"))
    synchronous = Mock(side_effect=AssertionError("Session evidence cannot fetch sources"))
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", asynchronous)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", synchronous)
    yield
    asynchronous.assert_not_awaited()
    synchronous.assert_not_called()


class SqlSession:
    """Real SQLite SELECT/storage semantics; PostgreSQL-only transaction setup is recorded.

    The separate guarded PostgreSQL cases exercise real isolation, row locks and
    triggers. This adapter never opens a network/database connection outside RAM.
    """

    def __init__(self, session):
        self.session = session
        self.statements = []
        self.commit = AsyncMock(side_effect=session.commit)
        self.rollback = AsyncMock(side_effect=session.rollback)
        self.flush = AsyncMock(side_effect=session.flush)
        self.add = Mock(side_effect=session.add)

    @property
    def no_autoflush(self):
        return self.session.no_autoflush

    async def execute(self, statement, *args, **kwargs):
        self.statements.append(statement)
        if str(statement).lstrip().upper().startswith("SET "):
            return Mock()
        return self.session.execute(statement, *args, **kwargs)

    async def scalar(self, statement):
        return (await self.execute(statement)).scalar()

    async def scalars(self, statement):
        return (await self.execute(statement)).scalars()

    async def get(self, model, key):
        return self.session.get(model, key)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None


@pytest.fixture
def context():
    from app.features.market_data.service.session_evidence import (
        SessionEvidenceImportService,
        SessionEvidenceReader,
    )

    engine = create_engine("sqlite://")
    for model in (
        WorkspaceModel,
        TradingVenueModel,
        UnderlyingModel,
        ListingModel,
        WarrantModel,
        WarrantListingModel,
        SessionEvidenceModel,
    ):
        model.__table__.create(engine)
    clocks = {"created_at": NOW - timedelta(days=365), "updated_at": NOW, "version": 1}
    with Session(engine, expire_on_commit=False, autoflush=False) as session:
        session.add_all(
            [
                WorkspaceModel(id=WORKSPACE, name="Synthetic sessions", created_at=NOW),
                TradingVenueModel(
                    id=VENUE,
                    mic="XETR",
                    name="Synthetic venue",
                    country_code="DE",
                    timezone="Europe/Berlin",
                    is_active=True,
                    reference_version="synthetic-reference-v1",
                    **clocks,
                ),
                UnderlyingModel(
                    id=INSTRUMENT,
                    workspace_id=WORKSPACE,
                    type=UnderlyingType.STOCK,
                    name="Synthetic session underlying",
                    lifecycle_status=LifecycleStatus.ACTIVE,
                    quality_status=ReferenceQuality.VERIFIED,
                    data_origin=DataOrigin.MANUAL,
                    **clocks,
                ),
                ListingModel(
                    id=LISTING,
                    workspace_id=WORKSPACE,
                    underlying_id=INSTRUMENT,
                    trading_venue_id=VENUE,
                    ticker="SYNTH",
                    currency_code="EUR",
                    lifecycle_status=LifecycleStatus.ACTIVE,
                    is_primary=True,
                    data_origin=DataOrigin.MANUAL,
                    **clocks,
                ),
            ]
        )
        session.commit()
        adapter = SqlSession(session)
        yield SimpleNamespace(
            sql=session,
            session=adapter,
            service=SessionEvidenceImportService(adapter),
            reader=SessionEvidenceReader(adapter),
            engine=engine,
        )
    engine.dispose()


async def record(context, value=None, *, now=NOW, workspace=WORKSPACE, actor=ACTOR):
    return await context.service.record(
        workspace_id=workspace,
        actor_id=actor,
        command=command() if value is None else value,
        now=now,
    )


async def read(context, **overrides):
    values = {
        "workspace_id": WORKSPACE,
        "instrument_kind": "UNDERLYING",
        "instrument_id": INSTRUMENT,
        "start_date": START,
        "end_date": END,
        "known_at": NOW,
        "expected_listing_id": LISTING,
    }
    values.update(overrides)
    return await context.reader.read(**values)


def rows(context):
    return context.sql.scalars(select(SessionEvidenceModel)).all()


@pytest.mark.asyncio
async def test_import_preserves_full_originals_hashes_and_distinct_audit_clocks(context):
    incoming = command()
    result = await record(context, incoming)
    assert result.manifest_json == incoming.manifest_json
    assert result.document_base64 == incoming.document_base64
    assert base64.b64decode(result.document_base64) == DOCUMENT
    assert result.source.manifest_sha256 == digest(incoming.manifest_json.encode())
    assert (
        result.source.document_sha256 == result.manifest.source_document_sha256 == digest(DOCUMENT)
    )
    assert result.source.recorded_by == ACTOR
    assert result.recorded_at == NOW
    assert result.source.reviewed_at == NOW - timedelta(hours=1)
    assert result.source.retrieved_at == NOW - timedelta(hours=2)
    assert result.source.published_at is None
    assert result.source.published_on == date(2026, 11, 1)
    assert result.verification == "MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION"
    assert result.revision_number == 1
    assert result.supersedes_revision_id is None
    assert len(rows(context)) == 1
    context.session.commit.assert_awaited_once()
    assert str(context.session.statements[0]) == "SET TRANSACTION ISOLATION LEVEL READ COMMITTED"
    assert "FOR UPDATE" in str(context.session.statements[1])

    saved = await context.reader._repository.get(WORKSPACE, result.id)
    assert saved == result


@pytest.mark.asyncio
async def test_replay_after_new_revision_returns_original_without_append_or_recommit(context):
    incoming = command()
    first = await record(context, incoming)
    second = await record(
        context,
        command(manifest(calendar_version="synthetic-v2"), supersedes_revision_id=first.id),
        now=NOW + timedelta(minutes=1),
    )
    before = context.session.commit.await_count
    assert await record(context, incoming, now=NOW + timedelta(minutes=2)) == first
    assert context.session.commit.await_count == before
    assert len(rows(context)) == 2
    assert second.supersedes_revision_id == first.id
    assert second.revision_number == 2


@pytest.mark.asyncio
async def test_same_request_with_changed_statement_is_conflict_without_extra_revision(context):
    incoming = command()
    await record(context, incoming)
    with pytest.raises(ApplicationError) as caught:
        await record(context, replace(incoming, review_reference="A different synthetic statement"))
    assert caught.value.code == "SESSION_EVIDENCE_REQUEST_CONFLICT"
    assert caught.value.status_code == 409
    assert len(rows(context)) == 1
    assert context.session.commit.await_count == 1


@pytest.mark.asyncio
async def test_replay_cannot_attribute_original_review_to_another_actor(context):
    incoming = command()
    original = await record(context, incoming)
    with pytest.raises(ApplicationError) as caught:
        await record(context, incoming, actor=uuid4())
    assert caught.value.code == "SESSION_EVIDENCE_REQUEST_CONFLICT"
    assert len(rows(context)) == 1
    assert (
        await context.reader._repository.get(WORKSPACE, original.id)
    ).source.recorded_by == ACTOR


@pytest.mark.asyncio
@pytest.mark.parametrize("predecessor", [None, UUID(int=999)])
async def test_stale_or_foreign_predecessor_never_creates_a_parallel_revision(context, predecessor):
    first = await record(context)
    with pytest.raises(ApplicationError) as caught:
        await record(context, command(supersedes_revision_id=predecessor))
    assert caught.value.code == "SESSION_EVIDENCE_REVISION_CONFLICT"
    assert [row.id for row in rows(context)] == [first.id]


@pytest.mark.asyncio
async def test_record_time_cannot_precede_the_existing_revision(context):
    first = await record(context)
    with pytest.raises(ApplicationError) as caught:
        await record(
            context,
            command(supersedes_revision_id=first.id),
            now=NOW - timedelta(minutes=1),
        )
    assert caught.value.code == "SESSION_EVIDENCE_REVISION_CONFLICT"
    assert len(rows(context)) == 1


def invalid_package(kind):
    if kind == "manifest_hash":
        return command(manifest_sha256="0" * 64)
    if kind == "document_hash":
        return command(document_sha256="0" * 64)
    if kind == "manifest_document_link":
        return command(manifest(source_document_sha256="0" * 64))
    if kind == "empty_document":
        return command(document_base64="", document_sha256=digest(b""))
    if kind == "invalid_base64":
        return command(document_base64="not base64 :/")
    if kind == "filename_path":
        return command(document_filename="../original.txt")
    if kind == "unsupported_media":
        return command(document_media_type="application/octet-stream")
    if kind == "future_review":
        return command(reviewed_at=NOW + timedelta(microseconds=1))
    if kind == "unknown_review_zone":
        return command(reviewed_at=NOW.replace(tzinfo=None))
    if kind == "future_retrieval":
        return command(retrieved_at=NOW + timedelta(microseconds=1))
    if kind == "publication_after_review":
        return command(manifest(source_published_on=None, source_published_at=NOW.isoformat()))
    if kind == "unknown_review_reference":
        return command(review_reference=" ")
    if kind == "duplicate_json_key":
        original = command().manifest_json.replace(
            '"calendar_version": "synthetic-v1",',
            '"calendar_version": "synthetic-v1", "calendar_version": "shadowed-v2",',
        )
        return command(manifest_json=original, manifest_sha256=digest(original.encode()))
    raise AssertionError(kind)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kind",
    [
        "manifest_hash",
        "document_hash",
        "manifest_document_link",
        "empty_document",
        "invalid_base64",
        "filename_path",
        "unsupported_media",
        "future_review",
        "unknown_review_zone",
        "future_retrieval",
        "publication_after_review",
        "unknown_review_reference",
        "duplicate_json_key",
    ],
)
async def test_invalid_original_package_rejected_before_any_owner_or_persistence_access(
    context, kind
):
    with pytest.raises(ApplicationError) as caught:
        await record(context, invalid_package(kind))
    assert caught.value.code == "SESSION_EVIDENCE_INVALID"
    assert caught.value.status_code == 422
    assert context.session.statements == []
    context.session.add.assert_not_called()
    context.session.flush.assert_not_awaited()
    context.session.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("part", ["document", "manifest"])
async def test_oversized_originals_fail_before_database_access(context, part):
    if part == "document":
        data = b"x" * (MAX_DOCUMENT_BYTES + 1)
        incoming = command(
            manifest(source_document_sha256=digest(data)),
            document_base64=base64.b64encode(data).decode(),
            document_sha256=digest(data),
        )
    else:
        original = " " * (MAX_MANIFEST_BYTES + 1)
        incoming = command(manifest_json=original, manifest_sha256=digest(original.encode()))
    with pytest.raises(ApplicationError) as caught:
        await record(context, incoming)
    assert caught.value.code == "SESSION_EVIDENCE_INVALID"
    assert context.session.statements == []
    context.session.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["instrument_id", "listing_id", "trading_venue_id", "venue_mic"])
async def test_import_rejects_foreign_instrument_listing_and_venue(context, field):
    value = manifest()
    value["binding"][field] = "XNYS" if field == "venue_mic" else str(uuid4())
    with pytest.raises(ApplicationError) as caught:
        await record(context, command(value))
    assert caught.value.code == (
        "SESSION_EVIDENCE_SCOPE_NOT_FOUND"
        if field == "instrument_id"
        else "SESSION_EVIDENCE_BINDING_MISMATCH"
    )
    assert rows(context) == []
    context.session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_foreign_workspace_cannot_import_or_read_known_instrument(context):
    original = await record(context)
    for operation in (
        record(context, workspace=uuid4()),
        read(context, workspace_id=uuid4()),
    ):
        with pytest.raises(ApplicationError) as caught:
            await operation
        assert caught.value.code == "SESSION_EVIDENCE_SCOPE_NOT_FOUND"
        assert caught.value.status_code == 404
    assert [row.id for row in rows(context)] == [original.id]


@pytest.mark.asyncio
async def test_warrant_scope_requires_its_actual_product_listing_and_stays_separate(context):
    product, listing = uuid4(), uuid4()
    clocks = {"created_at": NOW, "updated_at": NOW, "version": 1}
    context.sql.add_all(
        [
            WarrantModel(
                id=product,
                workspace_id=WORKSPACE,
                issuer_id=uuid4(),
                underlying_id=INSTRUMENT,
                display_name="Synthetic held product",
                lifecycle_status="ACTIVE",
                **clocks,
            ),
            WarrantListingModel(
                id=listing,
                workspace_id=WORKSPACE,
                warrant_id=product,
                trading_venue_id=VENUE,
                quotation_currency_code="EUR",
                lifecycle_status="ACTIVE",
                **clocks,
            ),
        ]
    )
    context.sql.commit()
    value = manifest()
    value["binding"].update(
        instrument_kind="WARRANT", instrument_id=str(product), listing_id=str(LISTING)
    )
    with pytest.raises(ApplicationError) as caught:
        await record(context, command(value))
    assert caught.value.code == "SESSION_EVIDENCE_BINDING_MISMATCH"
    value["binding"]["listing_id"] = str(listing)
    saved = await record(context, command(value))
    result = await read(
        context, instrument_kind="WARRANT", instrument_id=product, expected_listing_id=listing
    )
    assert result.status == "COMPLETE" and result.revision_id == saved.id
    assert (await read(context)).status == "MISSING"
    stored = rows(context)[0]
    assert stored.warrant_id == product and stored.warrant_listing_id == listing
    assert stored.underlying_id is stored.listing_id is None


@pytest.mark.asyncio
async def test_read_uses_whole_latest_revision_without_mixing_unknown_or_omitted_days(context):
    first = await record(context)
    replacement = manifest(calendar_version="synthetic-v2")
    replacement["days"] = [
        replacement["days"][0],
        {
            "session_date": END.isoformat(),
            "status": "UNKNOWN",
            "intervals": [],
            "source_reference": "Synthetic correction: closure not established",
        },
    ]
    second = await record(
        context,
        command(replacement, supersedes_revision_id=first.id),
        now=NOW + timedelta(minutes=1),
    )
    latest = await read(context, known_at=second.recorded_at)
    assert latest.status == "INCOMPLETE"
    assert latest.revision_id == second.id
    assert latest.revision_number == 2
    assert latest.missing_dates == (date(2026, 11, 10),)
    assert [day.session_date for day in latest.days] == [START, END]
    assert latest.days[-1].status == "UNKNOWN"
    assert "SESSION_DAY_EVIDENCE_GAP" in latest.reasons
    assert "SESSION_DAY_EVIDENCE_UNKNOWN" in latest.reasons

    prior = await read(context, known_at=first.recorded_at)
    assert prior.status == "COMPLETE"
    assert prior.revision_id == first.id
    assert prior.days[-1].status == "CLOSED"
    assert prior.fingerprint != latest.fingerprint
    missing = await read(context, known_at=first.recorded_at - timedelta(microseconds=1))
    assert missing.status == "MISSING"
    assert missing.revision_id is None and missing.source is None


@pytest.mark.asyncio
async def test_withdrawn_revision_prevents_fallback_even_when_older_days_were_complete(context):
    first = await record(context)
    withdrawn = await record(
        context,
        command(
            manifest(calendar_version="withdrawn-v2", evidence_status="WITHDRAWN", days=[]),
            supersedes_revision_id=first.id,
        ),
        now=NOW + timedelta(minutes=1),
    )
    result = await read(context, known_at=withdrawn.recorded_at)
    assert result.status == "UNSUITABLE"
    assert result.revision_id == withdrawn.id
    assert result.evidence_status == "WITHDRAWN"
    assert result.days == ()
    assert "SESSION_EVIDENCE_WITHDRAWN" in result.reasons


@pytest.mark.asyncio
async def test_requested_range_outside_coverage_remains_incomplete_without_invented_closed_days(
    context,
):
    await record(context)
    result = await read(
        context, start_date=START - timedelta(days=1), end_date=END + timedelta(days=1)
    )
    assert result.status == "INCOMPLETE"
    assert result.missing_dates == (START - timedelta(days=1), END + timedelta(days=1))
    assert "SESSION_COVERAGE_RANGE_GAP" in result.reasons
    assert len(result.days) == 3


@pytest.mark.asyncio
async def test_oversized_read_is_explicitly_limited_instead_of_truncated_or_complete(context):
    first = await record(context)
    result = await read(context, end_date=START + timedelta(days=MAX_SESSION_DAYS))
    assert result.status == "LIMIT_EXCEEDED"
    assert result.revision_id == first.id
    assert result.days == ()
    assert "SESSION_RANGE_LIMIT_EXCEEDED" in result.reasons


@pytest.mark.asyncio
async def test_read_does_not_rebind_listing_or_replace_documented_timezone_with_current_reference(
    context,
):
    first = await record(context)
    context.sql.get(TradingVenueModel, VENUE).timezone = "America/New_York"
    context.sql.commit()
    result = await read(context)
    assert result.status == "COMPLETE"
    assert result.binding.timezone == "Europe/Berlin"
    assert result.revision_id == first.id
    incompatible = await read(context, expected_listing_id=uuid4())
    assert incompatible.status == "UNSUITABLE"
    assert "SESSION_LISTING_BINDING_MISMATCH" in incompatible.reasons


@pytest.mark.asyncio
async def test_read_is_only_selects_and_never_flushes_pending_edits_or_changes_transaction(context):
    await record(context)
    # A consumer must not accidentally persist another owner's pending changes.
    listing = context.sql.get(ListingModel, LISTING)
    listing.ticker = "PENDING-UNFLUSHED"
    for method in (context.session.commit, context.session.rollback, context.session.flush):
        method.reset_mock()
    context.session.add.reset_mock()
    context.session.statements.clear()
    result = await read(context)
    assert result.status == "COMPLETE"
    assert result.operation_status == "READ_ONLY"
    assert all(
        str(statement).lstrip().upper().startswith("SELECT")
        for statement in context.session.statements
    )
    assert listing in context.sql.dirty
    context.session.add.assert_not_called()
    context.session.flush.assert_not_awaited()
    context.session.commit.assert_not_awaited()
    context.session.rollback.assert_not_awaited()
