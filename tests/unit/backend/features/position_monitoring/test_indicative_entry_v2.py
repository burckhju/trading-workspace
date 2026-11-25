"""V2 policy and durable family transitions in disposable synthetic SQLite only."""

from dataclasses import asdict, replace
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests.unit.backend.features.position_monitoring import (
    test_hebeltrader_product_price_scale as scales,
)
from tests.unit.backend.features.position_monitoring import (
    test_indicative_entry as legacy,
)
from tests.unit.backend.features.position_monitoring.test_hebeltrader_loss import (
    SqlSession,
)
from tests.unit.backend.features.position_monitoring.test_hebeltrader_original_bid import (
    NOW,
    saved_example,
)
from tests.unit.backend.features.product.test_listing_unit_review_composition import (
    current_listing_evidence,
)

from app.features.notification.persistence.models import NotificationModel
from app.features.position_monitoring.domain.indicative_entry import (
    qualify_review_quote,
)
from app.features.position_monitoring.domain.indicative_policy import (
    V1_POLICY,
    V2_POLICY,
)
from app.features.position_monitoring.persistence.indicative_entry import (
    IndicativeEntryAssessmentModel as Assessment,
)
from app.features.position_monitoring.persistence.indicative_entry import (
    IndicativeEntryEpisodeModel as Episode,
)
from app.features.position_monitoring.service.indicative_entry import (
    IndicativeEntryService,
    latest_indicative_assessment,
)
from app.features.position_monitoring.service.indicative_entry_inputs import (
    JSON_VALUE,
    _scale,
    supply_problems,
)
from app.features.position_monitoring.service.indicative_entry_read import (
    _assessment_view,
)
from app.features.product.domain.listing_unit_evidence import ListingUnitRoute
from app.features.product.domain.review_evidence import ProductReviewEvidence

durable = legacy.durable
case = scales.case


def delayed_saved(*, provider="GETTEX_DELAYED", age=900):
    saved = saved_example()
    venue = "MUND" if provider == "GETTEX_DELAYED" else "XSTU"
    return replace(
        saved,
        provider=provider,
        route=replace(saved.route, venue_mic=venue),
        quote=replace(
            saved.quote,
            original_evidence=None,
            original_market_status=None,
            observed_at=NOW - timedelta(seconds=age),
            source_mode=("OFFICIAL_DELAYED_PRETRADE" if provider == "GETTEX_DELAYED" else None),
            quote_time_basis=None,
            provider_exchange_code=venue,
            venue_mic=venue if provider == "GETTEX_DELAYED" else None,
            isin=saved.quote.isin if provider == "GETTEX_DELAYED" else None,
            trading_status="UNKNOWN",
        ),
    )


@pytest.mark.parametrize("provider", ["GETTEX_DELAYED", "BOERSE_STUTTGART_DELAYED"])
@pytest.mark.parametrize(
    "age,usable", [(0, True), (900, True), (1800, True), (1801, False), (-1, False)]
)
def test_only_v2_admits_documented_delayed_bid_with_original_shared_clock(provider, age, usable):
    saved = delayed_saved(provider=provider, age=age)
    assert not qualify_review_quote(saved, now=NOW, selection_policy=None).usable
    value = qualify_review_quote(saved, now=NOW, selection_policy=None, policy=V2_POLICY)
    assert value.usable is usable
    assert value.original_bid_at is None
    assert value.source_quote_at == saved.quote.observed_at
    assert value.source_time_basis == "SHARED_QUOTE_TIME"
    if usable:
        assert value.evaluation_mode == "DELAYED_SOURCE_BID"
        assert value.source_freshness == "WITHIN_1800_SECONDS"
        assert value.session_event_at == value.source_quote_at


@pytest.mark.parametrize("change", ["ask_only", "last", "venue", "source", "clock", "retained"])
def test_expansion_never_relabels_another_price_or_an_unapproved_source(change):
    saved = delayed_saved()
    if change == "ask_only":
        saved = replace(saved, quote=replace(saved.quote, bid=None))
    elif change == "last":
        saved = replace(
            saved,
            quote=replace(
                saved.quote,
                bid=None,
                ask=None,
                reference_price=Decimal(1),
                reference_price_type="LAST_TRADE",
            ),
        )
    elif change == "venue":
        saved = replace(saved, route=replace(saved.route, venue_mic="XSTU"))
    elif change == "source":
        saved = replace(saved, provider="UNREGISTERED_DELAYED_SOURCE")
    elif change == "clock":
        saved = replace(saved, quote=replace(saved.quote, observed_at=NOW + timedelta(seconds=1)))
    else:
        saved = replace(saved, quote=replace(saved.quote, retained=True))
    assert not qualify_review_quote(saved, now=NOW, selection_policy=None, policy=V2_POLICY).usable


