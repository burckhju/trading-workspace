"""Registered session GET keeps server time, position scope and failure semantics."""

from copy import deepcopy
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine
from tests.unit.backend.features.position_monitoring import (
    test_hebeltrader_sessions_service as examples,
)

from app.core.exceptions import register_exception_handlers
from app.features.position_monitoring.api import hebeltrader_sessions as api
from app.features.position_monitoring.api import router

case = examples.case
context = examples.context
no_provider_access = examples.no_provider_access
pytestmark = pytest.mark.asyncio


@pytest.fixture
def transport(context, monkeypatch):
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(router)
    app.dependency_overrides[api.get_session_reader] = lambda: context.reader
    monkeypatch.setattr(api, "WORKSPACE_ID", context.scope["workspace_id"])
    return ASGITransport(app=app)


def path(context):
    return f"/api/v1/position-monitoring/trades/{context.scope['trade_id']}/hebeltrader-sessions"


async def test_registered_get_preserves_provenance_precision_and_inactive_rule_status(
    context, transport
):
    before = deepcopy(context.state.owner)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            path(context), params={"position_id": str(context.scope["position_id"])}
        )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["position_id"] == str(context.scope["position_id"])
    assert result["trade_id"] == str(context.scope["trade_id"])
    assert result["definition_version"] == "hebeltrader-sessions-v1"
    assert result["baseline_id"] == "HEBELTRADER_CONFIRMED_BASELINE"
    assert result["baseline_version"] == "1.0.0"
    assert result["implementation_status"] == "F207_3_SESSION_EVIDENCE_AND_COUNT_ONLY"
    assert result["operation_status"] == "NOT_ACTIVATED"
    assert result["rule_evaluation_status"] == "B04_B05_B06_B58_NOT_EVALUATED"
    assert result["read_status"] == result["calendar"]["operation_status"] == "READ_ONLY"
    assert (
        result["calendar"]["verification"] == "MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION"
    )
    assert result["calendar"]["source"]["published_at"] is None
    assert result["calendar"]["source"]["published_on"] == "2026-08-03"
    assert result["calendar"]["source"]["reviewed_at"] != result["calendar"]["recorded_at"]
    assert result["calendar"]["source"]["manifest_sha256"] == "b" * 64
    assert result["calendar"]["source"]["document_sha256"] == "c" * 64
    assert (
        result["calendar"]["known_at"] == result["count"]["evaluated_at"] == result["evaluated_at"]
    )
    assert result["entry"]["executed_on"] is None
    assert result["entry"]["time_precision"] == "EXACT"
    assert result["count"]["completed_sessions"] >= 20
    assert result["count"]["threshold_reached"] is True
    assert result["period"]["days"][0]["source_reference"].startswith("Synthetic original calendar")
    assert context.state.owner == before
    examples.assert_passive_snapshot(context)


@pytest.mark.parametrize(
    "query",
    [
        "",
        "position_id=invalid",
        "position_id={position}&position_id={position}",
        "position_id={position}&known_at=2026-11-15T18:00:00Z",
        "position_id={position}&workspace_id=00000000-0000-4000-8000-000000000099",
    ],
)
async def test_query_cannot_invent_position_workspace_or_historical_evaluation_time(
    context, transport, query
):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            path(context) + "?" + query.format(position=context.scope["position_id"])
        )
    assert response.status_code == 422, response.text
    context.owner_read.assert_not_awaited()
    context.current_read.assert_not_awaited()


async def test_foreign_position_is_not_returned_as_a_missing_calendar(context, transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(path(context), params={"position_id": str(UUID(int=7899))})
    assert response.status_code == 404
    assert response.json()["code"] == "BASELINE_POSITION_NOT_FOUND"
    context.current_read.assert_not_awaited()


@pytest.mark.parametrize("integrity_error", [False, True])
async def test_database_or_original_integrity_failure_is_503_not_an_unassessable_report(
    context, transport, integrity_error
):
    message = "Synthetic private SQL, original document bytes and credentials"
    context.current_read.side_effect = (
        ValueError(message) if integrity_error else DBAPIError("SELECT", {}, Exception(message))
    )
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            path(context), params={"position_id": str(context.scope["position_id"])}
        )
    assert response.status_code == 503, response.text
    assert response.json()["code"] == "HEBELTRADER_SESSION_READ_UNAVAILABLE"
    assert "kein Nachweis" in response.json()["message"]
    assert message not in response.text
    context.period_read.assert_not_awaited()
    examples.assert_passive_snapshot(context)


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
async def test_passive_position_path_has_no_command_method(context, transport, method):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.request(
            method,
            path(context),
            params={"position_id": str(context.scope["position_id"])},
            json={"evaluated_at": (examples.NOW + timedelta(days=1)).isoformat()},
        )
    assert response.status_code == 405
    context.owner_read.assert_not_awaited()


async def test_dependency_constructs_reader_over_existing_engine_without_opening_a_session():
    engine = Mock(spec=AsyncEngine)
    reader = api.get_session_reader(SimpleNamespace(engine=engine))
    assert reader._engine is engine
    engine.connect.assert_not_called()
