"""Registered saved-evidence GET cannot change scope, clocks or owner facts."""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine
from tests.unit.backend.features.position_monitoring import (
    test_hebeltrader_original_bid_service as examples,
)

from app.core.exceptions import register_exception_handlers
from app.features.position_monitoring.api import hebeltrader_original_bid as api
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
    app.dependency_overrides[api.get_original_bid_reader] = lambda: context.reader
    monkeypatch.setattr(api, "WORKSPACE_ID", context.scope["workspace_id"])
    return ASGITransport(app=app)


def path(context):
    return (
        f"/api/v1/position-monitoring/trades/{context.scope['trade_id']}/hebeltrader-original-bid"
    )


async def test_registered_get_preserves_exact_quote_currency_times_and_missing_owner_proofs(
    context, transport
):
    before = deepcopy((context.state.owner, context.state.saved))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            path(context), params={"position_id": str(context.scope["position_id"])}
        )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["definition_version"] == "hebeltrader-original-bid-v1"
    assert result["baseline_id"] == "HEBELTRADER_CONFIRMED_BASELINE"
    assert result["baseline_version"] == "1.0.0"
    assert result["trade_id"] == str(context.scope["trade_id"])
    assert result["position_id"] == str(context.scope["position_id"])
    assert result["economic_basis"]["position"]["open_quantity"] == 80
    assert result["economic_basis"]["position"]["cost_basis"] == "218.0"
    assert result["bid"]["age_seconds"] == "60"
    assert result["bid"]["price_axis"] == "WARRANT_BID"
    assert result["bid"]["maximum_age_seconds"] == 900
    assert result["saved_quote"]["quote"]["original_evidence"]["bid"]["source_field"] == "bid_at"
    assert result["saved_quote"]["provenance"]["stored_at"] is None
    assert result["saved_quote"]["provenance"]["mutable"] is True
    assert result["saved_quote"]["provenance"]["historical_read"] is False
    assert result["product_sessions"]["calendar"]["instrument_kind"] == "WARRANT"
    assert result["underlying_sessions"]["calendar"]["instrument_kind"] == "UNDERLYING"
    assert (
        result["underlying_sessions"]["count"]["evaluated_at"] == result["bid"]["original_bid_at"]
    )
    assert result["underlying_sessions"]["count"]["evaluated_at"] != result["evaluated_at"]
    assert (
        result["product_sessions"]["calendar"]["verification"]
        == "MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION"
    )
    assert result["coverage_status"] == "PARTIAL"
    assert result["operation_status"] == "NOT_ACTIVATED"
    assert result["rule_evaluation_status"] == "B04_B05_B06_B58_NOT_EVALUATED"
    assert result["read_status"] == "READ_ONLY"
    assert len(result["checks"]) == 8
    assert all(item["affected_rules"] == ["B04", "B58"] for item in result["checks"])
    assert before == (context.state.owner, context.state.saved)
    examples.sessions.assert_passive_snapshot(context)


@pytest.mark.parametrize(
    "query",
    [
        "",
        "position_id=invalid",
        "position_id={position}&position_id={position}",
        "position_id={position}&evaluated_at=2026-11-15T18:00:00Z",
        "position_id={position}&known_at=2026-11-15T18:00:00Z",
        "position_id={position}&workspace_id=00000000-0000-4000-8000-000000000099",
    ],
)
async def test_query_cannot_invent_position_workspace_or_historical_clock(
    context, transport, query
):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            path(context) + "?" + query.format(position=context.scope["position_id"])
        )
    assert response.status_code == 422, response.text
    context.owner_read.assert_not_awaited()
    context.quote_read.assert_not_awaited()


async def test_foreign_position_is_404_not_missing_evidence(context, transport):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(path(context), params={"position_id": str(UUID(int=7999))})
    assert response.status_code == 404
    assert response.json()["code"] == "BASELINE_POSITION_NOT_FOUND"
    context.quote_read.assert_not_awaited()


async def test_registered_get_exposes_product_original_revision_without_document_payload(
    context, transport
):
    context.state.price_scale = examples.scales.scale_evidence()
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            path(context), params={"position_id": str(context.scope["position_id"])}
        )
    assert response.status_code == 200, response.text
    result = response.json()
    scale = result["product_price_scale"]
    assert scale["status"] == "DOCUMENTED"
    assert scale["execution_basis_id"] == result["economic_basis"]["basis_id"]
    assert [row["remaining_quantity"] for row in scale["purchases"]] == ["24", "36", "20"]
    assert scale["evidence"]["manifest"]["unit"] == "CURRENCY_PER_WARRANT"
    assert scale["evidence"]["source"]["document_sha256"] == "a" * 64
    assert "document_base64" not in scale["evidence"]
    assert "manifest_json" not in scale["evidence"]
    assert result["implementation_status"] == "F207_3_PRODUCT_PRICE_SCALE_EVIDENCE_ONLY"
    assert result["coverage_status"] == "PARTIAL"
    examples.sessions.assert_passive_snapshot(context)


async def test_product_source_integrity_error_is_503_without_leaking_document(context, transport):
    secret = "Synthetic private original-document text"
    context.scale_read.side_effect = ValueError(secret)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            path(context), params={"position_id": str(context.scope["position_id"])}
        )
    assert response.status_code == 503
    assert secret not in response.text
    assert response.json()["code"] == "HEBELTRADER_ORIGINAL_BID_READ_UNAVAILABLE"
    examples.sessions.assert_passive_snapshot(context)


@pytest.mark.parametrize("integrity_error", [False, True])
async def test_database_or_payload_error_is_503_and_not_missing_data(
    context, transport, integrity_error
):
    secret = "Synthetic private SQL, original document and credentials"
    context.quote_read.side_effect = (
        ValueError(secret) if integrity_error else DBAPIError("SELECT", {}, Exception(secret))
    )
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            path(context), params={"position_id": str(context.scope["position_id"])}
        )
    assert response.status_code == 503, response.text
    assert response.json()["code"] == "HEBELTRADER_ORIGINAL_BID_READ_UNAVAILABLE"
    assert "kein Nachweis" in response.json()["message"]
    assert secret not in response.text
    context.current_read.assert_not_awaited()
    examples.sessions.assert_passive_snapshot(context)


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
async def test_read_route_exposes_no_command_method(context, transport, method):
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.request(
            method,
            path(context),
            params={"position_id": str(context.scope["position_id"])},
            json={"activate": True},
        )
    assert response.status_code == 405
    context.owner_read.assert_not_awaited()


async def test_dependency_only_wraps_existing_engine():
    engine = Mock(spec=AsyncEngine)
    reader = api.get_original_bid_reader(SimpleNamespace(engine=engine))
    assert reader._engine is engine
    engine.connect.assert_not_called()
