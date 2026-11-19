"""Owner-scope gates and event identity; no live source or database is involved."""

from dataclasses import asdict, replace
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest
from tests.unit.backend.features.position_monitoring import test_hebeltrader_deadlines as facts

from app.features.position_monitoring.domain.product_deadline_review import (
    decide_product_deadline_review,
)
from app.features.position_monitoring.service.product_deadline_review import (
    product_deadline_context,
    product_deadline_event_key,
    product_deadline_input_fingerprint,
)
from app.features.position_monitoring.service.product_deadline_review_inputs import (
    JSON_VALUE,
    ProductDeadlineInputs,
    product_deadline_evidence_problems,
)
from app.features.product.domain.review_evidence import ProductDeadlineEvidence

NOW = datetime(2026, 10, 12, 12, tzinfo=facts.ZONE)


def product():
    return ProductDeadlineEvidence(
        facts.WORKSPACE,
        facts.WARRANT,
        NOW,
        "AVAILABLE",
        (),
        UUID(int=9501),
        facts.KNOWN,
        "d" * 64,
        terms_id=UUID(int=9502),
        maturity_on=facts.TERM,
        last_trading_on=facts.TERM,
        exit_listing_id=facts.LISTING,
        exit_venue_mic="XFRA",
        source_reference="https://example.invalid/synthetic-original-product-dates",
        verification="MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION",
    )


def inputs(*, now=NOW, evidence=None, owner="e" * 64, calendar=None):
    evidence = evidence or replace(product(), known_at=now)
    calendar = calendar or facts.calendar()
    calculation = facts.evaluate(read=calendar, event_at=now)
    return ProductDeadlineInputs(
        facts.WORKSPACE,
        UUID(int=9503),
        UUID(int=9504),
        facts.WARRANT,
        owner,
        False,
        calculation,
        JSON_VALUE.dump_python(
            {
                "product_evidence": asdict(evidence),
                "product_calendar": {"current": asdict(calendar)},
                "warrant_isin": "DE000AB00001",
            },
            mode="json",
        ),
        (),
    )


def decision(value):
    return decide_product_deadline_review(
        closed=value.closed, calculation=value.calculation, input_problems=value.problems
    )


def problems(evidence):
    return product_deadline_evidence_problems(
        evidence, workspace_id=facts.WORKSPACE, warrant_id=facts.WARRANT, now=NOW
    )


def test_sufficient_product_facts_preserve_human_review_without_upgrade():
    assert problems(product()) == ()
    value = inputs()
    result = decision(value)
    context = product_deadline_context(value, result, "DEADLINE_REVIEW", uuid4(), uuid4(), NOW)
    assert context["product_verification"] == product().verification
    assert context["calendar_verification"] == facts.calendar().verification
    assert context["qualified_b05"] == "false"
    assert context["product_cutoff_status"] == "UNVERIFIED"
    assert context["execution_usable"] == "false"
    assert context["deadline_stage"] == "EXIT_SESSION_STARTED"
    assert context["scheduled_at"] != context["detected_at"]
    assert "bid" not in context and "observed_at" not in context


@pytest.mark.parametrize("field", ["workspace_id", "warrant_id"])
def test_foreign_product_facts_are_not_rebound_to_the_requested_position(field):
    assert problems(replace(product(), **{field: uuid4()})) == (
        "PRODUCT_DEADLINE_OWNER_SCOPE_MISMATCH",
    )


@pytest.mark.parametrize("status", ["MISSING", "UNSUITABLE"])
def test_absent_or_retracted_product_evidence_is_not_last_good(status):
    result = problems(replace(product(), status=status, reasons=("SOURCE_WITHDRAWN",)))
    assert "SOURCE_WITHDRAWN" in result
    assert "PRODUCT_DEADLINE_EVIDENCE_UNAVAILABLE" in result


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("known_at", NOW.replace(tzinfo=None)),
        ("known_at", NOW + timedelta(seconds=1)),
        ("known_at", NOW - timedelta(seconds=1)),
        ("recorded_at", None),
        ("recorded_at", NOW.replace(tzinfo=None)),
        ("recorded_at", NOW + timedelta(seconds=1)),
    ],
)
def test_product_evidence_must_share_the_current_aware_knowledge_boundary(field, value):
    assert "PRODUCT_DEADLINE_KNOWLEDGE_TIME_INVALID" in problems(
        replace(product(), **{field: value})
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("revision_id", None),
        ("fingerprint", ""),
        ("terms_id", None),
        ("source_reference", None),
        ("verification", ""),
    ],
)
def test_no_bare_dates_without_original_owner_provenance(field, value):
    assert "PRODUCT_DEADLINE_PROVENANCE_MISSING" in problems(replace(product(), **{field: value}))


@pytest.mark.parametrize(
    ("field", "reason"),
    [
        ("maturity_on", "PRODUCT_MATURITY_EVIDENCE_MISSING"),
        ("last_trading_on", "PRODUCT_LAST_TRADING_DAY_EVIDENCE_MISSING"),
        ("exit_listing_id", "PRODUCT_EXIT_LISTING_MISSING"),
        ("exit_venue_mic", "PRODUCT_EXIT_LISTING_MISSING"),
    ],
)
def test_each_necessary_date_and_personal_listing_is_required(field, reason):
    assert reason in problems(replace(product(), **{field: None}))


def test_later_read_of_same_facts_is_same_assessment_and_same_logical_event():
    first = inputs()
    later = inputs(now=NOW + timedelta(minutes=15))
    assert product_deadline_input_fingerprint(first, decision(first)) == (
        product_deadline_input_fingerprint(later, decision(later))
    )
    assert product_deadline_event_key(first, decision(first)) == (
        product_deadline_event_key(later, decision(later))
    )


@pytest.mark.parametrize("changed_owner", ["economic", "product", "calendar"])
def test_real_owner_correction_is_new_assessment_but_same_unchanged_deadline_event(changed_owner):
    first = inputs()
    changed = inputs(
        owner="f" * 64 if changed_owner == "economic" else first.owner_basis_id,
        evidence=(
            replace(product(), revision_id=uuid4(), fingerprint="f" * 64)
            if changed_owner == "product"
            else None
        ),
        calendar=(
            replace(facts.calendar(), revision_id=uuid4(), fingerprint="f" * 64)
            if changed_owner == "calendar"
            else None
        ),
    )
    assert product_deadline_input_fingerprint(first, decision(first)) != (
        product_deadline_input_fingerprint(changed, decision(changed))
    )
    assert product_deadline_event_key(first, decision(first)) == (
        product_deadline_event_key(changed, decision(changed))
    )


def test_stage_change_has_a_distinct_business_event_without_a_new_provider_read():
    first = inputs()
    after = inputs(now=datetime(2026, 10, 12, 22, tzinfo=facts.ZONE))
    assert product_deadline_event_key(first, decision(first)) != (
        product_deadline_event_key(after, decision(after))
    )
    assert decision(after).outcome == "CALENDAR_SESSION_ENDED"


def test_data_problem_notice_has_no_actionable_event_key():
    value = replace(inputs(), problems=("PRODUCT_DEADLINE_EVIDENCE_UNAVAILABLE",))
    result = decision(value)
    assert product_deadline_event_key(value, result) is None
    context = product_deadline_context(value, result, "DATA_UNAVAILABLE", uuid4(), uuid4(), NOW)
    assert context["deadline_event_key"] is None
    assert context["data_problem_reasons"] == "PRODUCT_DEADLINE_EVIDENCE_UNAVAILABLE"