@pytest.mark.parametrize("age,usable", [(900, True), (901, False)])
def test_v2_does_not_relax_the_original_bid_clock_contract(age, usable):
    saved = saved_example(bid_age=timedelta(seconds=age))
    quote = qualify_review_quote(saved, now=NOW, selection_policy=None, policy=V2_POLICY)
    assert quote.usable is usable
    assert quote.original_bid_at == NOW - timedelta(seconds=age)
    assert quote.source_quote_at is None


def test_later_reading_after_twentieth_close_does_not_qualify_older_shared_quote():
    quote = qualify_review_quote(
        delayed_saved(age=900), now=NOW, selection_policy=None, policy=V2_POLICY
    )
    result = legacy.decision(quote=quote, completed_sessions=19, review_completed_sessions=20)
    assert result.outcome == "NOT_REACHED" and result.review_due is True
    assert result.session_count_at == NOW - timedelta(seconds=900)


def current_unit(evidence=None, **changes):
    evidence = evidence or scales.scale_evidence()
    return replace(
        ProductReviewEvidence(
            workspace_id=evidence.workspace_id,
            warrant_id=evidence.warrant_id,
            known_at=NOW,
            status="AVAILABLE",
            reasons=(),
            revision_id=uuid4(),
            recorded_at=NOW - timedelta(minutes=1),
            fingerprint="d" * 64,
            binding=evidence.binding,
            currency="EUR",
            unit="CURRENCY_PER_WARRANT",
            source_reference="https://example.invalid/synthetic-current-product",
            source_document_sha256="e" * 64,
        ),
        **changes,
    )


def expanded_scale(case, evidence=None, current=None, quote=None):
    original = scales.scale_evidence()
    return _scale(
        case[0],
        evidence or original,
        quote
        or qualify_review_quote(delayed_saved(), now=NOW, selection_policy=None, policy=V2_POLICY),
        isin=original.binding.isin,
        underlying_id=original.binding.underlying_id,
        now=NOW,
        policy=V2_POLICY,
        review_evidence=current or current_unit(),
    )


def test_documented_units_remain_preferred_without_mislabeling_shared_bid_time(case):
    material, problems = expanded_scale(case)
    assert problems == ()
    assert material["quality"] == "DOCUMENTED"
    assert material["history_continuity_assumed"] is False
    assert material["owner_assessment"]["bid_status"] == "MISSING"
    assert material["coverage_basis"] == "SHARED_QUOTE_TIME"


@pytest.mark.parametrize("documented_history", [True, False])
@pytest.mark.parametrize(
    "source_problem",
    [
        "LISTING_UNIT_RULE_NOT_OBSERVED_AT_EVENT",
        "LISTING_UNIT_RULE_NOT_EFFECTIVE_AT_EVENT",
        "LISTING_UNIT_RULE_ORIGINALS_UNQUALIFIED",
    ],
)
def test_unusable_optional_listing_source_does_not_defeat_documented_history(
    case, documented_history, source_problem
):
    current = current_unit(
        status="MISSING",
        unit=None,
        reasons=("PRODUCT_REVIEW_UNIT_UNPROVEN", source_problem),
    )
    original = current_listing_evidence(
        SimpleNamespace(id=current.revision_id, document_sha256=current.source_document_sha256)
    )
    route = ListingUnitRoute(
        delayed_saved().route.warrant_listing_id, "GETTEX_DELAYED", "MUND", "EUR"
    )
    listing = replace(
        original,
        workspace_id=current.workspace_id,
        warrant_id=current.warrant_id,
        route=route,
        known_at=NOW,
        event_at=NOW - timedelta(seconds=900),
        binding=replace(original.binding, product=current.binding, route=route),
        status="UNSUITABLE",
        reasons=(source_problem,),
    )
    current = replace(current, listing_unit_evidence=listing)
    material, problems = expanded_scale(
        case, evidence=scales.scale_evidence(missing=not documented_history), current=current
    )

    assert material["current_unit_evidence"]["listing_unit_evidence"]["status"] == "UNSUITABLE"
    assert source_problem in material["current_unit_evidence"]["reasons"]
    if documented_history:
        assert problems == () and material["quality"] == "DOCUMENTED"
        assert material["comparison_covered"]
    else:
        assert source_problem in problems and material["quality"] == "UNAVAILABLE"
        assert not material["comparison_covered"]


