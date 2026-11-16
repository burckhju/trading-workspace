"""Actual HTTP boundaries, synthetic imports, server-clock snapshots and zero read effects."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import TypeAdapter
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine
from tests.unit.backend.features.market_data.test_session_evidence_service import (
    SqlSession,
)
from tests.unit.backend.features.product import (
    test_price_scale_evidence_service as examples,
)

from app.core.config import Environment, Settings
from app.features.product.api import price_scale_evidence as api
from app.features.product.domain.price_scale_evidence import (
    ProductPriceScaleImportCommand,
)
from app.features.product.service import price_scale_evidence as service_module
from app.main import create_application

context = examples.context
no_provider_access = examples.no_provider_access
pytestmark = pytest.mark.asyncio
URL = f"/api/v1/warrants/{examples.WARRANT}/price-scale-evidence"
CONFIRMATION = "CONFIRM_PRODUCT_PRICE_SCALE_DOCUMENT_REVIEW"


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return examples.NOW.astimezone(tz) if tz else examples.NOW.replace(tzinfo=None)


def body(**overrides):
    value = TypeAdapter(ProductPriceScaleImportCommand).dump_python(examples.command(), mode="json")
    value["confirmation"] = CONFIRMATION
    value.update(overrides)
    return value


@pytest.fixture
def app(context, monkeypatch):
    application = create_application(
        Settings(_env_file=None, environment=Environment.TEST, documentation_enabled=True)
    )
    engine = Mock(spec=AsyncEngine)
    reader_session = SqlSession(context.sql)
    reader_session.commit = AsyncMock(side_effect=AssertionError("GET cannot commit"))
    reader_session.flush = AsyncMock(side_effect=AssertionError("GET cannot flush"))
    reader_session.add = Mock(side_effect=AssertionError("GET cannot write"))
    factory = Mock(return_value=reader_session)
    monkeypatch.setattr(api, "WORKSPACE_ID", examples.WORKSPACE)
    monkeypatch.setattr(api, "LOCAL_ACTOR_ID", examples.ACTOR)
    monkeypatch.setattr(service_module, "AsyncSession", factory)
    monkeypatch.setattr(service_module, "datetime", FrozenDatetime)
    application.dependency_overrides[api.get_import_service] = lambda: context.service
    application.dependency_overrides[api.get_read_service] = (
        lambda: service_module.ProductPriceScaleEvidenceReadService(engine)
    )
    context.reader_session = reader_session
    context.reader_factory = factory
    context.engine_mock = engine
    yield application
    application.dependency_overrides.clear()


async def test_import_current_and_exact_original_use_existing_scope_and_no_read_effects(
    app, context
):
    imported = body()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(URL + "/imports", json=imported)
        assert created.status_code == 201, created.text
        result = created.json()
        assert result["manifest_json"] == imported["manifest_json"]
        assert result["document_base64"] == imported["document_base64"]
        assert result["source"]["recorded_by"] == str(examples.ACTOR)
        assert result["verification"] == "MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION"
        context.session.commit.reset_mock()
        app.dependency_overrides[api.get_import_service] = lambda: pytest.fail(
            "GET constructed writer"
        )
        read = await client.get(URL + "/current")
        assert read.status_code == 200, read.text
        evidence = read.json()
        assert evidence["status"] == "AVAILABLE" and evidence["revision_id"] == result["id"]
        assert evidence["known_at"] == evidence["read_at"]
        assert datetime.fromisoformat(evidence["known_at"]) == examples.NOW
        assert "document_base64" not in evidence and "manifest_json" not in evidence
        original = await client.get(URL + f"/revisions/{result['id']}")
        assert original.status_code == 200, original.text
        assert original.json() == result
    assert len(examples.rows(context)) == 1
    context.reader_factory.assert_called_with(
        context.engine_mock, expire_on_commit=False, autoflush=False
    )
    for operation in (
        context.reader_session.commit,
        context.reader_session.flush,
        context.session.commit,
    ):
        operation.assert_not_awaited()
    context.reader_session.add.assert_not_called()
    assert context.reader_session.rollback.await_count == 2
    setup = [
        str(statement)
        for statement in context.reader_session.statements
        if str(statement).startswith("SET")
    ]
    assert (
        setup
        == [
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY",
            "SET LOCAL statement_timeout = '10000ms'",
        ]
        * 2
    )


@pytest.mark.parametrize(
    "change",
    [
        {"confirmation": None},
        {"confirmation": "ACTIVATE_BASELINE"},
        {"workspace_id": str(uuid4())},
        {"recorded_at": examples.NOW.isoformat()},
        {"recorded_by": str(uuid4())},
        {"reviewed_at": "2026-11-16T09:00:00"},
        {"reviewed_at": 1794823200},
        {"retrieved_at": 1794823200},
        {"request_id": "invalid"},
        {"manifest_sha256": "invalid"},
        {"document_sha256": "invalid"},
    ],
)
async def test_invalid_or_unconfirmed_command_never_reaches_storage(app, context, change):
    spy = AsyncMock(side_effect=context.service.record)
    context.service.record = spy
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(URL + "/imports", json=body(**change))
    assert response.status_code == 422, response.text
    spy.assert_not_awaited()
    assert examples.rows(context) == []


@pytest.mark.parametrize("suffix", ["/current", "/revisions/00000000-0000-4000-8000-000000000099"])
@pytest.mark.parametrize(
    "query",
    [
        "known_at=2026-01-01T00%3A00%3A00Z",
        "workspace_id=other",
        "refresh=true",
        "warrant_id=a&warrant_id=b",
    ],
)
async def test_read_does_not_accept_historical_workspace_refresh_or_duplicate_parameters(
    app, context, suffix, query
):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(URL + suffix + "?" + query)
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "PRODUCT_PRICE_SCALE_INVALID"
    context.reader_factory.assert_not_called()


async def test_actor_header_is_bound_and_body_or_query_cannot_override_workspace(app, context):
    actor = uuid4()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            URL + "/imports", json=body(), headers={"X-Actor-ID": str(actor)}
        )
        assert response.status_code == 201, response.text
        assert response.json()["source"]["recorded_by"] == str(actor)
        assert response.json()["workspace_id"] == str(examples.WORKSPACE)
        invalid_actor = await client.post(
            URL + "/imports", json=body(), headers={"X-Actor-ID": "bad"}
        )
        assert invalid_actor.status_code == 422
        query = await client.post(URL + "/imports?workspace_id=foreign", json=body())
        assert query.status_code == 422
    assert len(examples.rows(context)) == 1


async def test_foreign_product_and_unknown_original_are_404_not_missing(app, context):
    first = await examples.record(context)
    foreign = f"/api/v1/warrants/{uuid4()}/price-scale-evidence"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for path in (
            foreign + "/current",
            foreign + f"/revisions/{first.id}",
            URL + f"/revisions/{uuid4()}",
        ):
            response = await client.get(path)
            assert response.status_code == 404, response.text
            assert response.json()["code"] == "PRODUCT_PRICE_SCALE_SCOPE_NOT_FOUND"


async def test_new_revision_and_replay_conflicts_are_409_without_changed_original(app, context):
    imported = body()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post(URL + "/imports", json=imported)
        replay = await client.post(URL + "/imports", json=imported)
        assert replay.status_code == 201 and replay.json() == first.json()
        stale = await client.post(URL + "/imports", json=body())
        assert stale.status_code == 409
        conflict = await client.post(
            URL + "/imports", json=imported | {"review_reference": "Different review"}
        )
        assert conflict.status_code == 409
    assert len(examples.rows(context)) == 1


@pytest.mark.parametrize("failure", ["setup", "current", "original"])
async def test_read_failures_are_503_and_always_end_snapshot_without_writes(
    app, context, monkeypatch, failure
):
    first = await examples.record(context)
    error = DBAPIError("SELECT", {}, Exception("synthetic unavailable"))
    if failure == "setup":
        monkeypatch.setattr(context.reader_session, "execute", AsyncMock(side_effect=error))
    else:
        monkeypatch.setattr(
            service_module.ProductPriceScaleEvidenceReader,
            "revision" if failure == "original" else "current",
            AsyncMock(side_effect=error),
        )
    suffix = f"/revisions/{first.id}" if failure == "original" else "/current"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(URL + suffix)
    assert response.status_code == 503, response.text
    assert response.json()["code"] == "PRODUCT_PRICE_SCALE_READ_UNAVAILABLE"
    context.reader_session.rollback.assert_awaited_once()
    context.reader_session.commit.assert_not_awaited()


async def test_current_get_has_no_write_delete_or_activation_methods(app, context):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            response = await client.request(method, URL + "/current", json={})
            assert response.status_code == 405
    assert examples.rows(context) == []
