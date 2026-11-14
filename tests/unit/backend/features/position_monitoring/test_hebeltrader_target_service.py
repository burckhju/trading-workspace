"""Real target domain with synthetic owners and an intercepted persistence boundary."""

import asyncio
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call
from uuid import UUID

import httpx
import pytest
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from tests.unit.backend.features.position_monitoring import (
    test_hebeltrader_target_projection as examples,
)
from tests.unit.backend.features.trade_position import test_hebeltrader_coverage as owner_examples

from app.core.exceptions import ApplicationError
from app.features.learning.application.hebeltrader_source_reader import HebeltraderSourceEvidence
from app.features.position_monitoring.service import hebeltrader_targets as module
from app.features.position_monitoring.service.hebeltrader_target_contracts import (
    TargetAssessmentCommand,
)

case = owner_examples.case
pytestmark = pytest.mark.asyncio
NOW = examples.NOW


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW.astimezone(tz) if tz else NOW.replace(tzinfo=None)


@pytest.fixture(autouse=True)
def no_provider_access(monkeypatch):
    asynchronous = AsyncMock(
        side_effect=AssertionError("No provider call belongs to target assessment")
    )
    synchronous = Mock(side_effect=AssertionError("No provider call belongs to target assessment"))
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", asynchronous)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", synchronous)
    yield
    asynchronous.assert_not_awaited()
    synchronous.assert_not_called()


@pytest.fixture
def context(monkeypatch, case):
    owner = examples.owner_basis(case)
    engine = Mock(spec=AsyncEngine)
    writer = Mock(spec=AsyncSession)
    writer.bind = engine
    reader_session = Mock(spec=AsyncSession)
    for session in (writer, reader_session):
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
    state = SimpleNamespace(
        owner=owner, history=examples.price_history(owner), records=[], receipts=[]
    )
    trade = owner.execution_basis.trade
    scope = dict(
        workspace_id=trade.workspace_id, trade_id=trade.id, position_id=owner.coverage.position_id
    )

    def selected(workspace_id, trade_id, position_id):
        return [
            record
            for record in state.records
            if (record.workspace_id, record.trade_id, record.position_id)
            == (workspace_id, trade_id, position_id)
        ]

    def latest(workspace_id, trade_id, position_id):
        values = selected(workspace_id, trade_id, position_id)
        return values[-1] if values else None

    def requested(workspace_id, request_id):
        return next(
            (
                receipt
                for receipt in state.receipts
                if (receipt.workspace_id, receipt.request_id) == (workspace_id, request_id)
            ),
            None,
        )

    read_repository = SimpleNamespace(
        latest=AsyncMock(side_effect=latest),
        count=AsyncMock(side_effect=lambda *args: len(selected(*args))),
        get=AsyncMock(
            side_effect=lambda workspace_id, trade_id, position_id, assessment_id: next(
                (
                    item
                    for item in selected(workspace_id, trade_id, position_id)
                    if item.id == assessment_id
                ),
                None,
            )
        ),
        find_request=AsyncMock(side_effect=requested),
        add=AsyncMock(side_effect=AssertionError("Read snapshot cannot append assessments")),
        receipt=AsyncMock(side_effect=AssertionError("Read snapshot cannot append receipts")),
    )
    repository = SimpleNamespace(
        latest=AsyncMock(side_effect=AssertionError("Writer cannot supply snapshot facts")),
        count=AsyncMock(side_effect=AssertionError("Writer cannot supply snapshot facts")),
        get=AsyncMock(side_effect=AssertionError("Writer cannot supply snapshot facts")),
        find_request=AsyncMock(side_effect=AssertionError("Writer cannot supply snapshot facts")),
        add=AsyncMock(side_effect=state.records.append),
        receipt=AsyncMock(side_effect=state.receipts.append),
    )

    async def read_owner(session, *, workspace_id, trade_id, position_id, lock=False):
        assert session in (writer, reader_session)
        if (workspace_id, trade_id, position_id) != tuple(scope.values()):
            raise ApplicationError(
                code="BASELINE_POSITION_NOT_FOUND",
                message="Synthetic foreign scope",
                status_code=404,
            )
        if session is reader_session:
            assert lock is False
        return state.owner

    async def read_history(**kwargs):
        assert kwargs["workspace_id"] == trade.workspace_id
        assert kwargs["underlying_id"] == owner.coverage.underlying_id
        return state.history

    owner_read = AsyncMock(side_effect=read_owner)
    history_read = AsyncMock(side_effect=read_history)

    def repository_factory(session):
        assert session in (writer, reader_session)
        return repository if session is writer else read_repository

    def history_factory(session):
        assert session in (writer, reader_session)
        return SimpleNamespace(read=history_read)

    session_factory = Mock(return_value=reader_session)
    monkeypatch.setattr(module, "datetime", FrozenDatetime)
    monkeypatch.setattr(module, "AsyncSession", session_factory)
    monkeypatch.setattr(module, "SqlAlchemyHebeltraderTargetRepository", repository_factory)
    monkeypatch.setattr(module, "read_hebeltrader_monitoring_basis", owner_read)
    monkeypatch.setattr(module, "HebeltraderHistoryReader", history_factory)
    return SimpleNamespace(
        service=module.HebeltraderTargetService(writer),
        reader=module.HebeltraderTargetReader(engine),
        engine=engine,
        writer=writer,
        reader_session=reader_session,
        session_factory=session_factory,
        state=state,
        repository=repository,
        read_repository=read_repository,
        owner_read=owner_read,
        history_read=history_read,
        scope=scope,
        actor=trade.created_by,
    )