def test_missing_historical_scale_uses_explicit_current_unit_assumption_and_owner_cost(
    case,
):
    basis = case[0]
    before = asdict(basis)
    material, problems = expanded_scale(case, evidence=scales.scale_evidence(missing=True))
    assert problems == ()
    assert material["quality"] == "CURRENT_UNIT_HISTORY_ASSUMED"
    assert material["history_continuity_assumed"] is True
    assert material["owner_assessment"]["status"] == "MISSING"
    assert asdict(basis) == before
    assert basis.valuation_basis.position.average_entry_price == Decimal("2.725")
    assert [item.remaining_quantity for item in basis.buy_contributions] == [
        Decimal(24),
        Decimal(36),
        Decimal(20),
    ]


@pytest.mark.parametrize(
    "change", ["withdrawn", "adjustment", "currency", "terms", "current_conflict"]
)
def test_real_contradictions_block_current_unit_fallback(case, change):
    evidence = scales.scale_evidence()
    current = current_unit()
    if change in {"withdrawn", "adjustment"}:
        status = "WITHDRAWN" if change == "withdrawn" else "ADJUSTMENT_REQUIRED"
        evidence = replace(
            evidence,
            status="UNSUITABLE",
            reasons=(f"PRODUCT_PRICE_SCALE_{status}",),
            manifest=replace(evidence.manifest, status=status),
        )
    elif change == "currency":
        current = replace(current, currency="USD")
    elif change == "terms":
        current = replace(current, binding=replace(current.binding, current_terms_id=uuid4()))
    else:
        current = replace(current, status="UNSUITABLE", reasons=("ORIGINAL_DOCUMENT_CONFLICT",))
    material, problems = expanded_scale(case, evidence=evidence, current=current)
    assert problems and material["comparison_covered"] is False
    assert material["quality"] == "UNAVAILABLE"


def test_later_negative_price_less_status_blocks_delayed_quote_without_a_status_ttl():
    saved = delayed_saved()
    quote = qualify_review_quote(saved, now=NOW, selection_policy=None, policy=V2_POLICY)
    status = SimpleNamespace(
        latest_gap=None,
        latest_capture=None,
        latest_observations=(
            SimpleNamespace(
                original=SimpleNamespace(
                    observed_at=quote.source_quote_at + timedelta(seconds=1),
                    status="SUSPENDED",
                )
            ),
        ),
    )
    assert supply_problems(saved, quote, status) == ("REVIEW_LATER_NEGATIVE_STATUS_OBSERVED",)


def with_facts(
    inputs,
    *,
    mode="SOURCE_BID",
    quality="DOCUMENTED",
    price="1",
    offset=0,
    policy=V2_POLICY,
    provider=None,
    route=None,
):
    saved = inputs.saved
    if mode == "DELAYED_SOURCE_BID":
        saved = delayed_saved()
    elif mode == "INDICATIVE_ISSUER":
        saved = legacy.issuer_saved(provider or "MORGAN_STANLEY")
    if provider:
        saved = replace(saved, provider=provider)
    if route:
        saved = replace(saved, route=replace(saved.route, identity_key=route), identity_key=route)
    at = NOW + timedelta(seconds=offset)
    quote = legacy.quote(
        bid=Decimal(price),
        original_bid_at=at if mode == "SOURCE_BID" else None,
        received_at=at,
        evaluation_mode=mode,
        session_event_at=at,
        ordering_at=at,
        source_quote_at=at if mode == "DELAYED_SOURCE_BID" else None,
        source_time_basis={
            "SOURCE_BID": "ORIGINAL_BID_TIME",
            "DELAYED_SOURCE_BID": "SHARED_QUOTE_TIME",
            "INDICATIVE_ISSUER": "ORIGINAL_TIME_UNKNOWN",
        }[mode],
        source_freshness={
            "SOURCE_BID": "WITHIN_900_SECONDS",
            "DELAYED_SOURCE_BID": "WITHIN_1800_SECONDS",
            "INDICATIVE_ISSUER": "UNKNOWN",
        }[mode],
    )
    count = SimpleNamespace(
        completed_sessions=20, twentieth_closes_at=NOW - timedelta(hours=1), reasons=()
    )
    return replace(
        inputs,
        saved=saved,
        quote=quote,
        policy=policy,
        review_count=count,
        comparison_count=count,
        material={
            **inputs.material,
            "saved_quote": JSON_VALUE.dump_python(asdict(saved), mode="json"),
            "product_scale": {
                "quality": quality,
                "comparison_covered": True,
                "history_continuity_assumed": quality == "CURRENT_UNIT_HISTORY_ASSUMED",
            },
        },
    )


