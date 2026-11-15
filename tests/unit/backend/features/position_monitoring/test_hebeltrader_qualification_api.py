"""Qualification reads and explicit existing commands across the HTTP boundary."""

from copy import deepcopy
from dataclasses import replace
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import DBAPIError
from tests.unit.backend.features.position_monitoring import (
    test_hebeltrader_target_service as service_examples,
)
from tests.unit.backend.features.position_monitoring import (
    test_hebeltrader_targets_api as existing,
)

from app.features.position_monitoring.api import hebeltrader_targets as api
from app.features.position_monitoring.service.hebeltrader_targets import (
    HebeltraderTargetReader,
    target_error,
)

case = service_examples.case
context = service_examples.context
no_provider_access = service_examples.no_provider_access
pytestmark = pytest.mark.asyncio
REQUEST_ID = UUID(int=1200)
READS = (
    ("/qualification-preview", "qualification_preview"),
    (f"/requests/{REQUEST_ID}", "request_status"),
)


def preview_command(preview, *, request_id=REQUEST_ID):
    report = preview["report"]
    return {
        "position_id": report["position_id"],
        "request_id": str(request_id),
        "expected_basis_id": report["current_basis_id"],
        "expected_assessment_id": (
            report["latest_assessment"]["id"] if report["latest_assessment"] else None
        ),
        "confirmation": "ASSESS_SAVED_HEBELTRADER_EVIDENCE",
        "qualification": {
            **preview["qualification_binding"],
            "evidence_reference": "Synthetic original listing archive / page 7",
            "confirmation": "CONFIRM_HISTORICAL_LISTING_AND_UNCHANGED_ORIGINAL_SCALE",
        },
    }


@pytest.fixture
def transport(context, monkeypatch):
    # The application is local-workspace scoped; synthetic owner facts use their own UUID.
    monkeypatch.setattr(api, "WORKSPACE_ID", context.scope["workspace_id"])
    return ASGITransport(app=existing.application(reader=context.reader, service=context.service))


def path(context):
    return f"/api/v1/position-monitoring/trades/{context.scope['trade_id']}/hebeltrader-targets"


async def test_preview_to_existing_post_and_receipt_needs_only_explicit_user_confirmation(
    context, transport
):
    before = deepcopy((context.state.records, context.state.receipts))
    query = {"position_id": str(context.scope["position_id"])}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(path(context) + "/qualification-preview", params=query)
        assert response.status_code == 200, response.text
        preview = response.json()
        assert preview["operation_status"] == "READ_ONLY"
        assert preview["report"]["latest_assessment"] is None
        assert preview["readiness"]["status"] == "REVIEWABLE"
        assert preview["qualification"]["status"] == "MISSING"
        status = await client.get(path(context) + f"/requests/{REQUEST_ID}", params=query)
        assert status.status_code == 200, status.text
        unknown = status.json()
        assert unknown["status"] == "UNKNOWN"
        assert unknown["assessment"] is unknown["qualification"] is unknown["recorded_at"] is None
        assert (context.state.records, context.state.receipts) == before
        context.writer.commit.assert_not_awaited()

        body = preview_command(preview)
        saved = await client.post(path(context) + "/assessments", json=body)
        assert saved.status_code == 200, saved.text
        assert saved.json()["latest_assessment"]["targets"][0]["status"] == "PROVEN"
        after_command = deepcopy((context.state.records, context.state.receipts))
        status = await client.get(path(context) + f"/requests/{REQUEST_ID}", params=query)
        assert status.status_code == 200, status.text
        recorded = status.json()
        assert recorded["status"] == "RECORDED"
        assert recorded["operation_status"] == "READ_ONLY"
        assert recorded["assessment"] == saved.json()["latest_assessment"]
        assert (
            recorded["qualification"]["evidence_reference"]
            == body["qualification"]["evidence_reference"]
        )
        assert recorded["recorded_at"] == "2026-11-14T10:00:00Z"
        reread = await client.get(path(context) + "/qualification-preview", params=query)
        assert reread.status_code == 200, reread.text
        assert reread.json()["qualification"]["status"] == "REUSABLE"
        assert reread.json()["report"]["operation_status"] == "NOT_ACTIVATED"
        assert (context.state.records, context.state.receipts) == after_command
        context.writer.commit.assert_awaited_once()


