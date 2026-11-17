"""Original BID clocks compose existing owners in exactly one passive snapshot."""

from copy import deepcopy
from dataclasses import asdict, fields, replace
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from tests.unit.backend.features.position_monitoring import test_hebeltrader_original_bid as bids
from tests.unit.backend.features.position_monitoring import (
    test_hebeltrader_sessions_service as sessions,
)
from tests.unit.backend.features.position_monitoring import (
    test_hebeltrader_target_projection as projection,
)
from tests.unit.backend.features.trade_position import test_hebeltrader_coverage as executions

from app.core.exceptions import ApplicationError
from app.features.market_data.domain.risk_evidence import SavedQuoteEvidence
from app.features.market_data.domain.session_evidence import (
    SessionDay,
    SessionEvidenceCurrent,
    SessionEvidenceRead,
    SessionWindow,
)
from app.features.position_monitoring.service import hebeltrader_original_bid as module
from app.features.trade_position.domain.enums import ExecutionSide

case = executions.case
no_provider_access = sessions.no_provider_access
pytestmark = pytest.mark.asyncio
NOW = sessions.NOW


def scoped_quote(owner, age=timedelta(seconds=60)):
    saved = bids.saved_example(now=NOW, bid_age=age)
    return replace(
        saved,
        route=replace(
            saved.route,
            workspace_id=owner.execution_basis.trade.workspace_id,
            position_id=owner.coverage.position_id,
            warrant_id=owner.execution_basis.trade.product_id,
        ),
    )


def original_day(kind, day):
    return SessionDay(
        session_date=day,
        status="SESSION",
        intervals=(
            SessionWindow(
                datetime.combine(day, time(8), UTC),
                datetime.combine(day, time(22 if kind == "WARRANT" else 17), UTC),
            ),
        ),
        source_reference=f"Synthetic original {kind} document row {day}",
    )


@pytest.fixture
def context(monkeypatch, case):
    owner = projection.owner_basis(case)
    saved = scoped_quote(owner)
    calendar = sessions.calendar(owner)
    route = saved.route
    product = replace(
        calendar,
        instrument_kind="WARRANT",
        instrument_id=route.warrant_id,
        revision_id=UUID(int=7950),
        binding=replace(
            calendar.binding,
            instrument_kind="WARRANT",
            instrument_id=route.warrant_id,
            listing_id=route.warrant_listing_id,
            trading_venue_id=route.trading_venue_id,
            venue_mic=route.venue_mic,
        ),
    )
    state = SimpleNamespace(
        owner=owner,
        saved=saved,
        calendars={"UNDERLYING": calendar, "WARRANT": product},
        changes={},
        day=original_day,
    )
    engine = Mock(spec=AsyncEngine)
    session = Mock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    scope = dict(
        workspace_id=owner.execution_basis.trade.workspace_id,
        trade_id=owner.execution_basis.trade.id,
        position_id=owner.coverage.position_id,
    )

    async def read_owner(received, **kwargs):
        assert received is session
        assert kwargs["lock"] is False
        if {key: kwargs[key] for key in scope} != scope:
            raise ApplicationError(
                code="BASELINE_POSITION_NOT_FOUND",
                message="Synthetic foreign scope",
                status_code=404,
            )
        return state.owner

    async def read_quote(**kwargs):
        assert kwargs == dict(
            workspace_id=scope["workspace_id"],
            position_id=scope["position_id"],
            as_of=NOW,
            expected_warrant_id=state.owner.execution_basis.trade.product_id,
        )
        return state.saved

    async def read_current(**kwargs):
        kind = kwargs["instrument_kind"]
        assert kwargs == dict(
            workspace_id=scope["workspace_id"],
            instrument_kind=kind,
            instrument_id=(
                state.owner.coverage.underlying_id if kind == "UNDERLYING" else route.warrant_id
            ),
            known_at=NOW,
            expected_listing_id=None if kind == "UNDERLYING" else route.warrant_listing_id,
        )
        return state.calendars[kind]

    async def read_days(**kwargs):
        kind = kwargs["instrument_kind"]
        current = state.calendars[kind]
        assert kwargs["workspace_id"] == scope["workspace_id"]
        assert kwargs["instrument_id"] == current.instrument_id
        assert kwargs["expected_listing_id"] == current.binding.listing_id
        assert kwargs["known_at"] == NOW
        common = {
            field.name: getattr(current, field.name)
            for field in fields(SessionEvidenceCurrent)
            if field.name not in {"status", "reasons"}
        }
        result = SessionEvidenceRead(
            **common,
            start_date=kwargs["start_date"],
            end_date=kwargs["end_date"],
            days=tuple(
                state.day(kind, kwargs["start_date"] + timedelta(days=index))
                for index in range((kwargs["end_date"] - kwargs["start_date"]).days + 1)
            ),
            status="COMPLETE",
            reasons=(),
            missing_dates=(),
            fingerprint="d" * 64,
        )
        return replace(result, **state.changes.get(kind, {}))

    owner_read = AsyncMock(side_effect=read_owner)
    quote_read = AsyncMock(side_effect=read_quote)
    current_read = AsyncMock(side_effect=read_current)
    period_read = AsyncMock(side_effect=read_days)
    quote_factory = Mock(return_value=SimpleNamespace(saved_quote=quote_read))
    calendar_factory = Mock(return_value=SimpleNamespace(current=current_read, read=period_read))
    session_factory = Mock(return_value=session)
    monkeypatch.setattr(module, "datetime", sessions.FrozenDatetime)
    monkeypatch.setattr(module, "AsyncSession", session_factory)
    monkeypatch.setattr(module, "RiskMarketDataReader", quote_factory)
    monkeypatch.setattr(module, "SessionEvidenceReader", calendar_factory)
    monkeypatch.setattr(module, "read_hebeltrader_monitoring_basis", owner_read)
    return SimpleNamespace(
        reader=module.HebeltraderOriginalBidReader(engine),
        engine=engine,
        session=session,
        state=state,
        scope=scope,
        owner_read=owner_read,
        quote_read=quote_read,
        current_read=current_read,
        period_read=period_read,
        session_factory=session_factory,
        quote_factory=quote_factory,
        calendar_factory=calendar_factory,
    )


