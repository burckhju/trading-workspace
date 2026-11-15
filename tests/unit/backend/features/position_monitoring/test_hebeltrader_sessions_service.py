"""One passive snapshot composes existing economic facts and session evidence."""

from copy import deepcopy
from dataclasses import asdict, fields, replace
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from tests.unit.backend.features.position_monitoring import test_hebeltrader_sessions as days
from tests.unit.backend.features.position_monitoring import (
    test_hebeltrader_target_projection as owner_projection,
)
from tests.unit.backend.features.position_monitoring import (
    test_hebeltrader_target_service as existing,
)
from tests.unit.backend.features.trade_position import test_hebeltrader_coverage as executions

from app.core.exceptions import ApplicationError
from app.features.market_data.domain.session_evidence import (
    SessionEvidenceCurrent,
    SessionEvidenceRead,
    SessionSourceProvenance,
)
from app.features.position_monitoring.service import hebeltrader_sessions as module
from app.features.trade_position.domain.enums import ExecutionSide

case = executions.case
no_provider_access = existing.no_provider_access
pytestmark = pytest.mark.asyncio
NOW = datetime(2026, 11, 15, 18, tzinfo=UTC)


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW.astimezone(tz) if tz else NOW.replace(tzinfo=None)


def calendar(owner):
    return SessionEvidenceCurrent(
        workspace_id=owner.execution_basis.trade.workspace_id,
        instrument_kind="UNDERLYING",
        instrument_id=owner.coverage.underlying_id,
        known_at=NOW,
        revision_id=UUID(int=7850),
        supersedes_revision_id=UUID(int=7849),
        revision_number=2,
        calendar_id="synthetic-official-calendar",
        calendar_version="synthetic-original-v2",
        binding=days.binding(instrument_id=owner.coverage.underlying_id),
        coverage_start=executions.BUY_TIME.date(),
        coverage_end=NOW.date(),
        evidence_status="ACTIVE",
        source=SessionSourceProvenance(
            manifest_sha256="b" * 64,
            document_sha256="c" * 64,
            document_filename="synthetic-original.txt",
            document_media_type="text/plain",
            publisher="Synthetic exchange source",
            reference="https://example.invalid/original-synthetic-calendar",
            published_at=None,
            published_on=executions.BUY_TIME.date(),
            retrieved_at=NOW - timedelta(days=2),
            reviewed_at=NOW - timedelta(days=1),
            review_reference="Synthetic review against all original document rows",
            recorded_by=owner.execution_basis.trade.created_by,
        ),
        recorded_at=NOW - timedelta(hours=1),
        read_at=NOW,
        status="AVAILABLE",
        reasons=(),
    )


@pytest.fixture
def context(monkeypatch, case):
    owner = owner_projection.owner_basis(case)
    engine = Mock(spec=AsyncEngine)
    session = Mock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    state = SimpleNamespace(owner=owner, calendar=calendar(owner), read_changes={})
    scope = dict(
        workspace_id=owner.execution_basis.trade.workspace_id,
        trade_id=owner.execution_basis.trade.id,
        position_id=owner.coverage.position_id,
    )

    async def read_owner(received_session, **kwargs):
        assert received_session is session
        assert kwargs["lock"] is False
        if {key: kwargs[key] for key in scope} != scope:
            raise ApplicationError(
                code="BASELINE_POSITION_NOT_FOUND",
                message="Synthetic foreign scope",
                status_code=404,
            )
        return state.owner

    async def read_current(**kwargs):
        assert kwargs == dict(
            workspace_id=scope["workspace_id"],
            instrument_kind="UNDERLYING",
            instrument_id=state.owner.coverage.underlying_id,
            known_at=NOW,
        )
        return state.calendar

    async def read_days(**kwargs):
        assert kwargs["expected_listing_id"] == state.calendar.binding.listing_id
        assert kwargs["known_at"] == NOW
        common = {
            item.name: getattr(state.calendar, item.name)
            for item in fields(SessionEvidenceCurrent)
            if item.name not in {"status", "reasons"}
        }
        result = SessionEvidenceRead(
            **common,
            start_date=kwargs["start_date"],
            end_date=kwargs["end_date"],
            days=tuple(
                days.original_day(kwargs["start_date"] + timedelta(days=index))
                for index in range((kwargs["end_date"] - kwargs["start_date"]).days + 1)
            ),
            status="COMPLETE",
            reasons=(),
            missing_dates=(),
            fingerprint="d" * 64,
        )
        return replace(result, **state.read_changes)

    owner_read = AsyncMock(side_effect=read_owner)
    current_read = AsyncMock(side_effect=read_current)
    period_read = AsyncMock(side_effect=read_days)
    evidence_reader = SimpleNamespace(current=current_read, read=period_read)
    evidence_factory = Mock(
        side_effect=lambda received: evidence_reader if received is session else None
    )
    session_factory = Mock(return_value=session)
    monkeypatch.setattr(module, "datetime", FrozenDatetime)
    monkeypatch.setattr(module, "AsyncSession", session_factory)
    monkeypatch.setattr(module, "SessionEvidenceReader", evidence_factory)
    monkeypatch.setattr(module, "read_hebeltrader_monitoring_basis", owner_read)
    return SimpleNamespace(
        reader=module.HebeltraderSessionReader(engine),
        engine=engine,
        session=session,
        state=state,
        scope=scope,
        owner_read=owner_read,
        current_read=current_read,
        period_read=period_read,
        session_factory=session_factory,
        evidence_factory=evidence_factory,
    )


