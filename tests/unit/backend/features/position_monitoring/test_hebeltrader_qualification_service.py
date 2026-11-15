"""Saved comparison previews and exact receipts over real synthetic owner facts."""

from copy import deepcopy
from dataclasses import asdict, replace
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock
from uuid import UUID

import pytest
from tests.unit.backend.features.position_monitoring import (
    test_hebeltrader_target_service as existing,
)

from app.core.exceptions import ApplicationError
from app.features.learning.application.hebeltrader_source_reader import HebeltraderSourceEvidence
from app.features.position_monitoring.domain.hebeltrader_targets import (
    TargetComparisonQualification,
)
from app.features.position_monitoring.service import hebeltrader_targets as module
from app.features.position_monitoring.service.hebeltrader_target_contracts import (
    TargetAssessmentCommand,
)
from app.features.product.domain.models import OptionDirection
from app.features.trade_position.domain.enums import ExecutionSide

case = existing.case
context = existing.context
no_provider_access = existing.no_provider_access
pytestmark = pytest.mark.asyncio
NOW = existing.NOW


def command_from_preview(preview, *, number=1100, reference="Synthetic listing archive page 7"):
    binding = preview.qualification_binding
    assert binding is not None
    return TargetAssessmentCommand(
        position_id=preview.report.position_id,
        request_id=UUID(int=number),
        expected_basis_id=preview.report.current_basis_id,
        expected_assessment_id=(
            preview.report.latest_assessment.id if preview.report.latest_assessment else None
        ),
        qualification=TargetComparisonQualification(
            **asdict(binding), evidence_reference=reference
        ),
    )


def assert_read_boundary(context):
    context.session_factory.assert_called_once_with(
        context.engine, expire_on_commit=False, autoflush=False
    )
    assert [str(item.args[0]) for item in context.reader_session.execute.await_args_list] == [
        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY",
        "SET LOCAL statement_timeout = '10000ms'",
    ]
    context.reader_session.rollback.assert_awaited_once_with()
    for session in (context.writer, context.reader_session):
        session.commit.assert_not_awaited()
        for operation in ("add", "add_all", "delete", "flush"):
            getattr(session, operation).assert_not_called()
    context.read_repository.add.assert_not_awaited()
    context.read_repository.receipt.assert_not_awaited()
    context.repository.add.assert_not_awaited()
    context.repository.receipt.assert_not_awaited()


async def test_preview_reads_one_snapshot_without_assessing_or_changing_any_owner(
    context, monkeypatch
):
    forbidden = Mock(side_effect=AssertionError("Preview must not evaluate target hits"))
    monkeypatch.setattr(module, "evaluate_hebeltrader_targets", forbidden)
    monkeypatch.setattr(
        context.reader,
        "read",
        Mock(side_effect=AssertionError("Preview report needs the same input snapshot")),
    )
    before = deepcopy((asdict(context.state.owner), asdict(context.state.history)))
    preview = await context.reader.qualification_preview(**context.scope)

    assert preview.report.assessment_count == 0
    assert preview.report.latest_assessment is None
    assert preview.report.currentness == "NO_ASSESSMENT"
    assert preview.report.operation_status == "NOT_ACTIVATED"
    assert preview.operation_status == "READ_ONLY"
    assert preview.readiness.status == "REVIEWABLE"
    assert preview.readiness.usable_row_count == 1
    assert preview.qualification.status == "MISSING"
    assert preview.qualification.value is None
    assert preview.source == context.state.owner.coverage.source
    assert preview.history == context.state.history
    assert preview.history.rows[0].high == Decimal("120")
    assert preview.history.rows[0].time_precision == "DATE_ONLY"
    assert preview.history.binding.provenance == "CURRENT_REFERENCE_NOT_HISTORICALLY_VERIFIED"
    assert preview.source_scale.scope == "SOURCE_AND_PURCHASE_EVIDENCE_ONLY"
    assert preview.source_scale.market_observations_verified is False
    assert (
        preview.report.inputs.price_history_fingerprint
        == preview.history.fingerprint
        == preview.qualification_binding.history_fingerprint
    )
    assert (
        preview.report.inputs.source_version_id
        == preview.source.source_version_id
        == preview.qualification_binding.source_version_id
    )
    assert before == (asdict(context.state.owner), asdict(context.state.history))
    assert context.state.records == context.state.receipts == []
    context.owner_read.assert_awaited_once_with(context.reader_session, **context.scope, lock=False)
    context.history_read.assert_awaited_once()
    context.read_repository.latest.assert_awaited_once_with(*context.scope.values())
    context.read_repository.count.assert_awaited_once_with(*context.scope.values())
    forbidden.assert_not_called()
    assert_read_boundary(context)


