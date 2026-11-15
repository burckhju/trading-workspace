"""Real session evidence commands and snapshot reads through the HTTP boundary."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import TypeAdapter
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine
from tests.unit.backend.features.market_data import test_session_evidence_service as examples

from app.core.config import Environment, Settings
from app.features.market_data.api import session_evidence as api
from app.features.market_data.domain.session_evidence import SessionEvidenceImportCommand
from app.features.market_data.service import session_evidence as service_module
from app.main import create_application

context = examples.context
no_provider_access = examples.no_provider_access
pytestmark = pytest.mark.asyncio
URL = "/api/v1/market-data/session-evidence"
CONFIRMATION = "CONFIRM_OFFICIAL_SESSION_DOCUMENT_REVIEW"


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return examples.NOW.astimezone(tz) if tz else examples.NOW.replace(tzinfo=None)


def body(**overrides):
    result = TypeAdapter(SessionEvidenceImportCommand).dump_python(examples.command(), mode="json")
    result["confirmation"] = CONFIRMATION
    result.update(overrides)
    return result


def query(**overrides):
    result = {
        "instrument_kind": "UNDERLYING",
        "instrument_id": str(examples.INSTRUMENT),
        "start_date": examples.START.isoformat(),
        "end_date": examples.END.isoformat(),
        "known_at": examples.NOW.isoformat(),
        "expected_listing_id": str(examples.LISTING),
    }
    result.update(overrides)
    return result


@pytest.fixture
def app(context, monkeypatch):
    application = create_application(
        Settings(_env_file=None, environment=Environment.TEST, documentation_enabled=True)
    )
    engine = Mock(spec=AsyncEngine)
    reader_session = examples.SqlSession(context.sql)
    reader_session.commit = AsyncMock(side_effect=AssertionError("GET cannot commit"))
    reader_session.flush = AsyncMock(side_effect=AssertionError("GET cannot flush"))
    reader_session.add = Mock(side_effect=AssertionError("GET cannot write"))
    session_factory = Mock(return_value=reader_session)
    monkeypatch.setattr(api, "WORKSPACE_ID", examples.WORKSPACE)
    monkeypatch.setattr(api, "LOCAL_ACTOR_ID", examples.ACTOR)
    monkeypatch.setattr(api, "AsyncSession", session_factory)
    monkeypatch.setattr(service_module, "datetime", FrozenDatetime)
    application.dependency_overrides[api.get_import_service] = lambda: context.service
    application.dependency_overrides[api.get_read_engine] = lambda: engine
    context.reader_session = reader_session
    context.reader_session_factory = session_factory
    context.read_engine = engine
    yield application
    application.dependency_overrides.clear()


async def test_explicit_import_then_current_range_and_original_reads_preserve_exact_evidence(
    app, context
):
    incoming = body()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(URL + "/imports", json=incoming)
        assert created.status_code == 201, created.text
        result = created.json()
        assert result["manifest_json"] == incoming["manifest_json"]
        assert result["document_base64"] == incoming["document_base64"]
        assert result["source"]["recorded_by"] == str(examples.ACTOR)
        assert result["verification"] == "MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION"
        context.session.commit.reset_mock()
        context.session.statements.clear()

        def no_writer():
            raise AssertionError("A saved read must not construct an import service")

        app.dependency_overrides[api.get_import_service] = no_writer
        current = await client.get(URL + "/current", params=query())
        assert current.status_code == 200, current.text
        assert current.json()["revision_id"] == result["id"]
        assert current.json()["status"] == "AVAILABLE"
        ranged = await client.get(URL, params=query())
        assert ranged.status_code == 200, ranged.text
        assert ranged.json()["status"] == "COMPLETE"
        assert ranged.json()["days"][-1]["status"] == "CLOSED"
        assert ranged.json()["operation_status"] == "READ_ONLY"
        original = await client.get(URL + f"/revisions/{result['id']}", params=query())
        assert original.status_code == 200, original.text
        assert original.json() == result

    assert len(examples.rows(context)) == 1
    context.session.commit.assert_not_awaited()
    context.reader_session.commit.assert_not_awaited()
    context.reader_session.flush.assert_not_awaited()
    context.reader_session.add.assert_not_called()
    assert context.reader_session.rollback.await_count == 3
    context.reader_session_factory.assert_called_with(
        context.read_engine, expire_on_commit=False, autoflush=False
    )
    setups = [
        str(statement)
        for statement in context.reader_session.statements
        if str(statement).startswith("SET")
    ]
    assert (
        setups
        == [
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY",
            "SET LOCAL statement_timeout = '10000ms'",
        ]
        * 3
    )


@pytest.mark.parametrize(
    "change",
    [
        {"confirmation": None},
        {"confirmation": "ASSESS_SAVED_HEBELTRADER_EVIDENCE"},
        {"workspace_id": str(uuid4())},
        {"recorded_by": str(uuid4())},
        {"manifest_sha256": "wrong"},
        {"reviewed_at": "2026-11-15T09:00:00"},
        {"request_id": "not-an-id"},
    ],
)
async def test_invalid_or_unconfirmed_http_payload_never_reaches_the_command(app, context, change):
    spy = AsyncMock(side_effect=context.service.record)
    context.service.record = spy
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(URL + "/imports", json=body(**change))
    assert response.status_code == 422, response.text
    spy.assert_not_awaited()
    context.session.commit.assert_not_awaited()
    assert examples.rows(context) == []


async def test_actor_header_is_validated_and_retained_without_accepting_a_body_workspace(
    app, context
):
    actor = uuid4()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            URL + "/imports", json=body(), headers={"X-Actor-ID": str(actor)}
        )
        assert response.status_code == 201, response.text
        assert response.json()["source"]["recorded_by"] == str(actor)
        assert response.json()["workspace_id"] == str(examples.WORKSPACE)
        rejected = await client.post(
            URL + "/imports", json=body(), headers={"X-Actor-ID": "invalid"}
        )
        assert rejected.status_code == 422
    assert len(examples.rows(context)) == 1


@pytest.mark.parametrize(
    "change",
    [
        {"instrument_kind": "STOCK"},
        {"instrument_id": "invalid"},
        {"known_at": "2026-11-15T10:00:00"},
        {"start_date": "not-a-date"},
    ],
)
async def test_invalid_read_query_is_rejected_before_opening_snapshot(app, context, change):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(URL, params=query(**change))
    assert response.status_code == 422, response.text
    context.reader_session_factory.assert_not_called()


async def test_duplicate_query_and_foreign_original_scope_cannot_return_evidence(app, context):
    original = await examples.record(context)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        duplicate = [*query().items(), ("instrument_id", str(uuid4()))]
        response = await client.get(URL, params=duplicate)
        assert response.status_code == 422, response.text
        assert response.json()["code"] == "SESSION_EVIDENCE_INVALID"
        context.reader_session_factory.assert_not_called()
        for revision, instrument in ((original.id, uuid4()), (uuid4(), examples.INSTRUMENT)):
            response = await client.get(
                URL + f"/revisions/{revision}", params=query(instrument_id=str(instrument))
            )
            assert response.status_code == 404, response.text
            assert response.json()["code"] == "SESSION_EVIDENCE_SCOPE_NOT_FOUND"
            assert original.manifest_json not in response.text
    assert len(examples.rows(context)) == 1


@pytest.mark.parametrize(
    "endpoint", ["", "/current", "/revisions/00000000-0000-4000-8000-000000000333"]
)
async def test_unavailable_database_is_503_not_missing_evidence(app, context, endpoint):
    failure = DBAPIError("synthetic-select", None, RuntimeError("synthetic failure"), False)
    context.reader_session.execute = AsyncMock(side_effect=failure)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(URL + endpoint, params=query())
    assert response.status_code == 503, response.text
    assert response.json()["code"] == "SESSION_EVIDENCE_READ_UNAVAILABLE"
    context.reader_session.rollback.assert_awaited_once()
    context.reader_session.commit.assert_not_awaited()


async def test_read_exact_old_revision_after_replacement_never_relabels_original_as_current(
    app, context
):
    first = await examples.record(context)
    second = await examples.record(
        context,
        examples.command(
            examples.manifest(
                calendar_version="synthetic-new-calendar-v2", evidence_status="WITHDRAWN"
            ),
            supersedes_revision_id=first.id,
        ),
        now=examples.NOW + timedelta(seconds=1),
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        current = await client.get(
            URL + "/current", params=query(known_at=second.recorded_at.isoformat())
        )
        assert current.status_code == 200, current.text
        assert current.json()["revision_id"] == str(second.id)
        assert current.json()["status"] == "UNSUITABLE"
        original = await client.get(URL + f"/revisions/{first.id}", params=query())
        assert original.status_code == 200, original.text
        assert original.json()["id"] == str(first.id)
        assert original.json()["manifest_json"] == first.manifest_json
        assert original.json()["source"]["recorded_by"] == str(examples.ACTOR)


async def test_corrupted_original_bytes_fail_closed_in_saved_read(app, context):
    await examples.record(context)
    # SQLite deliberately bypasses the PostgreSQL immutable trigger for this reader failure case.
    examples.rows(context)[0].document_bytes = b"changed after capture"
    context.sql.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(URL, params=query())
    assert response.status_code == 503, response.text
    assert response.json()["code"] == "SESSION_EVIDENCE_READ_UNAVAILABLE"