async def command(context, *, number=950, qualify=True):
    report = await context.reader.read(**context.scope)
    return TargetAssessmentCommand(
        position_id=context.scope["position_id"],
        request_id=UUID(int=number),
        expected_basis_id=report.current_basis_id,
        expected_assessment_id=report.latest_assessment.id if report.latest_assessment else None,
        qualification=(
            examples.comparison(context.state.owner, context.state.history) if qualify else None
        ),
    )


async def assess(context, request, **changes):
    return await context.service.assess(
        **(
            dict(
                workspace_id=context.scope["workspace_id"],
                trade_id=context.scope["trade_id"],
                command=request,
                actor=context.actor,
                now=NOW,
            )
            | changes
        )
    )


def assert_no_economic_mutation(context):
    for operation in ("add", "add_all", "delete", "flush"):
        getattr(context.writer, operation).assert_not_called()


async def test_explicit_assessment_persists_original_inputs_domain_view_and_receipt(context):
    request = await command(context)
    before = asdict(context.state.owner)
    context.owner_read.reset_mock()
    report = await assess(context, request)
    assert len(context.state.records) == len(context.state.receipts) == 1
    record, receipt = context.state.records[0], context.state.receipts[0]
    assert report.latest_assessment.id == record.id == receipt.assessment_id
    assert report.latest_assessment.targets[0].status == "PROVEN"
    assert report.implementation_status == "F207_2_TARGET_HISTORY_ONLY"
    assert report.operation_status == "NOT_ACTIVATED"
    assert record.previous_assessment_id is None
    assert record.inputs["history"]["rows"][0]["provider"] == "SYNTHETIC"
    assert (
        record.inputs["source_provenance"]["content_hash"]
        == context.state.owner.coverage.source.content_hash
    )
    assert (
        record.inputs["qualification"]["history_fingerprint"] == context.state.history.fingerprint
    )
    domain = module.ASSESSMENT_ADAPTER.validate_python(record.result["domain"])
    assert domain.z1.proof.evidence.high == Decimal("120")
    assert domain.z1_orientation.original_quantity == 100
    assert domain.z1_orientation.assigned_sold_quantity == 40
    assert asdict(context.state.owner) == before
    assert context.owner_read.await_args_list == [
        call(context.writer, **context.scope, lock=True),
        call(context.reader_session, **context.scope, lock=False),
    ]
    writer_statements = [str(item.args[0]) for item in context.writer.execute.await_args_list]
    assert writer_statements == [
        "SET TRANSACTION ISOLATION LEVEL READ COMMITTED",
        "SET LOCAL statement_timeout = '10000ms'",
    ]
    context.read_repository.add.assert_not_awaited()
    context.read_repository.receipt.assert_not_awaited()
    context.writer.commit.assert_awaited_once_with()
    assert_no_economic_mutation(context)