async def test_preview_serializes_exact_original_values_and_distinct_time_and_scale_axes(
    context, monkeypatch
):
    context.state.history = replace(
        context.state.history,
        rows=(replace(context.state.history.rows[0], high=Decimal("120.1234567891")),),
    )
    monkeypatch.setattr(api, "WORKSPACE_ID", context.scope["workspace_id"])
    # GET must never request the writer dependency, including when no receipt exists.
    app = existing.application(reader=context.reader)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            path(context) + "/qualification-preview",
            params={"position_id": str(context.scope["position_id"])},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    row = body["history"]["rows"][0]
    assert row["high"] == "120.1234567891"
    assert row["time_precision"] == "DATE_ONLY"
    assert row["price_basis"] == "UNDERLYING"
    assert row["interval_basis"] == "LOCAL_CALENDAR_DAY_NOT_VERIFIED_SESSION"
    assert row["interval_start"] == "2026-08-05T22:00:00Z"
    assert row["interval_end"] == "2026-08-06T22:00:00Z"
    assert row["retrieved_at"] == "2026-11-12T10:00:00Z"
    assert row["source_updated_at"] == "2026-11-11T10:00:00Z"
    assert row["provider"] == "SYNTHETIC"
    assert body["source"]["content_hash"] == context.state.owner.coverage.source.content_hash
    assert body["source"]["source_version_id"] == body["qualification_binding"]["source_version_id"]
    assert body["source"]["time_precision"] == "DATE_ONLY"
    assert body["source_scale"]["scope"] == "SOURCE_AND_PURCHASE_EVIDENCE_ONLY"
    assert body["source_scale"]["market_observations_verified"] is False
    assert body["history"]["calendar_coverage"] == "NOT_ASSESSED"
    assert body["qualification"]["origin"] == "USER_DECLARATION_NOT_INDEPENDENT_VERIFICATION"
    assert body["report"]["latest_assessment"] is None


@pytest.mark.parametrize("suffix,method", READS)
@pytest.mark.parametrize(
    "query",
    [
        [],
        [("position_id", "not-a-position")],
        [("position_id", str(existing.POSITION_ID)), ("position_id", str(existing.POSITION_ID))],
        [("position_id", str(existing.POSITION_ID)), ("position_id", str(UUID(int=1201)))],
    ],
)
async def test_new_reads_require_one_unambiguous_position_before_any_reader_call(
    suffix, method, query
):
    reader = AsyncMock(spec=HebeltraderTargetReader)
    response = await existing.get(reader, suffix=suffix, query=query)
    assert response.status_code == 422, response.text
    reader.qualification_preview.assert_not_awaited()
    reader.request_status.assert_not_awaited()


@pytest.mark.parametrize("suffix,method", READS)
async def test_new_reads_preserve_scope_not_found_without_converting_it_to_unknown(suffix, method):
    reader = AsyncMock(spec=HebeltraderTargetReader)
    getattr(reader, method).side_effect = target_error(
        "BASELINE_POSITION_NOT_FOUND", "Position passt nicht zu Trade und Workspace.", 404
    )
    response = await existing.get(reader, suffix=suffix)
    assert response.status_code == 404
    assert response.json()["code"] == "BASELINE_POSITION_NOT_FOUND"
    assert "status" not in response.json()
    assert "assessment" not in response.json()


@pytest.mark.parametrize("suffix,method", READS)
async def test_new_read_database_errors_are_scrubbed_without_false_unknown_or_safe_result(
    suffix, method
):
    reader = AsyncMock(spec=HebeltraderTargetReader)
    getattr(reader, method).side_effect = DBAPIError("private SQL", {}, Exception("private token"))
    response = await existing.get(reader, suffix=suffix)
    assert response.status_code == 503
    assert response.json()["code"] == "HEBELTRADER_TARGET_READ_UNAVAILABLE"
    assert "private" not in response.text
    assert "status" not in response.json()
    assert "assessment" not in response.json()


async def test_malformed_request_identifier_never_reaches_receipt_lookup():
    reader = AsyncMock(spec=HebeltraderTargetReader)
    response = await existing.get(reader, suffix="/requests/not-a-request")
    assert response.status_code == 422, response.text
    reader.request_status.assert_not_awaited()


async def test_inconsistent_saved_receipt_is_an_unavailable_read_not_unknown_or_confirmed():
    reader = AsyncMock(spec=HebeltraderTargetReader)
    reader.request_status.side_effect = target_error(
        "HEBELTRADER_REQUEST_READ_INCONSISTENT",
        "Der gespeicherte Prüfvorgang konnte nicht vollständig gelesen werden.",
        503,
    )
    response = await existing.get(reader, suffix=f"/requests/{REQUEST_ID}")
    assert response.status_code == 503
    assert response.json()["code"] == "HEBELTRADER_REQUEST_READ_INCONSISTENT"
    assert "status" not in response.json()