async def step(engine, inputs, *, index=1):
    with Session(engine, expire_on_commit=False) as raw:
        session = SqlSession(raw)
        service = IndicativeEntryService(session, policy=inputs.policy)
        previous = await latest_indicative_assessment(
            session, inputs.workspace_id, inputs.position_id
        )
        if inputs.policy == V2_POLICY or (
            previous is not None and previous.result.get("loss_evidence_floor") is not None
        ):
            floor = await service._recovery_floor(session, inputs, previous)
            inputs = replace(inputs, material={**inputs.material, "loss_evidence_floor": floor})
        decision = service._decision(inputs, None)
        fingerprint = service._input_fingerprint(inputs, decision)
        return await service._persist(
            inputs,
            decision,
            fingerprint,
            previous.id if previous else None,
            previous is not None and previous.input_fingerprint == fingerprint,
            NOW + timedelta(seconds=index),
            True,
        )


@pytest.mark.asyncio
async def test_v1_to_v2_retains_episode_notice_outbox_and_strong_recovery_floor(
    durable,
):
    engine, inputs = durable
    first = await step(engine, with_facts(inputs, policy=V1_POLICY))
    upgraded = await step(engine, with_facts(inputs, mode="DELAYED_SOURCE_BID", offset=1), index=2)
    assert upgraded.alerts_created == upgraded.notifications_created == 0
    repeat = await step(engine, with_facts(inputs, mode="DELAYED_SOURCE_BID", offset=1), index=3)
    assert repeat.unchanged and repeat.alerts_created == repeat.notifications_created == 0
    weak = await step(
        engine,
        with_facts(inputs, mode="DELAYED_SOURCE_BID", offset=3, price="2"),
        index=4,
    )
    assert weak.loss_episode_active and weak.data_problem_active
    assert "REVIEW_RECOVERY_EVIDENCE_WEAKER" in weak.reasons
    recovered = await step(engine, with_facts(inputs, offset=4, price="2"), index=5)
    assert not recovered.loss_episode_active and not recovered.data_problem_active
    again = await step(engine, with_facts(inputs, offset=5), index=6)
    assert again.loss_episode_active and again.alerts_created == 1
    closed = await step(engine, replace(with_facts(inputs, offset=6), closed=True), index=7)
    assert not closed.loss_episode_active and not closed.review_due
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Assessment)) == 6
        losses = session.scalars(
            select(Episode).where(Episode.kind == "ENTRY_LOSS").order_by(Episode.episode_number)
        ).all()
        assert [row.rule_version for row in losses] == [
            V1_POLICY.version,
            V2_POLICY.version,
        ]
        assert losses[0].opening_assessment_id == first.assessment_id
        assert all(row.closed_at is not None for row in losses)
        assert not session.scalars(
            select(NotificationModel).where(NotificationModel.status == "PENDING")
        ).all()


@pytest.mark.asyncio
async def test_quality_floor_joins_price_and_scale_strength_across_entire_episode(
    durable,
):
    engine, inputs = durable
    await step(engine, with_facts(inputs, quality="CURRENT_UNIT_HISTORY_ASSUMED"))
    await step(engine, with_facts(inputs, mode="DELAYED_SOURCE_BID", offset=1), index=2)
    weak = await step(
        engine,
        with_facts(inputs, quality="CURRENT_UNIT_HISTORY_ASSUMED", offset=2, price="2"),
        index=3,
    )
    assert weak.outcome == "UNAVAILABLE" and weak.loss_episode_active
    assert weak.reasons == ("REVIEW_RECOVERY_EVIDENCE_WEAKER",)
    strong = await step(engine, with_facts(inputs, offset=3, price="2"), index=4)
    assert strong.outcome == "AT_OR_ABOVE_ENTRY" and not strong.loss_episode_active


