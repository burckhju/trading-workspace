"""F207-2 transport boundaries over synthetic, isolated owner doubles."""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import TypeAdapter
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

import app.features.position_monitoring.service.hebeltrader_targets as service_module
from app.core.exceptions import register_exception_handlers
from app.database.dependencies import get_database_manager, get_database_session
from app.features.position_monitoring.api.hebeltrader_targets import (
    LOCAL_ACTOR_ID,
    WORKSPACE_ID,
    get_target_reader,
    get_target_service,
    router,
)
from app.features.position_monitoring.domain.hebeltrader_targets import (
    TargetComparisonQualification,
)
from app.features.position_monitoring.persistence.hebeltrader_targets import (
    TargetAssessmentRecord,
)
from app.features.position_monitoring.service.hebeltrader_target_contracts import (
    HebeltraderTargetsReport,
    OrientationView,
    ProtectionBasisView,
    TargetAssessmentCommand,
    TargetAssessmentView,
    TargetEvidenceView,
    TargetInputsView,
    TargetView,
)
from app.features.position_monitoring.service.hebeltrader_targets import (
    HebeltraderTargetReader,
    HebeltraderTargetService,
    target_error,
)

NOW = datetime(2026, 11, 14, 10, tzinfo=UTC)
TRADE_ID = UUID(int=8101)
POSITION_ID = UUID(int=8102)
ASSESSMENT_ID = UUID(int=8103)
SOURCE_A = UUID(int=8104)
SOURCE_B = UUID(int=8105)
REQUEST_ID = UUID(int=8106)
ACTOR_ID = UUID(int=8107)
BASIS_ID = "a" * 64
PREFIX = "/api/v1/position-monitoring"
BASE = f"{PREFIX}/trades/{TRADE_ID}/hebeltrader-targets"


def report():
    assessment = TargetAssessmentView(
        id=ASSESSMENT_ID,
        recorded_at=NOW,
        basis_id=BASIS_ID,
        source_version_id=SOURCE_B,
        previous_assessment_id=None,
        targets=(
            TargetView(
                target="Z1",
                status="REVIEW_REQUIRED",
                threshold=Decimal("110.1234567891"),
                currency="USD",
                event_id=UUID(int=8110),
                proof_source_version_id=SOURCE_A,
                proof_scale_reference="synthetic-original-A",
                detail="Historischen Treffer aus Quelle A mit geänderter Grundlage prüfen.",
                reasons=("Die historische Quelle hat sich geändert.",),
                evidence=TargetEvidenceView(
                    trading_date=date(2026, 9, 9),
                    interval_start=datetime(2026, 9, 9, tzinfo=UTC),
                    interval_end=datetime(2026, 9, 10, tzinfo=UTC),
                    high=Decimal("111.1234567891"),
                    source_row_id=UUID(int=8111),
                    source_fingerprint="b" * 64,
                    provider="SYNTHETIC",
                    provider_symbol="TEST.US",
                    listing_id=UUID(int=8112),
                    time_precision="DATE_ONLY",
                    detected_at=NOW,
                ),
            ),
            TargetView(
                target="Z2",
                status="NOT_PROVEN",
                threshold=Decimal("120.1234567891"),
                currency="USD",
                event_id=None,
                proof_source_version_id=None,
                proof_scale_reference=None,
                detail="Kein Treffer in den verfügbaren Belegen, keine Entwarnung.",
                reasons=(),
                evidence=None,
            ),
        ),
        orientation=OrientationView(
            status="NOT_ASSESSABLE",
            original_quantity=7,
            assigned_sold_quantity=2,
            detail="Ursprünglichen Treffer klären; konkrete Verkaufsmengen bleiben eigene Fakten.",
        ),
        protection_basis=ProtectionBasisView(
            status="NOT_ASSESSABLE",
            personal_underlying_entry=Decimal("100.9876543219"),
            currency="USD",
            detail="Nur Prüfgrundlage, kein bekanntgegebener Schutzvorschlag.",
        ),
    )
    return HebeltraderTargetsReport(
        trade_id=TRADE_ID,
        position_id=POSITION_ID,
        current_basis_id=BASIS_ID,
        currentness="CURRENT",
        position_state="OPEN",
        read_started_at=NOW,
        read_completed_at=NOW,
        assessment_count=1,
        inputs=TargetInputsView(
            source_version_id=SOURCE_B,
            source_scale_reference="synthetic-original-B",
            price_history_fingerprint="c" * 64,
            listing_binding_fingerprint="d" * 64,
            qualification_reusable=False,
            available_price_rows=2,
            issues=("Quelle B ist nicht die ursprüngliche Zielquelle A.",),
        ),
        latest_assessment=assessment,
    )