async def test_input_snapshot_starts_after_writer_lock_and_observes_new_owner_revision(context):
    request = await command(context)
    context.session_factory.reset_mock()
    context.history_read.reset_mock()
    context.read_repository.latest.reset_mock()
    lock_requested = asyncio.Event()
    release_lock = asyncio.Event()
    trace = []
    old_owner = context.state.owner

    async def owner_with_wait(session, **kwargs):
        if session is context.writer:
            assert kwargs["lock"] is True
            trace.append("lock_requested")
            lock_requested.set()
            await release_lock.wait()
            trace.append("lock_acquired")
            # This result is deliberately stale: it must never be reused as the
            # separately scoped, consistent evidence snapshot for the command.
            return old_owner
        assert session is context.reader_session and kwargs["lock"] is False
        trace.append("fresh_owner_read")
        return context.state.owner

    def create_snapshot(*args, **kwargs):
        assert args == (context.engine,)
        assert kwargs == {"expire_on_commit": False, "autoflush": False}
        assert trace[-1] == "lock_acquired"
        trace.append("fresh_snapshot_created")
        return context.reader_session

    context.owner_read.side_effect = owner_with_wait
    context.session_factory.side_effect = create_snapshot
    task = asyncio.create_task(assess(context, request))
    try:
        await asyncio.wait_for(lock_requested.wait(), timeout=2)
        context.session_factory.assert_not_called()
        context.read_repository.latest.assert_not_awaited()
        context.history_read.assert_not_awaited()
        new_revision = replace(
            old_owner.evidence_revision,
            id=UUID(int=990),
            supersedes_evidence_id=old_owner.evidence_revision.id,
            recorded_at=NOW,
        )
        context.state.owner = replace(
            old_owner,
            evidence_revision=new_revision,
            coverage=replace(
                old_owner.coverage,
                basis_id="3" * 64,
                evidence_revision_id=new_revision.id,
                evidence_recorded_at=NOW,
            ),
        )
        assert context.state.owner.execution_basis is old_owner.execution_basis
        release_lock.set()
        with pytest.raises(ApplicationError) as caught:
            await asyncio.wait_for(task, timeout=2)
        assert caught.value.code == "HEBELTRADER_BASIS_CONFLICT"
    finally:
        release_lock.set()
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    assert trace == [
        "lock_requested",
        "lock_acquired",
        "fresh_snapshot_created",
        "fresh_owner_read",
    ]
    assert context.state.records == context.state.receipts == []
    context.writer.commit.assert_not_awaited()
    context.writer.rollback.assert_awaited_once_with()
    context.reader_session.rollback.assert_awaited()


async def test_request_replay_does_not_evaluate_or_append_anything(context, monkeypatch):
    request = await command(context)
    first = await assess(context, request)
    evaluate = Mock(side_effect=AssertionError("Replay must not reevaluate"))
    monkeypatch.setattr(module, "evaluate_hebeltrader_targets", evaluate)
    context.writer.commit.reset_mock()
    context.writer.rollback.reset_mock()
    second = await assess(context, request)
    assert second.latest_assessment == first.latest_assessment
    assert len(context.state.records) == len(context.state.receipts) == 1
    evaluate.assert_not_called()
    context.writer.commit.assert_not_awaited()
    context.writer.rollback.assert_awaited_once_with()
    assert_no_economic_mutation(context)


async def test_new_request_for_same_inputs_only_appends_a_receipt_and_reuses_qualification(context):
    first = await assess(context, await command(context))
    second_request = await command(context, number=951, qualify=False)
    second = await assess(context, second_request)
    assert second.latest_assessment.id == first.latest_assessment.id
    assert len(context.state.records) == 1
    assert len(context.state.receipts) == 2
    assert context.state.receipts[0].assessment_id == context.state.receipts[1].assessment_id
    assert second.inputs.qualification_reusable is True


async def test_new_terms_provenance_gets_a_current_audit_snapshot_even_if_call_direction_unchanged(
    context,
):
    first = await assess(context, await command(context))
    context.state.owner = replace(context.state.owner, option_terms_version_ids=(UUID(int=960),))
    next_request = await command(context, number=951, qualify=False)
    assert next_request.expected_basis_id != first.current_basis_id
    second = await assess(context, next_request)
    assert second.currentness == "CURRENT"
    assert len(context.state.records) == 2
    assert context.state.records[-1].inputs["option_terms_version_ids"] == [str(UUID(int=960))]
    assert (
        second.latest_assessment.targets[0].event_id == first.latest_assessment.targets[0].event_id
    )