async def test_preview_retains_bad_original_rows_and_their_reasons_beside_usable_evidence(context):
    good = context.state.history.rows[0]
    bad = replace(
        good,
        source_row_id=UUID(int=1101),
        fingerprint="a" * 64,
        high=Decimal("-1"),
        issues=("INVALID_ORIGINAL_VALUES",),
    )
    context.state.history = replace(
        context.state.history, rows=(good, bad), rows_observed=2, fingerprint="b" * 64
    )
    preview = await context.reader.qualification_preview(**context.scope)
    assert preview.history.rows == (good, bad)
    assert preview.readiness.status == "REVIEWABLE"
    assert preview.readiness.usable_row_count == 1
    reviews = {row.source_row_id: row for row in preview.readiness.rows}
    assert reviews[good.source_row_id].status == "SUITABLE_AFTER_CONFIRMATION"
    assert reviews[bad.source_row_id].status == "UNSUITABLE"
    assert "INVALID_ORIGINAL_VALUES" in {issue.code for issue in reviews[bad.source_row_id].issues}
    assert context.state.records == context.state.receipts == []


async def test_unsuitable_source_keeps_the_attempted_pin_without_promoting_it_to_a_binding(context):
    owner = context.state.owner
    attempted = owner.coverage.source.source_version_id
    context.state.owner = replace(
        owner,
        coverage=replace(owner.coverage, source=None, basis_id="a" * 64),
        source_evidence=HebeltraderSourceEvidence(attempted, None, ("PROVENANCE_MISMATCH",)),
    )
    preview = await context.reader.qualification_preview(**context.scope)
    assert preview.source is None
    assert preview.attempted_source_version_id == attempted
    assert "PROVENANCE_MISMATCH" in {item.code for item in preview.source_issues}
    assert preview.qualification_binding is None
    assert preview.readiness.status == "BLOCKED"
    assert "SOURCE_BASIS_MISSING" in {item.code for item in preview.readiness.issues}
    assert context.state.records == context.state.receipts == []


async def test_oversized_history_is_visible_and_never_qualified_as_a_truncated_sample(context):
    context.state.history = replace(
        context.state.history,
        status="LIMIT_EXCEEDED",
        reasons=("HISTORY_LIMIT_EXCEEDED",),
        rows=(),
        rows_observed=5001,
        stored_range_complete=False,
        intervals_complete=False,
        fingerprint="a" * 64,
    )
    preview = await context.reader.qualification_preview(**context.scope)
    assert preview.history.rows_observed == 5001
    assert preview.history.row_limit == 5000
    assert preview.history.rows == ()
    assert preview.history.stored_range_complete is False
    assert preview.readiness.status == "BLOCKED"
    assert preview.readiness.usable_row_count == 0
    assert preview.qualification_binding is None


@pytest.mark.parametrize("field", ["workspace_id", "trade_id", "position_id"])
@pytest.mark.parametrize("method", ["qualification_preview", "request_status"])
async def test_new_reads_reject_foreign_scope_before_reading_market_or_receipt_details(
    context, field, method
):
    scope = {**context.scope, field: UUID(int=1102)}
    extra = {"request_id": UUID(int=1103)} if method == "request_status" else {}
    with pytest.raises(ApplicationError) as caught:
        await getattr(context.reader, method)(**scope, **extra)
    assert caught.value.status_code == 404
    assert caught.value.code == "BASELINE_POSITION_NOT_FOUND"
    context.history_read.assert_not_awaited()
    context.read_repository.find_request.assert_not_awaited()
    context.read_repository.get.assert_not_awaited()
    assert context.state.records == context.state.receipts == []
    context.reader_session.rollback.assert_awaited_once()