def record():
    return TargetAssessmentRecord(
        id=ASSESSMENT_ID,
        workspace_id=WORKSPACE_ID,
        trade_id=TRADE_ID,
        position_id=POSITION_ID,
        product_id=UUID(int=8113),
        underlying_id=UUID(int=8114),
        source_version_id=SOURCE_B,
        evidence_revision_id=UUID(int=8115),
        previous_assessment_id=None,
        definition_version="hebeltrader-target-evidence-v1",
        baseline_id="HEBELTRADER_CONFIRMED_BASELINE",
        baseline_version="1.0.0",
        basis_id=BASIS_ID,
        input_fingerprint="e" * 64,
        recorded_at=NOW,
        recorded_by=ACTOR_ID,
        inputs={"historical_source_version_id": str(SOURCE_A)},
        result=TypeAdapter(TargetAssessmentView).dump_python(
            report().latest_assessment, mode="json"
        ),
    )


def application(reader=None, service=None):
    app = FastAPI()
    app.include_router(router, prefix=PREFIX)
    register_exception_handlers(app)

    def forbidden_reader():
        raise AssertionError("POST constructed the standalone GET reader")

    def forbidden_command():
        raise AssertionError("GET constructed an assessment command dependency")

    def forbidden_database():
        raise AssertionError("synthetic API test touched an actual database or container")

    app.dependency_overrides[get_target_reader] = (
        (lambda: reader) if reader is not None else forbidden_reader
    )
    app.dependency_overrides[get_target_service] = (
        (lambda: service) if service is not None else forbidden_command
    )
    app.dependency_overrides[get_database_session] = forbidden_database
    app.dependency_overrides[get_database_manager] = forbidden_database
    return app


async def get(reader, suffix="", query=None):
    async with AsyncClient(
        transport=ASGITransport(app=application(reader=reader)), base_url="http://test"
    ) as client:
        return await client.get(
            BASE + suffix,
            params=[("position_id", str(POSITION_ID))] if query is None else query,
        )


def command_body():
    return {
        "position_id": str(POSITION_ID),
        "request_id": str(REQUEST_ID),
        "expected_basis_id": BASIS_ID,
        "expected_assessment_id": None,
        "confirmation": "ASSESS_SAVED_HEBELTRADER_EVIDENCE",
    }


def qualification_body():
    return {
        "history_fingerprint": "c" * 64,
        "listing_fingerprint": "d" * 64,
        "source_version_id": str(SOURCE_B),
        "source_scale_reference": "synthetic-original-B",
        "evidence_reference": "synthetic-review-reference",
        "confirmation": "CONFIRM_HISTORICAL_LISTING_AND_UNCHANGED_ORIGINAL_SCALE",
    }


async def post(service, body=None, headers=None):
    async with AsyncClient(
        transport=ASGITransport(app=application(service=service)), base_url="http://test"
    ) as client:
        return await client.post(
            BASE + "/assessments", json=command_body() if body is None else body, headers=headers
        )


async def test_get_uses_only_reader_and_preserves_decimals_day_precision_and_original_provenance():
    reader = AsyncMock(spec=HebeltraderTargetReader)
    reader.read.return_value = report()
    response = await get(reader)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["trade_id"] == str(TRADE_ID)
    assert body["position_id"] == str(POSITION_ID)
    assert body["definition_version"] == "hebeltrader-targets-v1"
    assert body["baseline_id"] == "HEBELTRADER_CONFIRMED_BASELINE"
    assert body["baseline_version"] == "1.0.0"
    assert body["implementation_status"] == "F207_2_TARGET_HISTORY_ONLY"
    assert body["operation_status"] == "NOT_ACTIVATED"
    assert body["read_started_at"] == body["read_completed_at"] == "2026-11-14T10:00:00Z"
    assessment = body["latest_assessment"]
    target = assessment["targets"][0]
    assert target["threshold"] == "110.1234567891"
    assert target["currency"] == "USD"
    assert target["proof_source_version_id"] == str(SOURCE_A)
    assert target["proof_scale_reference"] == "synthetic-original-A"
    assert assessment["source_version_id"] == str(SOURCE_B)
    assert target["evidence"]["high"] == "111.1234567891"
    assert target["evidence"]["trading_date"] == "2026-09-09"
    assert target["evidence"]["time_precision"] == "DATE_ONLY"
    assert target["evidence"]["detected_at"] == "2026-11-14T10:00:00Z"
    assert assessment["orientation"]["proportion"] == "0.5"
    assert assessment["orientation"]["original_quantity"] == 7
    assert assessment["orientation"]["assigned_sold_quantity"] == 2
    assert assessment["protection_basis"]["personal_underlying_entry"] == "100.9876543219"
    reader.read.assert_awaited_once_with(WORKSPACE_ID, TRADE_ID, POSITION_ID)
    reader.assessment.assert_not_awaited()