def assert_passive_snapshot(context):
    context.session_factory.assert_called_once_with(
        context.engine, expire_on_commit=False, autoflush=False
    )
    assert [str(item.args[0]) for item in context.session.execute.await_args_list] == [
        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY",
        "SET LOCAL statement_timeout = '10000ms'",
    ]
    context.session.rollback.assert_awaited_once_with()
    context.session.commit.assert_not_awaited()
    for operation in ("add", "add_all", "delete", "flush"):
        getattr(context.session, operation).assert_not_called()


async def test_complete_input_is_a_read_time_count_without_any_rule_or_economic_mutation(context):
    before = deepcopy((asdict(context.state.owner), asdict(context.state.calendar)))
    report = await context.reader.read(**context.scope)
    first = context.state.owner.execution_basis.effective_executions[0]
    assert report.entry.execution_id == first.id
    assert report.entry.executed_at == first.executed_at
    assert report.entry.time_precision == "EXACT"
    assert report.count.completed_sessions == (NOW.date() - executions.BUY_TIME.date()).days
    assert report.count.twentieth_session_date == executions.BUY_TIME.date() + timedelta(days=20)
    assert report.count.threshold_reached is True
    assert report.position_state == "OPEN"
    assert report.evaluated_at == report.count.evaluated_at == report.calendar.known_at == NOW
    assert report.period.days[0].session_date == executions.BUY_TIME.date() + timedelta(days=1)
    assert report.period.fingerprint == "d" * 64
    assert report.calendar.source.published_at is None
    assert report.calendar.source.published_on == executions.BUY_TIME.date()
    assert report.calendar.verification == "MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION"
    assert report.implementation_status == "F207_3_SESSION_EVIDENCE_AND_COUNT_ONLY"
    assert report.rule_evaluation_status == "B04_B05_B06_B58_NOT_EVALUATED"
    assert report.operation_status == "NOT_ACTIVATED"
    assert report.read_status == "READ_ONLY"
    assert report.issues == ()
    assert "900 Sekunden" in " ".join(report.notices)
    assert "Original-Geldkurszeit" in " ".join(report.notices)
    assert before == (asdict(context.state.owner), asdict(context.state.calendar))
    context.owner_read.assert_awaited_once_with(context.session, **context.scope, lock=False)
    context.evidence_factory.assert_called_once_with(context.session)
    assert_passive_snapshot(context)


async def test_sale_and_rebuy_keep_owner_entry_without_recomputing_inventory(context):
    basis = context.state.owner.execution_basis
    assert [fact.side for fact in basis.effective_executions] == [
        ExecutionSide.BUY,
        ExecutionSide.BUY,
        ExecutionSide.SELL,
        ExecutionSide.BUY,
    ]
    report = await context.reader.read(**context.scope)
    assert report.entry.execution_id == basis.effective_executions[0].id
    assert report.count.anchor_date == basis.valuation_basis.position.opened_at.date()
    assert basis.valuation_basis.position.open_quantity == 80
    assert basis.valuation_basis.position.cost_basis == Decimal("218")
    assert_passive_snapshot(context)