@pytest.mark.asyncio
async def test_returning_to_v1_does_not_discard_an_active_v2_recovery_floor(durable):
    engine, inputs = durable
    await step(engine, with_facts(inputs))
    lower = await step(
        engine,
        with_facts(inputs, mode="INDICATIVE_ISSUER", price="2", offset=1, policy=V1_POLICY),
        index=2,
    )
    assert lower.loss_episode_active and "REVIEW_RECOVERY_EVIDENCE_WEAKER" in lower.reasons
    recovered = await step(
        engine, with_facts(inputs, price="2", offset=2, policy=V1_POLICY), index=3
    )
    assert recovered.outcome == "AT_OR_ABOVE_ENTRY" and not recovered.loss_episode_active


def test_read_clock_digest_is_not_a_new_scale_fact_but_revision_change_is(durable):
    _, base = durable
    inputs = with_facts(base)
    scale = {
        **inputs.material["product_scale"],
        "owner_assessment": {
            "evidence": {
                "revision_id": "same-revision",
                "fingerprint": "a" * 64,
                "known_at": NOW.isoformat(),
            }
        },
    }
    first = replace(inputs, material={**inputs.material, "product_scale": scale})
    value = IndicativeEntryService._decision(first, None)
    identity = IndicativeEntryService._input_fingerprint(first, value)
    evidence = scale["owner_assessment"]["evidence"]
    later_scale = {
        **scale,
        "owner_assessment": {
            "evidence": {
                **evidence,
                "fingerprint": "b" * 64,
                "known_at": (NOW + timedelta(seconds=10)).isoformat(),
            }
        },
    }
    later = replace(inputs, material={**inputs.material, "product_scale": later_scale})
    assert IndicativeEntryService._input_fingerprint(later, value) == identity
    later_scale["owner_assessment"]["evidence"]["revision_id"] = "changed-revision"
    assert IndicativeEntryService._input_fingerprint(later, value) != identity


@pytest.mark.asyncio
async def test_unknown_clock_source_switch_and_older_known_clock_cannot_clear_loss(
    durable,
):
    engine, inputs = durable
    await step(engine, with_facts(inputs, mode="INDICATIVE_ISSUER"))
    switched = await step(
        engine,
        with_facts(inputs, mode="INDICATIVE_ISSUER", provider="JPMORGAN", offset=1, price="2"),
        index=2,
    )
    assert switched.loss_episode_active
    assert "REVIEW_RECOVERY_SOURCE_NOT_COMPARABLE" in switched.reasons
    old = await step(engine, with_facts(inputs, offset=-1, price="2"), index=3)
    assert old.loss_episode_active and "REVIEW_OUT_OF_ORDER_OBSERVATION" in old.reasons
    current = await step(engine, with_facts(inputs, offset=2, price="2"), index=4)
    assert not current.loss_episode_active


@pytest.mark.asyncio
async def test_family_root_unique_prevents_parallel_independent_version_histories(
    durable,
):
    engine, inputs = durable
    await step(engine, with_facts(inputs, policy=V1_POLICY))
    with Session(engine) as session:
        existing = session.scalar(select(Assessment))
        values = {
            column.name: getattr(existing, column.name) for column in Assessment.__table__.columns
        }
        session.add(Assessment(**(values | {"id": uuid4(), "rule_version": V2_POLICY.version})))
        with pytest.raises(IntegrityError, match="UNIQUE constraint failed"):
            session.commit()


@pytest.mark.asyncio
async def test_passive_view_reports_actual_assessment_version_and_shared_clock(durable):
    engine, inputs = durable
    await step(
        engine,
        with_facts(inputs, mode="DELAYED_SOURCE_BID", quality="CURRENT_UNIT_HISTORY_ASSUMED"),
    )
    with Session(engine) as session:
        view = _assessment_view(session.scalar(select(Assessment)))
    assert view.rule_version == V2_POLICY.version
    assert view.original_bid_at is None and datetime.fromisoformat(view.source_quote_at) == NOW
    assert view.source_time_basis == "SHARED_QUOTE_TIME"
    assert view.source_freshness == "WITHIN_1800_SECONDS"
    assert view.history_continuity_assumed is True
    assert view.source["venue_mic"] == "MUND"