def checks(report):
    return {check.key: check for check in report.checks}


async def test_exact_original_bid_read_keeps_all_owners_and_open_gaps_distinct(context):
    before = deepcopy(
        (asdict(context.state.owner), asdict(context.state.saved), context.state.calendars)
    )
    report = await context.reader.read(**context.scope)
    observed = report.saved_quote.quote.observed_at
    assert report.bid.original_bid_at == NOW - timedelta(seconds=60)
    assert observed == NOW - timedelta(seconds=90)
    assert report.bid.age_seconds == Decimal("60")
    assert report.evaluated_at == report.bid.evaluated_at == NOW
    assert report.underlying_sessions.count.evaluated_at == report.bid.original_bid_at
    assert report.underlying_sessions.count.threshold_reached is True
    assert report.product_sessions.at_bid.event_at == report.bid.original_bid_at
    assert report.product_sessions.at_read.event_at == NOW
    assert report.product_sessions.interval_relation == "SAME_INTERVAL"
    assert report.product_sessions.period.start_date == NOW.date() - timedelta(days=1)
    assert len(report.checks) == 8
    expected = checks(report)
    assert (
        expected["PRICE_SCALE"].status
        == expected["VERIFIED_LIVE_MARKET_STATUS"].status
        == "MISSING"
    )
    assert all(
        check.status == "SATISFIED"
        for key, check in expected.items()
        if key not in {"PRICE_SCALE", "VERIFIED_LIVE_MARKET_STATUS"}
    )
    assert report.coverage_status == "PARTIAL"
    assert report.implementation_status == "F207_3_ORIGINAL_BID_EVIDENCE_ONLY"
    assert report.rule_evaluation_status == "B04_B05_B06_B58_NOT_EVALUATED"
    assert report.operation_status == "NOT_ACTIVATED"
    assert report.read_status == "READ_ONLY"
    assert report.saved_quote.provenance.stored_at is None
    assert report.saved_quote.provenance.historical_read is False
    assert before == (
        asdict(context.state.owner),
        asdict(context.state.saved),
        context.state.calendars,
    )
    assert report.economic_basis is context.state.owner.execution_basis.valuation_basis
    context.owner_read.assert_awaited_once_with(context.session, **context.scope, lock=False)
    context.quote_factory.assert_called_once_with(context.session)
    context.calendar_factory.assert_called_once_with(context.session)
    sessions.assert_passive_snapshot(context)


async def test_partial_sale_and_rebuy_use_existing_cost_contributions_and_entry(context):
    basis = context.state.owner.execution_basis
    assert [fact.side for fact in basis.effective_executions] == [
        ExecutionSide.BUY,
        ExecutionSide.BUY,
        ExecutionSide.SELL,
        ExecutionSide.BUY,
    ]
    report = await context.reader.read(**context.scope)
    assert report.economic_basis.position.open_quantity == 80
    assert report.economic_basis.position.cost_basis == Decimal("218")
    assert report.economic_basis.position.average_entry_price == Decimal("2.725")
    assert report.entry.execution_id == basis.effective_executions[0].id
    assert (
        report.economic_basis.buy_currency_evidence == basis.valuation_basis.buy_currency_evidence
    )
    assert report.economic_basis.basis_id == basis.valuation_basis.basis_id