async def test_corrected_first_execution_changes_anchor_and_identity_without_rewriting_original(
    context,
):
    old_owner = context.state.owner
    old_history = deepcopy(old_owner.execution_basis.history)
    before = await context.reader.read(**context.scope)
    original = old_owner.execution_basis.history[0]
    correction = replace(
        original,
        id=UUID(int=7880),
        executed_at=original.executed_at - timedelta(days=1),
        supersedes_execution_id=original.id,
    )
    context.state.owner = replace(
        old_owner,
        execution_basis=executions.execution_basis([*old_history, correction]),
    )
    after = await context.reader.read(**context.scope)
    assert after.entry.execution_id == correction.id
    assert after.count.anchor_date == correction.executed_at.date()
    assert after.count.completed_sessions == before.count.completed_sessions + 1
    assert after.basis_id != before.basis_id
    assert old_owner.execution_basis.history == old_history
    assert original in context.state.owner.execution_basis.history


async def test_missing_target_source_and_option_direction_do_not_block_independent_session_count(
    context,
):
    owner = context.state.owner
    context.state.owner = replace(
        owner,
        coverage=replace(owner.coverage, source=None),
        evidence_revision=None,
        source_evidence=None,
        option_direction=None,
        option_terms_version_ids=(),
        option_direction_reason="OPTION_DIRECTION_MISSING",
    )
    report = await context.reader.read(**context.scope)
    assert report.count.status == "AVAILABLE"
    assert report.count.threshold_reached is True
    assert report.rule_evaluation_status == "B04_B05_B06_B58_NOT_EVALUATED"


@pytest.mark.parametrize("cancelled", [False, True])
async def test_closed_and_trade_cancelled_positions_do_not_run_a_current_count(context, cancelled):
    basis = context.state.owner.execution_basis
    if cancelled:
        basis = replace(basis, trade=replace(basis.trade, cancelled_at=NOW))
        assert basis.valuation_basis.position.is_cancelled is False
    else:
        closing = executions.fact(
            7881, quantity=80, side=ExecutionSide.SELL, after=timedelta(days=3)
        )
        basis = executions.execution_basis([*basis.history, closing])
    context.state.owner = replace(context.state.owner, execution_basis=basis)
    report = await context.reader.read(**context.scope)
    assert report.position_state == ("CANCELLED" if cancelled else "CLOSED")
    assert report.count.status == "NOT_APPLICABLE"
    assert report.count.completed_sessions is report.count.threshold_reached is None
    assert report.period.status == "NOT_REQUESTED"
    context.period_read.assert_not_awaited()
    assert_passive_snapshot(context)


@pytest.mark.parametrize("ambiguous", [False, True])
async def test_date_only_owner_ordering_anchor_is_never_presented_as_known_clock(
    context, ambiguous
):
    basis = context.state.owner.execution_basis
    first = basis.effective_executions[0]
    execution_date = first.executed_at.date()
    execution_zone = "America/New_York" if ambiguous else "Europe/Berlin"
    first = replace(
        first,
        executed_on=execution_date,
        execution_timezone=execution_zone,
        executed_at=datetime.combine(execution_date, time.min, ZoneInfo(execution_zone)).astimezone(
            UTC
        ),
    )
    context.state.owner = replace(
        context.state.owner,
        execution_basis=replace(
            basis, effective_executions=(first, *basis.effective_executions[1:])
        ),
    )
    report = await context.reader.read(**context.scope)
    assert report.entry.executed_at is None
    assert report.entry.executed_on == first.executed_on
    assert report.entry.time_precision == "DATE_ONLY"
    if ambiguous:
        assert report.count.status == "NOT_ASSESSABLE"
        assert report.count.reasons == ("ENTRY_CALENDAR_DAY_AMBIGUOUS",)
        assert report.issues[0].detail.startswith("Das Kaufdatum ohne Uhrzeit")
        context.period_read.assert_not_awaited()
    else:
        assert report.count.status == "AVAILABLE"
        assert report.count.anchor_date == first.executed_on


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        ("MISSING", "SESSION_EVIDENCE_MISSING"),
        ("UNSUITABLE", "SESSION_EVIDENCE_WITHDRAWN"),
        ("UNSUITABLE", "SESSION_OWNER_BINDING_CHANGED"),
    ],
)
async def test_missing_withdrawn_or_changed_calendar_remains_readable_and_unassessable(
    context, status, reason
):
    context.state.calendar = replace(context.state.calendar, status=status, reasons=(reason,))
    report = await context.reader.read(**context.scope)
    assert report.count.status == "NOT_ASSESSABLE"
    assert report.count.completed_sessions is report.count.threshold_reached is None
    assert report.issues[0].code == reason
    assert report.issues[0].detail
    assert report.calendar == context.state.calendar
    context.period_read.assert_not_awaited()
    assert_passive_snapshot(context)