@pytest.mark.parametrize("state", ["OPEN", "CLOSED", "CANCELLED"])
async def test_get_preserves_owner_position_state_and_historical_review_without_commands(state):
    reader = AsyncMock(spec=HebeltraderTargetReader)
    reader.read.return_value = replace(report(), position_state=state)
    response = await get(reader)
    assert response.status_code == 200
    assert response.json()["position_state"] == state
    assert response.json()["latest_assessment"]["targets"][0]["status"] == "REVIEW_REQUIRED"


async def test_get_keeps_absent_assessment_distinct_from_completed_or_clear_evaluation():
    reader = AsyncMock(spec=HebeltraderTargetReader)
    reader.read.return_value = replace(
        report(), latest_assessment=None, assessment_count=0, currentness="NO_ASSESSMENT"
    )
    response = await get(reader)
    assert response.status_code == 200
    assert response.json()["latest_assessment"] is None
    assert response.json()["currentness"] == "NO_ASSESSMENT"
    assert response.json()["assessment_count"] == 0


async def test_historical_assessment_get_retains_exact_record_and_uses_only_history_reader():
    reader = AsyncMock(spec=HebeltraderTargetReader)
    reader.assessment.return_value = record()
    response = await get(reader, f"/assessments/{ASSESSMENT_ID}")
    assert response.status_code == 200, response.text
    assert response.json()["id"] == str(ASSESSMENT_ID)
    assert response.json()["result"]["targets"][0]["threshold"] == "110.1234567891"
    assert response.json()["recorded_by"] == str(ACTOR_ID)
    reader.assessment.assert_awaited_once_with(WORKSPACE_ID, TRADE_ID, POSITION_ID, ASSESSMENT_ID)
    reader.read.assert_not_awaited()


@pytest.mark.parametrize("suffix", ["", f"/assessments/{ASSESSMENT_ID}"])
@pytest.mark.parametrize(
    "query",
    [
        [],
        [("position_id", "")],
        [("position_id", "not-a-uuid")],
        [("position_id", str(POSITION_ID)), ("position_id", str(POSITION_ID))],
        [("position_id", str(POSITION_ID)), ("position_id", str(UUID(int=8999)))],
    ],
)
async def test_both_gets_require_one_unambiguous_valid_position_before_any_owner_read(
    suffix, query
):
    reader = AsyncMock(spec=HebeltraderTargetReader)
    response = await get(reader, suffix, query)
    assert response.status_code == 422, response.text
    reader.read.assert_not_awaited()
    reader.assessment.assert_not_awaited()


@pytest.mark.parametrize(
    "suffix,method", [("", "read"), (f"/assessments/{ASSESSMENT_ID}", "assessment")]
)
async def test_scope_error_stays_an_owner_error_instead_of_an_empty_success(suffix, method):
    reader = AsyncMock(spec=HebeltraderTargetReader)
    getattr(reader, method).side_effect = target_error(
        "BASELINE_POSITION_NOT_FOUND", "Position passt nicht zu Trade und Workspace.", 404
    )
    response = await get(reader, suffix)
    assert response.status_code == 404
    assert response.json()["code"] == "BASELINE_POSITION_NOT_FOUND"
    assert "latest_assessment" not in response.json()


@pytest.mark.parametrize(
    "suffix,method", [("", "read"), (f"/assessments/{ASSESSMENT_ID}", "assessment")]
)
async def test_technical_read_failure_is_scrubbed_503_and_never_an_empty_or_clear_history(
    suffix, method
):
    reader = AsyncMock(spec=HebeltraderTargetReader)
    getattr(reader, method).side_effect = DBAPIError("private SQL", {}, Exception("private token"))
    response = await get(reader, suffix)
    assert response.status_code == 503
    assert response.json()["code"] == "HEBELTRADER_TARGET_READ_UNAVAILABLE"
    assert "private" not in response.text
    assert "latest_assessment" not in response.json()
    assert "keine Entwarnung" in response.json()["message"]


@pytest.mark.parametrize("previous_id", [None, ASSESSMENT_ID])
@pytest.mark.parametrize("actor", [None, ACTOR_ID])
async def test_explicit_post_preserves_the_request_id_cas_basis_predecessor_and_actor(
    previous_id, actor
):
    service = AsyncMock(spec=HebeltraderTargetService)
    service.assess.return_value = report()
    body = command_body()
    body["expected_assessment_id"] = str(previous_id) if previous_id else None
    response = await post(service, body, {"X-Actor-ID": str(actor)} if actor else None)
    assert response.status_code == 200, response.text
    assert response.json()["operation_status"] == "NOT_ACTIVATED"
    service.assess.assert_awaited_once_with(
        workspace_id=WORKSPACE_ID,
        trade_id=TRADE_ID,
        command=TargetAssessmentCommand(
            position_id=POSITION_ID,
            request_id=REQUEST_ID,
            expected_basis_id=BASIS_ID,
            expected_assessment_id=previous_id,
            qualification=None,
        ),
        actor=actor or LOCAL_ACTOR_ID,
    )