@pytest.mark.parametrize("seconds,expected", [(60, False), (30, True)])
async def test_twentieth_session_must_have_finished_at_bid_not_the_later_read(
    context, seconds, expected
):
    context.state.saved = scoped_quote(context.state.owner, timedelta(seconds=seconds))
    first = executions.BUY_TIME.date()

    def document(kind, day):
        normal = original_day(kind, day)
        if kind == "WARRANT" or 0 < (day - first).days <= 19:
            return normal
        if day == NOW.date():
            return replace(
                normal,
                intervals=(
                    SessionWindow(datetime.combine(day, time(8), UTC), NOW - timedelta(seconds=30)),
                ),
            )
        return replace(normal, status="CLOSED", intervals=())

    context.state.day = document
    report = await context.reader.read(**context.scope)
    count = report.underlying_sessions.count
    assert count.threshold_reached is expected
    assert count.completed_sessions == (20 if expected else 19)
    assert count.evaluated_at == NOW - timedelta(seconds=seconds)
    assert checks(report)["TWENTY_UNDERLYING_SESSIONS_AT_BID"].status == (
        "SATISFIED" if expected else "NOT_REACHED"
    )


@pytest.mark.parametrize("kind", ["WARRANT", "UNDERLYING"])
@pytest.mark.parametrize(
    "status,reason",
    [("MISSING", "SESSION_EVIDENCE_MISSING"), ("UNSUITABLE", "SESSION_EVIDENCE_WITHDRAWN")],
)
async def test_missing_or_withdrawn_calendar_never_falls_back_to_old_rows(
    context, kind, status, reason
):
    context.state.calendars[kind] = replace(
        context.state.calendars[kind], status=status, reasons=(reason,)
    )
    report = await context.reader.read(**context.scope)
    assert not any(
        call.kwargs["instrument_kind"] == kind for call in context.period_read.await_args_list
    )
    if kind == "WARRANT":
        assert report.product_sessions.at_bid.status == "NOT_ASSESSABLE"
        assert reason in report.product_sessions.at_bid.reasons
    else:
        assert report.underlying_sessions.count.status == "NOT_ASSESSABLE"
        assert reason in report.underlying_sessions.count.reasons


@pytest.mark.parametrize("kind", ["WARRANT", "UNDERLYING"])
@pytest.mark.parametrize(
    "reason",
    ["SESSION_DAY_EVIDENCE_GAP", "SESSION_DAY_EVIDENCE_UNKNOWN", "SESSION_RANGE_LIMIT_EXCEEDED"],
)
async def test_incomplete_unknown_or_oversized_period_is_not_qualified(context, kind, reason):
    context.state.changes[kind] = dict(status="INCOMPLETE", reasons=(reason,))
    report = await context.reader.read(**context.scope)
    if kind == "WARRANT":
        assert report.product_sessions.at_read.status == "NOT_ASSESSABLE"
        assert report.product_sessions.interval_relation == "NOT_ASSESSABLE"
    else:
        assert report.underlying_sessions.count.completed_sessions is None
        assert reason in report.underlying_sessions.count.reasons


@pytest.mark.parametrize("kind", ["legacy", "reference", "ask_only", "missing", "invalid", "old"])
async def test_no_qualified_bid_never_counts_sessions_at_a_substitute_clock(context, kind):
    saved = context.state.saved
    if kind == "legacy":
        saved = replace(saved, quote=replace(saved.quote, original_evidence=None))
    elif kind == "reference":
        saved = replace(
            saved,
            quote=replace(
                saved.quote,
                original_evidence=None,
                bid=None,
                ask=None,
                reference_price=Decimal("2"),
                reference_price_type="LAST_TRADE",
            ),
        )
    elif kind == "ask_only":
        saved = replace(
            saved,
            quote=replace(
                saved.quote,
                original_evidence=replace(saved.quote.original_evidence, bid=None),
                bid=None,
            ),
        )
    elif kind in {"missing", "invalid"}:
        saved = SavedQuoteEvidence(
            (
                "NO_SAVED_QUOTE_FOR_CURRENT_ROUTE"
                if kind == "missing"
                else "SAVED_QUOTE_IDENTITY_OR_TIME_INVALID"
            ),
            route=saved.route,
        )
    else:
        saved = scoped_quote(context.state.owner, timedelta(seconds=900, microseconds=1))
    context.state.saved = saved
    report = await context.reader.read(**context.scope)
    assert report.bid.status in {"MISSING", "UNSUITABLE"}
    assert report.underlying_sessions.count is None
    assert report.product_sessions.period.status == "NOT_REQUESTED"
    context.period_read.assert_not_awaited()
    if kind in {"reference", "ask_only"}:
        assert checks(report)["EXECUTION_CURRENCY"].status == "MISSING"


