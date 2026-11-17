"""Pure B05 preparation with explicit synthetic Product inputs and calendar rows."""

from copy import deepcopy
from dataclasses import asdict, replace
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from app.features.market_data.domain.session_evidence import (
    MAX_SESSION_DAYS,
    SessionBinding,
    SessionDay,
    SessionEvidenceRead,
    SessionSourceProvenance,
    SessionWindow,
)
from app.features.position_monitoring.domain.hebeltrader_deadlines import (
    calculate_product_deadline,
)

WORKSPACE, WARRANT, LISTING = (UUID(int=value) for value in (9101, 9102, 9103))
ZONE = ZoneInfo("Europe/Berlin")
KNOWN = datetime(2026, 1, 1, tzinfo=UTC)
NOW = datetime(2026, 10, 9, 7, tzinfo=ZONE)
TERM = date(2026, 11, 1)


def source():
    return SessionSourceProvenance(
        manifest_sha256="a" * 64,
        document_sha256="b" * 64,
        document_filename="synthetic-product-calendar.txt",
        document_media_type="text/plain",
        publisher="Synthetic exchange calendar publisher",
        reference="https://example.invalid/synthetic-product-calendar",
        published_at=KNOWN,
        published_on=None,
        retrieved_at=KNOWN,
        reviewed_at=KNOWN,
        review_reference="Synthetic manual comparison of the complete original calendar",
        recorded_by=UUID(int=9104),
    )


def calendar(start=date(2026, 10, 1), end=date(2026, 10, 31), closed=()):
    # Every row is an explicit synthetic fact. Production must never manufacture
    # weekends, public holidays or regular session clocks this way.
    rows = []
    for offset in range((end - start).days + 1):
        day = start + timedelta(days=offset)
        rows.append(
            SessionDay(
                session_date=day,
                status="CLOSED" if day in closed else "SESSION",
                intervals=(
                    ()
                    if day in closed
                    else (
                        SessionWindow(
                            datetime.combine(day, time(8), ZONE),
                            datetime.combine(day, time(22), ZONE),
                        ),
                    )
                ),
                source_reference=f"Synthetic original document, explicit row {day}",
            )
        )
    return SessionEvidenceRead(
        workspace_id=WORKSPACE,
        instrument_kind="WARRANT",
        instrument_id=WARRANT,
        start_date=start,
        end_date=end,
        known_at=KNOWN,
        revision_id=UUID(int=9110),
        supersedes_revision_id=None,
        revision_number=1,
        calendar_id="synthetic-product-calendar",
        calendar_version="synthetic-version-1",
        binding=SessionBinding(
            instrument_kind="WARRANT",
            instrument_id=WARRANT,
            listing_id=LISTING,
            trading_venue_id=UUID(int=9111),
            venue_mic="XFRA",
            timezone="Europe/Berlin",
            market_segment="Synthetic fixed product exit listing",
            valid_from=date(2026, 1, 1),
            valid_through=date(2027, 12, 31),
        ),
        coverage_start=start,
        coverage_end=end,
        evidence_status="ACTIVE",
        days=tuple(rows),
        status="COMPLETE",
        reasons=(),
        missing_dates=(),
        source=source(),
        fingerprint="c" * 64,
        recorded_at=KNOWN,
        read_at=NOW,
    )


def evaluate(read=None, **changes):
    return calculate_product_deadline(
        **(
            dict(
                workspace_id=WORKSPACE,
                warrant_id=WARRANT,
                exit_listing_id=LISTING,
                maturity_on=TERM,
                last_trading_on=TERM,
                calendar=calendar() if read is None else read,
                event_at=NOW,
            )
            | changes
        )
    )


def test_twentieth_previous_documented_session_excludes_term_and_closed_days():
    read = calendar(end=TERM, closed=(date(2026, 10, 11), date(2026, 10, 18)))
    before = deepcopy(asdict(read))
    result = evaluate(read)
    assert result.status == "AVAILABLE"
    assert result.relevant_product_date == TERM
    assert result.exit_session_date == date(2026, 10, 10)
    assert result.warning_session_date == date(2026, 10, 9)
    assert result.warning_at == datetime(2026, 10, 9, 8, tzinfo=ZONE)
    assert len(result.preceding_session_dates) == 20
    assert TERM not in result.preceding_session_dates
    assert result.stage == "BEFORE_WARNING"
    assert asdict(read) == before
    assert result.scope == "DOCUMENTED_CALENDAR_CALCULATION_ONLY"
    assert result.rule_status == "B05_NOT_ACTIVATED"
    assert result.calendar_verification == "MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION"


@pytest.mark.parametrize("closed_term", [False, True])
def test_term_day_never_counts_even_when_documented_as_closed(closed_term):
    read = calendar(end=TERM, closed=(TERM,) if closed_term else ())
    result = evaluate(read)
    assert result.exit_session_date == date(2026, 10, 12)
    assert result.warning_session_date == date(2026, 10, 11)