async def test_optional_price_qualification_requires_and_passes_its_own_explicit_confirmation():
    service = AsyncMock(spec=HebeltraderTargetService)
    service.assess.return_value = report()
    body = {**command_body(), "qualification": qualification_body()}
    response = await post(service, body)
    assert response.status_code == 200, response.text
    assert service.assess.await_args.kwargs[
        "command"
    ].qualification == TargetComparisonQualification(
        history_fingerprint="c" * 64,
        listing_fingerprint="d" * 64,
        source_version_id=SOURCE_B,
        source_scale_reference="synthetic-original-B",
        evidence_reference="synthetic-review-reference",
    )
    service.assess.assert_awaited_once()


@pytest.mark.parametrize(
    "mutation",
    [
        lambda body: body.pop("confirmation"),
        lambda body: body.update(confirmation="CONFIRM_ORDER"),
        lambda body: body.pop("request_id"),
        lambda body: body.update(request_id="not-a-uuid"),
        lambda body: body.update(position_id="not-a-position"),
        lambda body: body.pop("expected_basis_id"),
        lambda body: body.update(expected_basis_id="not-a-basis"),
        lambda body: body.pop("expected_assessment_id"),
        lambda body: body.update(expected_assessment_id=False),
        lambda body: body.update(activate_baseline=True),
        lambda body: body.update(send_notification=True),
        lambda body: body.update(order_quantity=50),
        lambda body: body.update(observed_at="2026-09-09T12:00:00Z"),
        lambda body: body["qualification"].pop("confirmation"),
        lambda body: body["qualification"].update(confirmation="ASSESS_SAVED_HEBELTRADER_EVIDENCE"),
        lambda body: body["qualification"].update(history_fingerprint="stale"),
        lambda body: body["qualification"].update(listing_fingerprint="G" * 64),
        lambda body: body["qualification"].update(source_version_id="current"),
        lambda body: body["qualification"].update(source_scale_reference="  "),
        lambda body: body["qualification"].update(evidence_reference="  "),
        lambda body: body["qualification"].update(automatic=True),
    ],
)
async def test_invalid_or_unconfirmed_commands_never_reach_the_service(mutation):
    service = AsyncMock(spec=HebeltraderTargetService)
    body = {**command_body(), "qualification": qualification_body()}
    mutation(body)
    response = await post(service, body)
    assert response.status_code == 422, response.text
    service.assess.assert_not_awaited()


async def test_cas_conflict_is_returned_without_retry_or_conversion_to_a_successful_read():
    service = AsyncMock(spec=HebeltraderTargetService)
    service.assess.side_effect = target_error(
        "HEBELTRADER_INPUTS_CHANGED", "Beleggrundlage wurde geändert.", 409
    )
    response = await post(service)
    assert response.status_code == 409
    assert response.json()["code"] == "HEBELTRADER_INPUTS_CHANGED"
    assert "latest_assessment" not in response.json()
    service.assess.assert_awaited_once()


async def test_post_database_error_stays_unconfirmed_without_retry_or_private_detail():
    service = AsyncMock(spec=HebeltraderTargetService)
    service.assess.side_effect = DBAPIError("private SQL", {}, Exception("private token"))
    response = await post(service)
    assert response.status_code == 503
    assert response.json()["code"] == "HEBELTRADER_TARGET_WRITE_UNCONFIRMED"
    assert "private" not in response.text
    assert "nicht bestätigt" in response.json()["message"]
    service.assess.assert_awaited_once()


@pytest.mark.parametrize("failure", [False, True])
async def test_reader_snapshot_is_repeatable_read_only_without_autoflush_and_always_rolls_back(
    monkeypatch, failure
):
    session = AsyncMock(spec=AsyncSession)
    session.__aenter__.return_value = session
    constructor = Mock(return_value=session)
    monkeypatch.setattr(service_module, "AsyncSession", constructor)
    engine = object()
    reader = HebeltraderTargetReader(engine)
    if failure:
        with pytest.raises(ValueError, match="synthetic read failure"):
            async with reader._snapshot():
                raise ValueError("synthetic read failure")
    else:
        async with reader._snapshot() as actual:
            assert actual is session
    constructor.assert_called_once_with(engine, expire_on_commit=False, autoflush=False)
    assert [str(call.args[0]) for call in session.execute.await_args_list] == [
        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY",
        "SET LOCAL statement_timeout = '10000ms'",
    ]
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()
    session.flush.assert_not_awaited()
    session.add.assert_not_called()