@pytest.mark.parametrize("currency,status", [("USD", "KNOWN"), (None, "UNKNOWN"), (None, "MIXED")])
async def test_historical_currency_is_reused_and_mismatches_are_never_converted(
    context, currency, status
):
    owner = context.state.owner
    context.state.owner = replace(
        owner,
        execution_basis=replace(
            owner.execution_basis,
            valuation_basis=replace(
                owner.execution_basis.valuation_basis,
                cost_basis_currency=currency,
                currency_status=status,
            ),
        ),
    )
    report = await context.reader.read(**context.scope)
    assert checks(report)["EXECUTION_CURRENCY"].status == (
        "MISSING" if status == "UNKNOWN" else "UNSUITABLE"
    )
    assert report.economic_basis.cost_basis_currency == currency
    assert report.bid.currency == "EUR"


@pytest.mark.parametrize("at_read", [False, True])
async def test_documented_interval_at_each_clock_is_separate_and_close_is_excluded(
    context, at_read
):
    def document(kind, day):
        normal = original_day(kind, day)
        if kind == "WARRANT" and day == NOW.date():
            close = NOW if at_read else NOW - timedelta(seconds=60)
            return replace(
                normal, intervals=(SessionWindow(datetime.combine(day, time(8), UTC), close),)
            )
        return normal

    context.state.day = document
    report = await context.reader.read(**context.scope)
    assert report.product_sessions.at_read.status == "OUTSIDE_DOCUMENTED_INTERVAL"
    assert report.product_sessions.at_bid.status == (
        "IN_DOCUMENTED_INTERVAL" if at_read else "OUTSIDE_DOCUMENTED_INTERVAL"
    )
    assert report.coverage_status == "UNSUITABLE"


async def test_different_documented_intervals_are_visible_without_inventing_a_new_rule(context):
    def document(kind, day):
        normal = original_day(kind, day)
        if kind == "WARRANT" and day == NOW.date():
            return replace(
                normal,
                intervals=(
                    SessionWindow(datetime.combine(day, time(8), UTC), NOW - timedelta(seconds=30)),
                    SessionWindow(
                        NOW - timedelta(seconds=20), datetime.combine(day, time(22), UTC)
                    ),
                ),
            )
        return normal

    context.state.day = document
    report = await context.reader.read(**context.scope)
    assert report.product_sessions.interval_relation == "DIFFERENT_INTERVALS"
    assert checks(report)["PRODUCT_SESSION_AT_BID"].status == "SATISFIED"
    assert checks(report)["PRODUCT_SESSION_AT_READ"].status == "SATISFIED"
    assert checks(report)["VERIFIED_LIVE_MARKET_STATUS"].status == "MISSING"


@pytest.mark.parametrize(
    "mutation",
    [
        "foreign_position",
        "foreign_workspace",
        "foreign_product",
        "quote_scope",
        "calendar_scope",
        "calendar_listing",
        "calendar_venue",
        "period_revision",
        "period_source",
        "period_range",
    ],
)
async def test_cross_owner_mismatch_fails_as_read_error_not_complete_or_missing_evidence(
    context, mutation
):
    foreign = UUID(int=7999)
    owner = context.state.owner
    if mutation == "foreign_position":
        position = replace(owner.execution_basis.valuation_basis.position, id=foreign)
        context.state.owner = replace(
            owner,
            execution_basis=replace(
                owner.execution_basis,
                valuation_basis=replace(owner.execution_basis.valuation_basis, position=position),
            ),
        )
    elif mutation in {"foreign_workspace", "foreign_product"}:
        trade = replace(
            owner.execution_basis.trade,
            **{"workspace_id" if mutation == "foreign_workspace" else "product_id": foreign},
        )
        context.state.owner = replace(
            owner, execution_basis=replace(owner.execution_basis, trade=trade)
        )
    elif mutation == "quote_scope":
        context.state.saved = replace(
            context.state.saved, route=replace(context.state.saved.route, position_id=foreign)
        )
    elif mutation.startswith("calendar_"):
        current = context.state.calendars["WARRANT"]
        changes = (
            {"instrument_id": foreign}
            if mutation == "calendar_scope"
            else {
                "binding": replace(
                    current.binding,
                    **{
                        (
                            "listing_id" if mutation == "calendar_listing" else "trading_venue_id"
                        ): foreign
                    },
                )
            }
        )
        context.state.calendars["WARRANT"] = replace(current, **changes)
    else:
        current = context.state.calendars["WARRANT"]
        changes = {
            "period_revision": dict(revision_id=foreign),
            "period_source": dict(source=replace(current.source, document_sha256="a" * 64)),
            "period_range": dict(start_date=NOW.date()),
        }[mutation]
        context.state.changes["WARRANT"] = changes
    with pytest.raises(ApplicationError) as error:
        await context.reader.read(**context.scope)
    assert error.value.code == "HEBELTRADER_ORIGINAL_BID_READ_INCONSISTENT"
    sessions.assert_passive_snapshot(context)