async def test_preview_confirmation_roundtrip_records_exact_inputs_and_request_without_auto_replay(
    context,
):
    preview = await context.reader.qualification_preview(**context.scope)
    request = command_from_preview(preview)
    response = await existing.assess(context, request)
    record, receipt = context.state.records[0], context.state.receipts[0]
    before = deepcopy((context.state.records, context.state.receipts))
    status = await context.reader.request_status(**context.scope, request_id=request.request_id)
    assert status.status == "RECORDED"
    assert status.assessment == response.latest_assessment
    assert status.assessment.id == receipt.assessment_id == record.id
    assert status.qualification == request.qualification
    assert status.recorded_at == receipt.recorded_at
    assert status.assessment.targets[0].status == "PROVEN"
    assert record.inputs["history"]["rows"][0]["fingerprint"] == preview.history.rows[0].fingerprint
    assert record.inputs["source_provenance"]["content_hash"] == preview.source.content_hash
    assert (context.state.records, context.state.receipts) == before
    context.writer.commit.assert_awaited_once()
    await existing.assess(context, request)
    assert (context.state.records, context.state.receipts) == before
    context.writer.commit.assert_awaited_once()


@pytest.mark.parametrize("changed", ["owner", "history", "predecessor"])
async def test_preview_cas_rejects_inputs_changed_before_confirmation_without_receipt(
    context, changed
):
    preview = await context.reader.qualification_preview(**context.scope)
    request = command_from_preview(preview)
    if changed == "owner":
        context.state.owner = replace(
            context.state.owner,
            coverage=replace(context.state.owner.coverage, basis_id="a" * 64),
        )
    elif changed == "history":
        context.state.history = replace(context.state.history, fingerprint="b" * 64)
    else:
        await existing.assess(context, replace(request, request_id=UUID(int=1104)))
    before = deepcopy((context.state.records, context.state.receipts))
    context.writer.commit.reset_mock()
    with pytest.raises(ApplicationError) as caught:
        await existing.assess(context, request)
    assert caught.value.code == "HEBELTRADER_BASIS_CONFLICT"
    assert (context.state.records, context.state.receipts) == before
    context.writer.commit.assert_not_awaited()


@pytest.mark.parametrize(
    ("field", "value"), [("source_version_id", UUID(int=1105)), ("source_scale_reference", "other")]
)
async def test_editing_the_preview_binding_cannot_qualify_a_different_source_or_scale(
    context, field, value
):
    preview = await context.reader.qualification_preview(**context.scope)
    request = command_from_preview(preview)
    request = replace(request, qualification=replace(request.qualification, **{field: value}))
    with pytest.raises(ApplicationError) as caught:
        await existing.assess(context, request)
    assert caught.value.code == "HEBELTRADER_QUALIFICATION_MISMATCH"
    assert caught.value.status_code == 422
    assert context.state.records == context.state.receipts == []


async def test_reusable_binding_does_not_claim_current_suitability_for_unsupported_product(context):
    first = await context.reader.qualification_preview(**context.scope)
    request = command_from_preview(first)
    await existing.assess(context, request)
    context.state.owner = replace(context.state.owner, option_direction=OptionDirection.PUT)
    preview = await context.reader.qualification_preview(**context.scope)
    assert preview.qualification.status == "REUSABLE"
    assert preview.qualification.value == request.qualification
    assert preview.report.inputs.qualification_reusable is True
    assert preview.readiness.status == "BLOCKED"
    assert preview.qualification_binding is None
    assert "PRODUCT_DIRECTION_NOT_SUPPORTED" in {item.code for item in preview.readiness.issues}
    assert preview.report.latest_assessment.targets[0].status == "PROVEN"
    assert len(context.state.records) == 1