@pytest.mark.parametrize("earlier_field", ["maturity_on", "last_trading_on"])
def test_b17_uses_earlier_required_product_date(earlier_field):
    changes = {"maturity_on": date(2026, 11, 5), "last_trading_on": date(2026, 11, 5)}
    changes[earlier_field] = TERM
    result = evaluate(**changes)
    assert result.relevant_product_date == TERM
    assert result.exit_session_date == date(2026, 10, 12)


@pytest.mark.parametrize(
    ("count", "status", "reason"),
    [
        (19, "NOT_ASSESSABLE", "TWENTY_PRODUCT_SESSIONS_MISSING"),
        (20, "PARTIAL", "PREWARNING_PRODUCT_SESSION_MISSING"),
        (21, "AVAILABLE", None),
    ],
)
def test_nineteen_twenty_and_twenty_one_sessions_preserve_warning_coverage(count, status, reason):
    read = calendar(start=TERM - timedelta(days=count))
    result = evaluate(read)
    assert result.status == status
    assert result.reasons == ((reason,) if reason else ())
    assert (result.exit_session_date is not None) is (count >= 20)
    assert (result.warning_at is not None) is (count >= 21)


@pytest.mark.parametrize(
    ("instant", "stage"),
    [
        (datetime(2026, 10, 11, 7, 59, 59, tzinfo=ZONE), "BEFORE_WARNING"),
        (datetime(2026, 10, 11, 8, tzinfo=ZONE), "WARNING_DUE"),
        (datetime(2026, 10, 12, 7, 59, 59, tzinfo=ZONE), "WARNING_DUE"),
        (datetime(2026, 10, 12, 8, tzinfo=ZONE), "EXIT_SESSION_STARTED"),
        (datetime(2026, 10, 12, 21, 59, 59, tzinfo=ZONE), "EXIT_SESSION_STARTED"),
        (datetime(2026, 10, 12, 22, tzinfo=ZONE), "CALENDAR_SESSION_ENDED"),
        (datetime(2026, 12, 1, 12, tzinfo=ZONE), "CALENDAR_SESSION_ENDED"),
    ],
)
def test_original_b19_opening_and_late_discovery_never_shift_deadline(instant, stage):
    result = evaluate(event_at=instant)
    assert result.stage == stage
    assert result.exit_session_date == date(2026, 10, 12)
    assert result.warning_at == datetime(2026, 10, 11, 8, tzinfo=ZONE)
    assert result.evaluated_at == instant


def test_shortened_multiple_interval_session_preserves_actual_calendar_clocks():
    read = calendar()
    exit_day = date(2026, 10, 12)
    windows = tuple(
        SessionWindow(
            datetime.combine(exit_day, time(start), ZONE),
            datetime.combine(exit_day, time(end), ZONE),
        )
        for start, end in ((8, 10), (11, 14))
    )
    read = replace(
        read,
        days=tuple(
            replace(day, intervals=windows) if day.session_date == exit_day else day
            for day in read.days
        ),
    )
    at_break = evaluate(read, event_at=datetime.combine(exit_day, time(10, 30), ZONE))
    at_close = evaluate(read, event_at=windows[-1].closes_at)
    assert at_break.stage == "EXIT_SESSION_STARTED"
    assert at_close.stage == "CALENDAR_SESSION_ENDED"
    assert at_close.calendar_session_closes_at == windows[-1].closes_at
    assert len(at_close.preceding_session_dates) == 20


def test_dst_fold_compares_instants_and_does_not_invent_instrument_deadline():
    read = calendar(start=date(2026, 10, 24), end=date(2026, 11, 13))
    close = datetime(2026, 10, 25, 2, 30, tzinfo=ZONE, fold=1)
    windows = (SessionWindow(datetime(2026, 10, 25, 1, tzinfo=ZONE), close),)
    read = replace(
        read, days=(read.days[0], replace(read.days[1], intervals=windows), *read.days[2:])
    )
    changes = dict(maturity_on=date(2026, 11, 14), last_trading_on=date(2026, 11, 14))
    before = evaluate(read, event_at=datetime(2026, 10, 25, 2, 45, tzinfo=ZONE, fold=0), **changes)
    at = evaluate(read, event_at=close.astimezone(UTC), **changes)
    assert before.stage == "EXIT_SESSION_STARTED"
    assert at.stage == "CALENDAR_SESSION_ENDED"
    assert at.calendar_session_closes_at == close
    assert at.scope == "DOCUMENTED_CALENDAR_CALCULATION_ONLY"