@pytest.mark.parametrize("state", ["CLOSED", "CANCELLED", "TRADE_CANCELLED"])
async def test_closed_and_cancelled_positions_cannot_obtain_current_qualification(context, state):
    owner = context.state.owner
    basis = owner.execution_basis
    if state == "TRADE_CANCELLED":
        basis = replace(basis, trade=replace(basis.trade, cancelled_at=NOW))
    else:
        position = basis.valuation_basis.position
        position = (
            replace(position, is_cancelled=True)
            if state == "CANCELLED"
            else replace(position, open_quantity=0, cost_basis=Decimal("0"), closed_at=NOW)
        )
        basis = replace(basis, valuation_basis=replace(basis.valuation_basis, position=position))
    context.state.owner = replace(owner, execution_basis=basis)
    report = await context.reader.read(**context.scope)
    assert report.coverage_status == "NOT_APPLICABLE"
    assert report.bid.status == "NOT_APPLICABLE"
    assert all(check.status == "NOT_APPLICABLE" for check in report.checks)
    assert report.underlying_sessions.count is None
    context.period_read.assert_not_awaited()


async def test_saved_payload_quality_and_source_corrections_change_audit_basis(context):
    before = await context.reader.read(**context.scope)
    saved = context.state.saved
    context.state.saved = replace(
        saved,
        provenance=replace(
            saved.provenance,
            raw_payload_fingerprint="a" * 64,
            warnings=("Synthetic replacement metadata",),
        ),
    )
    after = await context.reader.read(**context.scope)
    assert after.basis_id != before.basis_id
    assert after.economic_basis == before.economic_basis
    assert before.saved_quote == saved


async def test_execution_correction_uses_updated_owner_without_rewriting_earlier_report(context):
    before = await context.reader.read(**context.scope)
    owner = context.state.owner
    original_history = deepcopy(owner.execution_basis.history)
    original = original_history[0]
    correction = replace(
        original,
        id=UUID(int=7998),
        executed_at=original.executed_at - timedelta(days=1),
        supersedes_execution_id=original.id,
    )
    updated = executions.execution_basis([*original_history, correction])
    context.state.owner = replace(owner, execution_basis=updated)
    after = await context.reader.read(**context.scope)
    assert after.entry.execution_id == correction.id
    assert after.underlying_sessions.count.anchor_date == correction.executed_at.date()
    assert (
        after.underlying_sessions.count.completed_sessions
        == before.underlying_sessions.count.completed_sessions + 1
    )
    assert after.economic_basis is updated.valuation_basis
    assert (
        after.economic_basis.position.open_quantity == before.economic_basis.position.open_quantity
    )
    assert after.economic_basis.position.cost_basis == before.economic_basis.position.cost_basis
    assert after.basis_id != before.basis_id
    assert before.entry.execution_id == original.id
    assert owner.execution_basis.history == original_history
    assert original in updated.history and correction in updated.history


@pytest.mark.parametrize("failure", ["set", "timeout", "quote", "calendar"])
async def test_errors_always_close_snapshot_without_mutation(context, failure):
    error = DBAPIError("SYNTHETIC", {}, Exception("Synthetic database error"))
    if failure == "set":
        context.session.execute.side_effect = error
    elif failure == "timeout":
        context.session.execute.side_effect = [None, error]
    elif failure == "quote":
        context.quote_read.side_effect = error
    else:
        context.current_read.side_effect = error
    with pytest.raises(DBAPIError):
        await context.reader.read(**context.scope)
    context.session.rollback.assert_awaited_once_with()
    context.session.commit.assert_not_awaited()
    for name in ("add", "add_all", "delete", "flush"):
        getattr(context.session, name).assert_not_called()