async def test_reused_declaration_names_containing_assessment_not_an_invented_original_attestor(
    context, monkeypatch
):
    first = await context.reader.qualification_preview(**context.scope)
    request = command_from_preview(first)
    await existing.assess(context, request)
    original = context.state.records[0]
    later = NOW + timedelta(hours=1)

    class LaterDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return later.astimezone(tz) if tz else later.replace(tzinfo=None)

    monkeypatch.setattr(module, "datetime", LaterDatetime)
    context.state.owner = replace(
        context.state.owner,
        coverage=replace(context.state.owner.coverage, basis_id="a" * 64),
    )
    current = await context.reader.qualification_preview(**context.scope)
    followup = replace(command_from_preview(current, number=1106), qualification=None)
    await existing.assess(context, followup, actor=UUID(int=1107), now=later)
    latest = context.state.records[-1]
    preview = await context.reader.qualification_preview(**context.scope)
    assert latest.id != original.id
    assert latest.recorded_by != original.recorded_by
    assert preview.qualification.status == "REUSABLE"
    assert preview.qualification.value == request.qualification
    assert preview.qualification.contained_in_assessment_id == latest.id
    assert preview.qualification.contained_in_recorded_at == later
    assert preview.qualification.origin == "USER_DECLARATION_NOT_INDEPENDENT_VERIFICATION"
    assert "recorded_by" not in asdict(preview.qualification)
    assert "confirmed_by" not in asdict(preview.qualification)
    assert context.state.records[0] == original


async def test_new_qualification_never_clears_a_source_correction_or_rewrites_the_old_proof(
    context,
):
    first = await context.reader.qualification_preview(**context.scope)
    first_request = command_from_preview(first)
    await existing.assess(context, first_request)
    original = deepcopy(context.state.records[0])
    owner = context.state.owner
    source = replace(owner.coverage.source, source_version_id=UUID(int=1108), content_hash="f" * 64)
    context.state.owner = replace(
        owner,
        coverage=replace(owner.coverage, source=source, basis_id="b" * 64),
        source_evidence=HebeltraderSourceEvidence(source.source_version_id, source),
    )
    preview = await context.reader.qualification_preview(**context.scope)
    assert preview.qualification.status == "STALE"
    assert preview.readiness.status == "REVIEWABLE"
    response = await existing.assess(
        context,
        command_from_preview(preview, number=1109, reference="Synthetic corrected-source archive"),
    )
    assert response.latest_assessment.targets[0].status == "REVIEW_REQUIRED"
    assert (
        response.latest_assessment.targets[0].proof_source_version_id
        == first.source.source_version_id
    )
    current = await context.reader.qualification_preview(**context.scope)
    await existing.assess(
        context, replace(command_from_preview(current, number=1110), qualification=None)
    )
    assert context.state.records[-1].result["targets"][0]["status"] == "REVIEW_REQUIRED"
    assert context.state.records[0] == original
    saved = await context.reader.request_status(
        **context.scope, request_id=first_request.request_id
    )
    assert saved.assessment.id == original.id
    assert saved.assessment.targets[0].status == "PROVEN"
    assert saved.qualification == first_request.qualification


async def test_unknown_request_is_read_only_uncertainty_not_an_assessment_or_failure(
    context, monkeypatch
):
    forbidden = Mock(side_effect=AssertionError("Receipt lookup must not assess saved prices"))
    monkeypatch.setattr(module, "evaluate_hebeltrader_targets", forbidden)
    request_id = UUID(int=1111)
    result = await context.reader.request_status(**context.scope, request_id=request_id)
    assert result.status == "UNKNOWN"
    assert result.request_id == request_id
    assert result.assessment is result.qualification is result.recorded_at is None
    assert result.operation_status == "READ_ONLY"
    context.owner_read.assert_awaited_once()
    assert context.owner_read.await_args.args == (context.reader_session,)
    assert all(
        context.owner_read.await_args.kwargs[key] == value for key, value in context.scope.items()
    )
    assert context.owner_read.await_args.kwargs.get("lock", False) is False
    context.read_repository.find_request.assert_awaited_once_with(
        context.scope["workspace_id"], request_id
    )
    context.read_repository.latest.assert_not_awaited()
    context.read_repository.get.assert_not_awaited()
    context.history_read.assert_not_awaited()
    forbidden.assert_not_called()
    assert_read_boundary(context)


@pytest.mark.parametrize("field", ["trade_id", "position_id"])
async def test_foreign_receipt_is_generic_not_found_before_its_assessment_can_be_read(
    context, field
):
    preview = await context.reader.qualification_preview(**context.scope)
    request = command_from_preview(preview)
    await existing.assess(context, request)
    foreign = UUID(int=1112)
    context.state.receipts[0] = replace(context.state.receipts[0], **{field: foreign})
    context.read_repository.get.reset_mock()
    with pytest.raises(ApplicationError) as caught:
        await context.reader.request_status(**context.scope, request_id=request.request_id)
    assert caught.value.status_code == 404
    assert str(foreign) not in caught.value.message
    assert str(context.state.records[0].id) not in caught.value.message
    context.read_repository.get.assert_not_awaited()