@pytest.mark.parametrize(
    ("status", "reason"),
    [
        ("INCOMPLETE", "SESSION_DAY_EVIDENCE_GAP"),
        ("INCOMPLETE", "SESSION_DAY_EVIDENCE_UNKNOWN"),
        ("INCOMPLETE", "SESSION_COVERAGE_RANGE_GAP"),
        ("LIMIT_EXCEEDED", "SESSION_RANGE_LIMIT_EXCEEDED"),
    ],
)
async def test_incomplete_calendar_is_not_partially_counted_or_reported_as_zero(
    context, status, reason
):
    missing = executions.BUY_TIME.date() + timedelta(days=1)
    context.state.read_changes = dict(status=status, reasons=(reason,), missing_dates=(missing,))
    report = await context.reader.read(**context.scope)
    assert report.count.status == "NOT_ASSESSABLE"
    assert report.count.completed_sessions is report.count.threshold_reached is None
    assert report.period.status == status
    assert report.period.missing_dates == (missing,)
    assert report.period.days
    assert report.issues[0].code == reason


async def test_same_day_entry_reports_zero_without_requesting_an_inverted_period(context):
    basis = context.state.owner.execution_basis
    first = replace(
        basis.effective_executions[0], executed_at=NOW - timedelta(hours=2), recorded_at=NOW
    )
    context.state.owner = replace(
        context.state.owner, execution_basis=executions.execution_basis([first])
    )
    report = await context.reader.read(**context.scope)
    assert report.count.status == "AVAILABLE"
    assert report.count.completed_sessions == 0
    assert report.count.threshold_reached is False
    assert report.period.status == "NOT_REQUESTED"
    context.period_read.assert_not_awaited()


@pytest.mark.parametrize("field", ["workspace_id", "trade_id", "position_id"])
async def test_foreign_position_is_rejected_by_execution_owner_before_any_calendar_read(
    context, field
):
    with pytest.raises(ApplicationError) as caught:
        await context.reader.read(**(context.scope | {field: UUID(int=7899)}))
    assert caught.value.code == "BASELINE_POSITION_NOT_FOUND"
    context.current_read.assert_not_awaited()
    context.period_read.assert_not_awaited()
    assert_passive_snapshot(context)


@pytest.mark.parametrize(
    "changes",
    [
        {"workspace_id": UUID(int=7899)},
        {"instrument_kind": "WARRANT"},
        {"instrument_id": UUID(int=7899)},
        {"known_at": NOW - timedelta(seconds=1)},
        {"revision_id": UUID(int=7899)},
        {"start_date": executions.BUY_TIME.date()},
        {"end_date": NOW.date() - timedelta(days=1)},
        {"binding": days.binding(listing_id=UUID(int=7899))},
        {"source": None},
    ],
)
async def test_mixed_revision_scope_or_range_is_an_error_without_a_partial_report(context, changes):
    context.state.read_changes = changes
    with pytest.raises(ApplicationError) as caught:
        await context.reader.read(**context.scope)
    assert caught.value.code == "HEBELTRADER_SESSION_READ_INCONSISTENT"
    assert_passive_snapshot(context)


async def test_wrong_instrument_current_metadata_is_not_used_as_an_entry_calendar(context):
    context.state.calendar = replace(context.state.calendar, instrument_kind="WARRANT")
    with pytest.raises(ApplicationError, match="konsistent"):
        await context.reader.read(**context.scope)
    context.period_read.assert_not_awaited()


async def test_read_transaction_setup_failure_also_rolls_back(context):
    failure = DBAPIError("SET LOCAL", {}, Exception("Synthetic private detail"))
    context.session.execute.side_effect = [None, failure]
    with pytest.raises(DBAPIError):
        await context.reader.read(**context.scope)
    context.session.rollback.assert_awaited_once_with()
    context.owner_read.assert_not_awaited()
    context.session.commit.assert_not_awaited()