@pytest.mark.parametrize("change", ["request_content", "basis", "predecessor"])
async def test_request_id_and_compare_and_swap_conflicts_do_not_append(context, change):
    request = await command(context)
    if change == "request_content":
        await assess(context, request)
        request = replace(request, expected_basis_id="0" * 64)
        expected = "HEBELTRADER_REQUEST_CONFLICT"
    else:
        request = replace(
            request,
            **(
                {"expected_basis_id": "0" * 64}
                if change == "basis"
                else {"expected_assessment_id": UUID(int=970)}
            ),
        )
        expected = "HEBELTRADER_BASIS_CONFLICT"
    before = (len(context.state.records), len(context.state.receipts))
    context.writer.commit.reset_mock()
    with pytest.raises(ApplicationError) as caught:
        await assess(context, request)
    assert caught.value.code == expected
    assert (len(context.state.records), len(context.state.receipts)) == before
    context.writer.commit.assert_not_awaited()
    assert_no_economic_mutation(context)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("history_fingerprint", "0" * 64),
        ("listing_fingerprint", "0" * 64),
        ("source_version_id", UUID(int=971)),
        ("source_scale_reference", "unverified-new-scale"),
        ("evidence_reference", " "),
    ],
)
async def test_explicit_qualification_cannot_be_rebound_to_other_source_or_price_material(
    context, field, value
):
    request = await command(context)
    request = replace(request, qualification=replace(request.qualification, **{field: value}))
    with pytest.raises(ApplicationError) as caught:
        await assess(context, request)
    assert caught.value.code == "HEBELTRADER_QUALIFICATION_MISMATCH"
    assert caught.value.status_code == 422
    assert context.state.records == context.state.receipts == []
    context.writer.commit.assert_not_awaited()


@pytest.mark.parametrize("field", ["workspace_id", "trade_id", "position_id"])
async def test_foreign_scope_is_stopped_by_the_execution_owner_before_any_append(context, field):
    request = await command(context)
    args = {field: UUID(int=972)}
    if field == "position_id":
        request = replace(request, **args)
        args = {}
    with pytest.raises(ApplicationError) as caught:
        await assess(context, request, **args)
    assert caught.value.code == "BASELINE_POSITION_NOT_FOUND"
    assert context.state.records == context.state.receipts == []
    context.writer.commit.assert_not_awaited()


async def test_explicit_assessment_without_comparison_records_uncertainty_not_a_false_hit(context):
    report = await assess(context, await command(context, qualify=False))
    assert report.latest_assessment.targets[0].status == "NOT_ASSESSABLE"
    assert report.latest_assessment.targets[0].evidence is None
    assert report.inputs.qualification_reusable is False
    assert context.state.records[0].inputs["qualification"] is None


async def test_unsuitable_source_retains_attempted_pin_and_reasons_without_qualifying_it(context):
    owner = context.state.owner
    attempted_pin = owner.coverage.source.source_version_id
    context.state.owner = replace(
        owner,
        coverage=replace(owner.coverage, source=None, basis_id="2" * 64),
        source_evidence=HebeltraderSourceEvidence(attempted_pin, None, ("PROVENANCE_MISMATCH",)),
    )
    report = await assess(context, await command(context, qualify=False))
    record = context.state.records[0]
    assert record.inputs["source_evidence"] == {
        "source_version_id": str(attempted_pin),
        "source": None,
        "reasons": ["PROVENANCE_MISMATCH"],
    }
    assert record.inputs["source_provenance"] is None
    assert record.inputs["source"] is None
    assert record.source_version_id is None
    assert report.inputs.source_version_id is None
    assert report.latest_assessment.targets[0].status == "NOT_ASSESSABLE"


async def test_get_uses_own_database_readonly_transaction_without_evaluation_or_command(
    context, monkeypatch
):
    evaluate = Mock(side_effect=AssertionError("GET must not assess"))
    monkeypatch.setattr(module, "evaluate_hebeltrader_targets", evaluate)
    report = await context.reader.read(**context.scope)
    assert report.latest_assessment is None and report.currentness == "NO_ASSESSMENT"
    statements = [str(call.args[0]) for call in context.reader_session.execute.await_args_list]
    assert statements == [
        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY",
        "SET LOCAL statement_timeout = '10000ms'",
    ]
    assert context.session_factory.call_args.kwargs == {
        "expire_on_commit": False,
        "autoflush": False,
    }
    context.reader_session.rollback.assert_awaited_once_with()
    context.reader_session.commit.assert_not_awaited()
    context.writer.execute.assert_not_awaited()
    context.repository.add.assert_not_awaited()
    context.repository.receipt.assert_not_awaited()
    context.repository.find_request.assert_not_awaited()
    context.read_repository.find_request.assert_not_awaited()
    evaluate.assert_not_called()


async def test_get_after_data_change_preserves_persisted_proof_and_only_reports_changed_inputs(
    context, monkeypatch
):
    first = await assess(context, await command(context))
    original = deepcopy(context.state.records[0].result)
    context.state.history = replace(
        context.state.history, rows=(), status="MISSING", fingerprint="6" * 64
    )
    evaluate = Mock(side_effect=AssertionError("GET must not replace the persisted assessment"))
    monkeypatch.setattr(module, "evaluate_hebeltrader_targets", evaluate)
    report = await context.reader.read(**context.scope)
    assert report.currentness == "CHANGED_INPUTS"
    assert report.latest_assessment == first.latest_assessment
    assert report.inputs.available_price_rows == 0
    assert context.state.records[0].result == original
    assert len(context.state.records) == len(context.state.receipts) == 1
    evaluate.assert_not_called()