def test_explicit_calendar_rows_across_year_end_preserve_documented_closures():
    # Synthetic fixture follows the documented day pattern, not an inferred
    # production calendar. The input explicitly supplies every closed day.
    closures = tuple(
        date.fromisoformat(day)
        for day in (
            "2026-12-12",
            "2026-12-13",
            "2026-12-19",
            "2026-12-20",
            "2026-12-24",
            "2026-12-25",
            "2026-12-26",
            "2026-12-27",
            "2026-12-31",
            "2027-01-01",
            "2027-01-02",
            "2027-01-03",
            "2027-01-09",
            "2027-01-10",
        )
    )
    read = calendar(start=date(2026, 12, 11), end=date(2027, 1, 14), closed=closures)
    result = evaluate(read, maturity_on=date(2027, 1, 15), last_trading_on=date(2027, 1, 15))
    assert result.exit_session_date == date(2026, 12, 14)
    assert result.warning_session_date == date(2026, 12, 11)
    assert result.relevant_product_date == date(2027, 1, 15)


@pytest.mark.parametrize("kind", ["missing", "unknown", "duplicate", "unsorted"])
def test_incomplete_or_conflicted_days_are_not_weekends_or_zero_sessions(kind):
    read = calendar()
    first = read.days[0]
    rows = {
        "missing": read.days[1:],
        "unknown": (replace(first, status="UNKNOWN", intervals=()), *read.days[1:]),
        "duplicate": (first, *read.days),
        "unsorted": tuple(reversed(read.days)),
    }
    result = evaluate(replace(read, days=rows[kind]))
    assert result.status == "NOT_ASSESSABLE"
    assert result.exit_session_date is None
    assert result.preceding_session_dates == ()


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"maturity_on": None}, "PRODUCT_MATURITY_EVIDENCE_MISSING"),
        ({"last_trading_on": None}, "PRODUCT_LAST_TRADING_DAY_EVIDENCE_MISSING"),
        ({"exit_listing_id": None}, "PRODUCT_EXIT_LISTING_MISSING"),
        ({"calendar": None}, "PRODUCT_SESSION_EVIDENCE_MISSING"),
        ({"last_trading_on": date.min}, "PRODUCT_DATE_HAS_NO_PRECEDING_SESSION_RANGE"),
        ({"exit_listing_id": UUID(int=999)}, "PRODUCT_SESSION_SCOPE_MISMATCH"),
        ({"warrant_id": UUID(int=999)}, "PRODUCT_SESSION_SCOPE_MISMATCH"),
        ({"workspace_id": UUID(int=999)}, "PRODUCT_SESSION_SCOPE_MISMATCH"),
    ],
)
def test_missing_owner_inputs_never_fall_back_to_other_dates_or_listings(changes, reason):
    result = evaluate(**changes)
    assert result.status == "NOT_ASSESSABLE"
    assert reason in result.reasons


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "INCOMPLETE"},
        {"evidence_status": "WITHDRAWN"},
        {"source": None},
        {"revision_id": None},
        {"missing_dates": (date(2026, 10, 2),)},
        {"reasons": ("SESSION_OWNER_BINDING_CHANGED",)},
        {"instrument_kind": "UNDERLYING"},
        {"binding": None},
        {"recorded_at": KNOWN + timedelta(seconds=1)},
        {"recorded_at": None},
        {"known_at": NOW + timedelta(seconds=1)},
        {"known_at": KNOWN.replace(tzinfo=None)},
        {"end_date": date(2026, 10, 30)},
        {"coverage_end": date(2026, 10, 30)},
        {"coverage_start": date(2026, 10, 2)},
    ],
)
def test_owner_scope_quality_knowledge_and_range_are_required(changes):
    result = evaluate(replace(calendar(), **changes))
    assert result.status == "NOT_ASSESSABLE"
    assert result.exit_session_date is result.warning_at is None


def test_source_revision_changes_result_without_rewriting_prior_calculation():
    first = calendar()
    original = evaluate(first)
    changed = replace(
        first,
        revision_id=UUID(int=9112),
        supersedes_revision_id=first.revision_id,
        revision_number=2,
        fingerprint="d" * 64,
        days=tuple(
            (
                replace(day, status="CLOSED", intervals=())
                if day.session_date == date(2026, 10, 31)
                else day
            )
            for day in first.days
        ),
    )
    revised = evaluate(changed)
    assert original.exit_session_date == date(2026, 10, 12)
    assert revised.exit_session_date == date(2026, 10, 11)
    assert original.calendar_revision_id == first.revision_id
    assert revised.calendar_revision_id == changed.revision_id
    assert original.calendar_fingerprint != revised.calendar_fingerprint


def test_range_limit_and_naive_clock_fail_before_synthetic_calendar_generation():
    read = calendar()
    start = TERM - timedelta(days=MAX_SESSION_DAYS + 1)
    read = replace(
        read,
        start_date=start,
        coverage_start=start,
        binding=replace(read.binding, valid_from=start),
    )
    assert evaluate(read).reasons == ("PRODUCT_SESSION_RANGE_LIMIT",)
    with pytest.raises(ValueError, match="timezone-aware"):
        evaluate(event_at=NOW.replace(tzinfo=None))
