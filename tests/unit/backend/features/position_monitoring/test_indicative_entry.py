"""Synthetic review policy and durable SQLite history; no external adapter exists."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from tests.unit.backend.features.position_monitoring.test_hebeltrader_loss import (
    SqlSession,
)
from tests.unit.backend.features.position_monitoring.test_hebeltrader_original_bid import (
    NOW,
    saved_example,
)

from app.features.alert.persistence.models import AlertModel
from app.features.market_data.domain.issuer_indications import ISSUER_INDICATIONS
from app.features.notification.persistence.models import (
    NotificationDeliveryAttemptModel,
    NotificationModel,
)
from app.features.position_monitoring.domain.indicative_entry import (
    RULE_SCOPE,
    IndicativeQuote,
    decide_indicative_entry,
    qualify_review_quote,
)
from app.features.position_monitoring.persistence.indicative_entry import (
    IndicativeEntryAssessmentModel as Assessment,
)
from app.features.position_monitoring.persistence.indicative_entry import (
    IndicativeEntryEpisodeModel as Episode,
)
from app.features.position_monitoring.service.indicative_entry import (
    IndicativeEntryService,
)
from app.features.position_monitoring.service.indicative_entry_inputs import (
    IndicativeInputs,
)


def issuer_saved(provider="MORGAN_STANLEY", *, age=0):
    saved = saved_example()
    mode, basis, _policy, _warning = ISSUER_INDICATIONS[provider]
    return replace(
        saved,
        provider=provider,
        retrieved_at=NOW - timedelta(seconds=age),
        quote=replace(
            saved.quote,
            original_evidence=None,
            observed_at=None,
            source_mode=mode,
            quote_time_basis=basis,
            quote_time_text="Original source text with unknown date or zone",
            provider_exchange_code="ISSUER",
        ),
    )


@pytest.mark.parametrize("age,usable", [(0, True), (900, True), (901, False)])
def test_original_bid_age_and_separate_side_clock(age, usable):
    saved = saved_example(bid_age=timedelta(seconds=age))
    result = qualify_review_quote(saved, now=NOW, selection_policy=None)
    assert result.usable is usable
    assert result.original_bid_at == NOW - timedelta(seconds=age)
    if usable:
        assert result.evaluation_mode == "SOURCE_BID"
        assert result.session_event_at == saved.quote.original_evidence.bid.observed_at
        assert result.session_event_at != saved.quote.observed_at  # older Ask/common time


@pytest.mark.parametrize("provider", ["JPMORGAN", "MORGAN_STANLEY"])
@pytest.mark.parametrize("age,usable", [(0, True), (300, True), (301, False)])
def test_registered_issuer_receipt_never_becomes_original_time(provider, age, usable):
    result = qualify_review_quote(
        issuer_saved(provider, age=age),
        now=NOW,
        selection_policy=ISSUER_INDICATIONS[provider][2],
    )
    assert result.usable is usable
    assert result.original_bid_at is None
    if usable:
        assert result.evaluation_mode == "INDICATIVE_ISSUER"
        assert result.session_event_at == NOW
        assert result.ordering_at == NOW - timedelta(seconds=age)


@pytest.mark.parametrize("change", ["bid", "side", "policy", "retained", "refresh", "future"])
def test_price_and_clock_substitutes_are_rejected(change):
    saved = issuer_saved() if change == "policy" else saved_example()
    if change == "bid":
        saved = replace(
            saved,
            quote=replace(
                saved.quote,
                bid=None,
                ask=None,
                original_evidence=None,
                reference_price=Decimal("1"),
                reference_price_type="LAST_TRADE",
            ),
        )
    elif change == "side":
        saved = replace(saved, quote=replace(saved.quote, original_evidence=None))
    elif change == "retained":
        saved = replace(saved, quote=replace(saved.quote, retained=True))
    elif change == "refresh":
        saved = replace(saved, quote=replace(saved.quote, refresh_error="TRANSPORT_ERROR"))
    elif change == "future":
        saved = replace(saved, retrieved_at=NOW + timedelta(seconds=1))
    result = qualify_review_quote(saved, now=NOW, selection_policy="UNCONFIRMED")
    assert not result.usable


def quote(**changes):
    return replace(
        IndicativeQuote(Decimal("1"), "EUR", NOW, NOW, "SOURCE_BID", NOW, NOW, ()),
        **changes,
    )


def decision(**changes):
    return decide_indicative_entry(
        **{
            "closed": False,
            "gross_entry": Decimal("2"),
            "remaining_quantity": 80,
            "quote": quote(),
            "review_completed_sessions": 20,
            "completed_sessions": 20,
            "input_problems": (),
        }
        | changes
    )


def test_twentieth_close_between_bid_and_read_only_makes_review_due():
    result = decision(completed_sessions=19, review_completed_sessions=20)
    assert result.outcome == "NOT_REACHED" and result.review_due is True
    assert decision(completed_sessions=20).outcome == "BELOW_ENTRY"
    assert decision(completed_sessions=19, review_completed_sessions=19).review_due is False


def test_data_problem_never_claims_price_recovery_or_cancels_independent_reminder():
    result = decision(quote=quote(bid=None), input_problems=("NO_BID",))
    assert result.outcome == "UNAVAILABLE" and result.review_due is True
    assert IndicativeEntryService._desired("ENTRY_LOSS", result) is None
    assert IndicativeEntryService._desired("REVIEW_DUE", result) is True
    assert decision(quote=quote(bid=Decimal("2"))).outcome == "AT_OR_ABOVE_ENTRY"


@pytest.fixture
def durable(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/synthetic_indicative_review_only.db")
    for model in (
        AlertModel,
        Assessment,
        Episode,
        NotificationModel,
        NotificationDeliveryAttemptModel,
    ):
        model.__table__.create(engine)
    saved = saved_example()
    material = {
        "economic_basis": {
            "cost_basis_currency": "EUR",
            "position": {"average_entry_price": "2", "open_quantity": 80},
        },
        "warrant_name": "Synthetic review warrant",
        "warrant_isin": saved.quote.isin,
        "warrant_wkn": "TEST01",
    }
    inputs = IndicativeInputs(
        saved.route.workspace_id,
        uuid4(),
        saved.route.position_id,
        "1" * 64,
        False,
        saved,
        quote(),
        None,
        None,
        material,
        (),
    )
    yield engine, inputs
    engine.dispose()


async def persist(engine, inputs, value, index, previous=None, duplicate=False, notify=True):
    with Session(engine, expire_on_commit=False) as raw:
        return await IndicativeEntryService(SqlSession(raw))._persist(
            inputs,
            value,
            str(index).zfill(64),
            previous,
            duplicate,
            NOW + timedelta(seconds=index),
            notify,
        )


@pytest.mark.asyncio
async def test_loss_gap_repeat_recovery_reentry_restart_full_sale(durable):
    engine, inputs = durable
    first = await persist(engine, inputs, decision(), 1)
    assert first.alerts_created == first.notifications_created == 2
    assert first.loss_episode_active and first.review_due
    repeat = await persist(engine, inputs, decision(), 1, first.assessment_id, True)
    assert repeat.unchanged and repeat.alerts_created == repeat.notifications_created == 0
    gap = await persist(
        engine, inputs, decision(input_problems=("NO_BID",)), 2, first.assessment_id
    )
    assert gap.data_problem_active and gap.loss_episode_active and gap.alerts_created == 1
    again = await persist(
        engine, inputs, decision(input_problems=("NO_BID",)), 2, gap.assessment_id, True
    )
    assert again.alerts_created == again.notifications_created == 0
    recovered = await persist(
        engine, inputs, decision(quote=quote(bid=Decimal("2"))), 3, gap.assessment_id
    )
    assert not recovered.data_problem_active and not recovered.loss_episode_active
    assert recovered.review_due
    second = await persist(engine, inputs, decision(), 4, recovered.assessment_id)
    assert second.loss_episode_active and second.alerts_created == 1
    closed = await persist(
        engine,
        inputs,
        decision(closed=True, remaining_quantity=0),
        5,
        second.assessment_id,
    )
    assert not any((closed.review_due, closed.data_problem_active, closed.loss_episode_active))
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Assessment)) == 5
        assert session.scalar(select(func.count()).select_from(Episode)) == 4
        notices = session.scalars(select(AlertModel)).all()
        assert {row.status for row in notices} == {"RESOLVED"}
        assert {row.price_context["scope"] for row in notices} == {RULE_SCOPE}
        assert {row.price_context["qualified_b04"] for row in notices} == {"false"}
        for row in notices:
            if row.alert_type != "INDICATIVE_ENTRY_LOSS":
                assert row.observed_value is row.threshold_value is None
        assert {row.status for row in session.scalars(select(NotificationModel))} == {"FAILED"}
        assert {
            row.error_code for row in session.scalars(select(NotificationDeliveryAttemptModel))
        } == {"REVIEW_ALERT_RESOLVED", "REVIEW_POSITION_CLOSED"}


@pytest.mark.asyncio
async def test_correction_partial_sale_and_source_change_preserve_logical_notices(
    durable,
):
    engine, inputs = durable
    first = await persist(engine, inputs, decision(), 1)
    changed = replace(
        inputs, owner_basis_id="9" * 64, saved=replace(inputs.saved, provider="OTHER")
    )
    corrected = await persist(
        engine,
        changed,
        decision(gross_entry=Decimal("3"), remaining_quantity=60),
        2,
        first.assessment_id,
    )
    assert corrected.alerts_created == corrected.notifications_created == 0
    assert corrected.loss_episode_active and corrected.review_due
    with Session(engine) as session:
        assert session.get(Assessment, corrected.assessment_id).owner_basis_id == "9" * 64
        assert session.scalar(select(func.count()).select_from(Episode)) == 2


@pytest.mark.asyncio
async def test_late_channel_enable_recovers_outbox_without_duplicate_alerts(durable):
    engine, inputs = durable
    first = await persist(engine, inputs, decision(), 1, notify=False)
    assert first.notifications_created == 0
    enabled = await persist(engine, inputs, decision(), 1, first.assessment_id, True)
    assert enabled.alerts_created == 0 and enabled.notifications_created == 2
    repeated = await persist(engine, inputs, decision(), 1, first.assessment_id, True)
    assert repeated.notifications_created == 0


def test_order_and_same_time_conflicts_do_not_recover(durable):
    _, inputs = durable
    count = SimpleNamespace(completed_sessions=20)
    inputs = replace(inputs, review_count=count, comparison_count=count)
    previous = SimpleNamespace(
        ordering_at=NOW,
        result={"bid": "1", "evaluation_mode": "SOURCE_BID"},
        inputs={
            "saved_quote": {
                "provider": inputs.saved.provider,
                "route": {"identity_key": inputs.saved.route.identity_key},
            }
        },
    )
    for alternative in (
        quote(bid=Decimal("3"), ordering_at=NOW - timedelta(seconds=1)),
        quote(bid=Decimal("3")),
    ):
        result = IndicativeEntryService._decision(replace(inputs, quote=alternative), previous)
        assert result.outcome == "UNAVAILABLE"
        assert IndicativeEntryService._desired("ENTRY_LOSS", result) is None


def test_source_or_time_semantics_change_is_not_an_original_time_ordering_claim(
    durable,
):
    _, inputs = durable
    count = SimpleNamespace(completed_sessions=20)
    inputs = replace(inputs, review_count=count, comparison_count=count)
    previous = SimpleNamespace(
        ordering_at=NOW + timedelta(seconds=10),
        result={"bid": "1", "evaluation_mode": "INDICATIVE_ISSUER"},
        inputs={
            "saved_quote": {
                "provider": "MORGAN_STANLEY",
                "route": {"identity_key": "other-route"},
            }
        },
    )
    result = IndicativeEntryService._decision(
        replace(inputs, quote=quote(bid=Decimal("3"))), previous
    )
    assert result.outcome == "AT_OR_ABOVE_ENTRY"


def test_read_clock_and_same_gap_do_not_enter_fingerprint(durable):
    _, inputs = durable
    first = replace(inputs, material={**inputs.material, "product_scale": {"review_at": NOW}})
    later = replace(
        first,
        material={
            **first.material,
            "product_scale": {"review_at": NOW + timedelta(seconds=1)},
        },
    )
    assert IndicativeEntryService._input_fingerprint(first, decision()) == (
        IndicativeEntryService._input_fingerprint(later, decision())
    )


def test_original_status_facts_bind_assessment_without_delivery_clock_or_gap_churn(
    durable,
):
    _, inputs = durable
    point = {
        "fingerprint": "a" * 64,
        "original": {"status": "CLOSED", "observed_at": NOW.isoformat()},
        "captured_at": NOW.isoformat(),
    }

    def bound(**status):
        return replace(inputs, material={**inputs.material, "status_observations": status})

    value = decision(input_problems=("REVIEW_LATER_NEGATIVE_STATUS_OBSERVED",))
    first = IndicativeEntryService._input_fingerprint(
        bound(latest_observations=[point], latest_capture=point), value
    )
    # Owner fact identity excludes delivery/request clocks. Receiving a duplicate
    # point, or another copy of an already known gap, is not a new assessment.
    delivered_again = {**point, "captured_at": (NOW + timedelta(seconds=1)).isoformat()}
    gap = {"fingerprint": "b" * 64, "original": None, "reason": "HTTP_503"}
    for capture in (delivered_again, gap, {**gap, "fingerprint": "c" * 64}):
        assert (
            IndicativeEntryService._input_fingerprint(
                bound(latest_observations=[point, delivered_again], latest_capture=capture),
                value,
            )
            == first
        )


@pytest.mark.parametrize("changed_fact", ["status", "original_clock", "source_binding"])
def test_changed_original_status_fact_is_not_hidden_by_same_problem_reason(durable, changed_fact):
    _, inputs = durable
    original = {
        "status": "CLOSED",
        "observed_at": NOW.isoformat(),
        "source_reference": "one",
    }
    point = {
        "fingerprint": "a" * 64,
        "original": original,
        "captured_at": NOW.isoformat(),
    }
    changes = {
        "status": {"status": "SUSPENDED"},
        "original_clock": {"observed_at": (NOW - timedelta(seconds=1)).isoformat()},
        "source_binding": {"source_reference": "two"},
    }
    # The status owner supplies the new bound fingerprint for each changed
    # original fact; the consumer does not recalculate or invent that identity.
    changed = {
        **point,
        "fingerprint": "b" * 64,
        "original": {**original, **changes[changed_fact]},
    }
    first = replace(
        inputs,
        material={
            **inputs.material,
            "status_observations": {"latest_observations": [point]},
        },
    )
    later = replace(
        first,
        material={
            **first.material,
            "status_observations": {
                "latest_observations": [point],
                "latest_capture": changed,
            },
        },
    )
    value = decision(input_problems=("REVIEW_LATER_NEGATIVE_STATUS_OBSERVED",))
    assert IndicativeEntryService._input_fingerprint(first, value) != (
        IndicativeEntryService._input_fingerprint(later, value)
    )


@pytest.mark.asyncio
async def test_review_event_is_once_per_entry_and_twentieth_threshold_even_after_revision(
    durable,
):
    engine, inputs = durable
    inputs = replace(
        inputs, material={**inputs.material, "entry": {"execution_id": "original-buy"}}
    )
    first = await persist(engine, inputs, decision(), 1)
    withdrawn = await persist(
        engine,
        inputs,
        decision(review_completed_sessions=None, input_problems=("CALENDAR_WITHDRAWN",)),
        2,
        first.assessment_id,
    )
    assert withdrawn.alerts_created == 1  # separate data episode only
    corrected = await persist(
        engine,
        inputs,
        decision(review_completed_sessions=19, completed_sessions=19),
        3,
        withdrawn.assessment_id,
    )
    assert not corrected.review_due
    restored = await persist(engine, inputs, decision(), 4, corrected.assessment_id)
    assert restored.review_due and restored.alerts_created == 0  # already reported same event
    new_entry = replace(
        inputs, material={**inputs.material, "entry": {"execution_id": "corrected-buy"}}
    )
    changed = await persist(engine, new_entry, decision(), 5, restored.assessment_id)
    assert changed.alerts_created == 1
    with Session(engine) as session:
        reminders = session.scalars(select(Episode).where(Episode.kind == "REVIEW_DUE")).all()
        assert len(reminders) == 2
        assert len({row.event_key for row in reminders}) == 2


def test_restart_does_not_erase_a_failed_refresh_of_the_same_saved_quote(durable):
    _, inputs = durable
    saved = {
        "provider": "FRANKFURT_QUOTES",
        "identity_key": "route",
        "retrieved_at": "receipt-1",
        "provenance": {"raw_payload_fingerprint": "price-1"},
    }
    inputs = replace(inputs, material={**inputs.material, "saved_quote": saved})
    failed = IndicativeEntryService._preserve_refresh_failure(inputs, None, True)
    previous = SimpleNamespace(inputs=failed.material)
    restarted = IndicativeEntryService._preserve_refresh_failure(inputs, previous, False)
    assert "REVIEW_QUOTE_REFRESH_FAILED" in restarted.problems
    rewrapped = replace(
        inputs,
        material={
            **inputs.material,
            "saved_quote": {
                **saved,
                "provenance": {"raw_payload_fingerprint": "changed-request-envelope"},
            },
        },
    )
    assert "REVIEW_QUOTE_REFRESH_FAILED" in (
        IndicativeEntryService._preserve_refresh_failure(rewrapped, previous, False).problems
    )
    newer = replace(
        inputs,
        material={
            **inputs.material,
            "saved_quote": {
                **saved,
                "retrieved_at": "receipt-2",
                "provenance": {"raw_payload_fingerprint": "price-2"},
            },
        },
    )
    assert IndicativeEntryService._preserve_refresh_failure(newer, previous, False).problems == ()
    closed = replace(inputs, closed=True)
    assert IndicativeEntryService._preserve_refresh_failure(closed, previous, True) is closed