@pytest.mark.parametrize("mode", ["retracement", "missing", "source_correction"])
async def test_later_explicit_assessment_retains_original_proof_and_history(context, mode):
    first = await assess(context, await command(context))
    original = deepcopy(context.state.records[0].result)
    if mode == "retracement":
        history = examples.price_history(
            context.state.owner, high="109", trading_date=date(2026, 8, 7)
        )
        context.state.history = replace(
            history,
            fingerprint="6" * 64,
            rows=(replace(history.rows[0], source_row_id=UUID(int=980), fingerprint="5" * 64),),
        )
    elif mode == "missing":
        context.state.history = replace(
            context.state.history, rows=(), status="MISSING", fingerprint="6" * 64
        )
    else:
        owner = context.state.owner
        source = replace(
            owner.coverage.source,
            source_version_id=UUID(int=981),
            underlying=replace(owner.coverage.source.underlying, target_1=Decimal("115")),
        )
        context.state.owner = replace(
            owner, coverage=replace(owner.coverage, source=source, basis_id="4" * 64)
        )
        before_assessment = await context.reader.read(**context.scope)
        assert before_assessment.inputs.source_version_id == source.source_version_id
        assert (
            before_assessment.latest_assessment.source_version_id
            == owner.coverage.source.source_version_id
        )
        assert (
            before_assessment.latest_assessment.targets[0].proof_source_version_id
            == owner.coverage.source.source_version_id
        )
        assert before_assessment.currentness == "CHANGED_INPUTS"
        assert len(context.state.records) == 1
    second = await assess(context, await command(context, number=951))
    assert second.latest_assessment.previous_assessment_id == first.latest_assessment.id
    assert len(context.state.records) == 2
    target = second.latest_assessment.targets[0]
    assert target.status == ("REVIEW_REQUIRED" if mode == "source_correction" else "PROVEN")
    assert target.evidence == first.latest_assessment.targets[0].evidence
    assert target.event_id == first.latest_assessment.targets[0].event_id
    assert (
        target.proof_source_version_id == first.latest_assessment.targets[0].proof_source_version_id
    )
    assert context.state.records[0].result == original
    assert context.history_read.await_args.kwargs["listing_id"] == examples.LISTING


async def test_assessment_history_read_is_scoped_readonly_and_does_not_refresh_market_data(context):
    report = await assess(context, await command(context))
    context.history_read.reset_mock()
    historical = await context.reader.assessment(
        **context.scope, assessment_id=report.latest_assessment.id
    )
    assert historical is context.state.records[0]
    context.history_read.assert_not_awaited()
    context.reader_session.commit.assert_not_awaited()
    with pytest.raises(ApplicationError) as caught:
        await context.reader.assessment(**context.scope, assessment_id=UUID(int=982))
    assert caught.value.code == "HEBELTRADER_ASSESSMENT_NOT_FOUND"


async def test_read_failure_rolls_back_its_own_snapshot_without_becoming_missing_data(context):
    context.history_read.side_effect = RuntimeError("synthetic stored-history read failure")
    with pytest.raises(RuntimeError, match="synthetic stored-history read failure"):
        await context.reader.read(**context.scope)
    context.reader_session.rollback.assert_awaited_once_with()
    context.reader_session.commit.assert_not_awaited()
    context.repository.add.assert_not_awaited()
    context.repository.receipt.assert_not_awaited()


@pytest.mark.parametrize("kind", ["integrity", "serialization", "database"])
async def test_failed_persistence_rolls_back_and_never_reports_success(context, kind):
    request = await command(context)
    if kind == "integrity":
        error = IntegrityError("synthetic insert", {}, RuntimeError("conflict"))
        expected = "HEBELTRADER_ASSESSMENT_CONFLICT"
    else:
        original = RuntimeError("synthetic database failure")
        if kind == "serialization":
            original.sqlstate = "40001"
        error = DBAPIError("synthetic insert", {}, original)
        expected = "HEBELTRADER_BASIS_CONFLICT" if kind == "serialization" else None
    context.repository.add.side_effect = error
    with pytest.raises(ApplicationError if expected else DBAPIError) as caught:
        await assess(context, request)
    if expected:
        assert caught.value.code == expected
    context.writer.rollback.assert_awaited_once_with()
    context.writer.commit.assert_not_awaited()
    context.repository.receipt.assert_not_awaited()