async def test_request_resolves_its_original_assessment_and_declaration_even_after_a_new_revision(
    context,
):
    preview = await context.reader.qualification_preview(**context.scope)
    first = command_from_preview(preview, reference="Synthetic original declaration")
    first_report = await existing.assess(context, first)
    current = await context.reader.qualification_preview(**context.scope)
    second = command_from_preview(current, number=1113, reference="Synthetic later declaration")
    second_report = await existing.assess(context, second)
    assert second_report.latest_assessment.id != first_report.latest_assessment.id
    context.read_repository.latest.reset_mock()
    before = deepcopy((context.state.records, context.state.receipts))
    result = await context.reader.request_status(**context.scope, request_id=first.request_id)
    assert result.assessment == first_report.latest_assessment
    assert result.qualification == first.qualification
    assert result.qualification != second.qualification
    assert result.recorded_at == context.state.receipts[0].recorded_at
    context.read_repository.latest.assert_not_awaited()
    context.read_repository.get.assert_awaited_once_with(
        *context.scope.values(), first_report.latest_assessment.id
    )
    assert (context.state.records, context.state.receipts) == before


async def test_repeated_input_receipt_uses_its_own_later_time_not_the_reused_assessment_time(
    context, monkeypatch
):
    first = command_from_preview(await context.reader.qualification_preview(**context.scope))
    initial = await existing.assess(context, first)
    later = NOW + timedelta(hours=1)

    class LaterDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return later.astimezone(tz) if tz else later.replace(tzinfo=None)

    monkeypatch.setattr(module, "datetime", LaterDatetime)
    preview = await context.reader.qualification_preview(**context.scope)
    repeat = replace(command_from_preview(preview, number=1114), qualification=None)
    await existing.assess(context, repeat, now=later)
    assert len(context.state.records) == 1
    assert len(context.state.receipts) == 2
    status = await context.reader.request_status(**context.scope, request_id=repeat.request_id)
    assert status.assessment == initial.latest_assessment
    assert status.assessment.recorded_at == NOW
    assert status.recorded_at == later
    assert status.qualification == first.qualification


async def test_missing_assessment_for_existing_receipt_is_unavailable_not_unknown(context):
    first = command_from_preview(await context.reader.qualification_preview(**context.scope))
    await existing.assess(context, first)
    context.read_repository.get.side_effect = lambda *args: None
    before = deepcopy((context.state.records, context.state.receipts))
    with pytest.raises(ApplicationError) as caught:
        await context.reader.request_status(**context.scope, request_id=first.request_id)
    assert caught.value.status_code == 503
    assert caught.value.code == "HEBELTRADER_REQUEST_READ_INCONSISTENT"
    assert (context.state.records, context.state.receipts) == before


async def test_closed_position_keeps_historical_preview_and_receipt_without_new_qualification(
    context, case
):
    first = command_from_preview(await context.reader.qualification_preview(**context.scope))
    report = await existing.assess(context, first)
    basis, revision, source = case
    sale = existing.owner_examples.fact(
        1115,
        quantity=basis.valuation_basis.position.open_quantity,
        side=ExecutionSide.SELL,
        after=timedelta(days=7),
    )
    closed_basis = existing.owner_examples.execution_basis((*basis.history, sale))
    context.state.owner = existing.examples.owner_basis((closed_basis, revision, source))
    before = deepcopy((context.state.records, context.state.receipts))
    preview = await context.reader.qualification_preview(**context.scope)
    assert preview.report.position_state == "CLOSED"
    assert preview.readiness.status == "NOT_APPLICABLE"
    assert preview.qualification_binding is None
    assert preview.report.latest_assessment == report.latest_assessment
    status = await context.reader.request_status(**context.scope, request_id=first.request_id)
    assert status.status == "RECORDED"
    assert status.assessment == report.latest_assessment
    assert (context.state.records, context.state.receipts) == before
