"""B04/B57 from qualified inputs to actual durable SQL history, synthetic only."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from tests.unit.backend.features.position_monitoring.test_hebeltrader_original_bid import (
    NOW,
    saved_example,
)

from app.features.alert.persistence.models import AlertModel
from app.features.market_data.domain.original_market_status_evidence import (
    OriginalMarketStatusEvidence,
)
from app.features.market_data.domain.status_observations import (
    MarketStatusObservation,
    StatusRouteBinding,
    resolve_status_observations,
)
from app.features.notification.persistence.models import (
    NotificationDeliveryAttemptModel,
    NotificationModel,
)
from app.features.position_monitoring.domain.hebeltrader_loss import decide_loss
from app.features.position_monitoring.persistence.hebeltrader_loss import (
    HebeltraderLossAssessmentModel as Assessment,
)
from app.features.position_monitoring.persistence.hebeltrader_loss import (
    HebeltraderLossEpisodeModel as Episode,
)
from app.features.position_monitoring.service.hebeltrader_b58_sources import (
    B58SourcePath,
    B58SourceRegistry,
)
from app.features.position_monitoring.service.hebeltrader_loss import HebeltraderLossService
from app.features.position_monitoring.service.hebeltrader_loss_inputs import LossInputs


def decision(**changes):
    return decide_loss(
        **{
            "closed": False,
            "bid": Decimal("1"),
            "gross_entry": Decimal("2"),
            "bid_at": NOW,
            "remaining_quantity": 80,
            "completed_sessions_at_bid": 20,
            "input_problems": (),
        }
        | changes
    )


@pytest.mark.parametrize("sessions,outcome", [(19, "NOT_REACHED"), (20, "LOSS"), (21, "LOSS")])
def test_only_twenty_completed_sessions_enable_loss(sessions, outcome):
    assert decision(completed_sessions_at_bid=sessions).outcome == outcome


@pytest.mark.parametrize(
    "price,outcome", [("1.9999999999", "LOSS"), ("2", "RECOVERED"), ("2.01", "RECOVERED")]
)
def test_personal_gross_entry_without_fee_or_target_condition(price, outcome):
    assert decision(bid=Decimal(price)).outcome == outcome


@pytest.mark.parametrize(
    "problem",
    [
        "ORIGINAL_BID_TOO_OLD",
        "ORIGINAL_BID_SIDE_TIME_MISSING",
        "ORIGINAL_BID_AFTER_READ",
        "EXECUTION_BID_CURRENCY_MISMATCH",
        "PRODUCT_PRICE_SCALE_EVIDENCE_MISSING",
        "PRODUCT_PRICE_SCALE_ADJUSTMENT_REQUIRED",
        "B58_OPEN_AT_EVALUATION_NOT_PROVEN",
    ],
)
def test_unqualified_input_is_never_recovery(problem):
    result = decision(bid=Decimal("5"), input_problems=(problem,))
    assert result.outcome == "NOT_ASSESSABLE"
    assert result.reasons == (problem,)


def status_case(*, at=NOW, status="OPEN"):
    saved = saved_example()
    route = saved.route
    binding = StatusRouteBinding(
        route.workspace_id,
        route.warrant_id,
        route.warrant_listing_id,
        saved.provider,
        route.identity_key,
        saved.quote.isin,
        route.venue_mic,
    )
    original = OriginalMarketStatusEvidence(
        "original-market-status-evidence-v1",
        "frankfurt-quotes-v1",
        "synthetic-test-source",
        at,
        saved.quote.isin,
        "XFRA",
        status,
        status,
        "trading_status",
        at,
        at.isoformat(),
        "status_observed_at",
    )
    point = MarketStatusObservation(uuid4(), "a" * 64, binding, at, at, original, None)
    evidence = resolve_status_observations((point,), route=binding, event_at=NOW, known_at=NOW)
    path = B58SourcePath(
        saved.provider,
        saved.quote.isin,
        "XFRA",
        "frankfurt-quotes-v1",
        "synthetic-test-source",
        "https://example.invalid/explicit-synthetic-source-contract",
        "b" * 64,
        "bid_at",
        "trading_status",
        "status_observed_at",
    )
    return saved, point, evidence, path


def test_real_registry_is_empty_and_payload_shape_cannot_qualify_supplier():
    saved, _, evidence, _ = status_case()
    assert B58SourceRegistry().qualification_references == ()
    result = B58SourceRegistry().qualify(saved, evidence)
    assert result.status == "NOT_QUALIFIED"
    assert result.reasons == ("B58_REAL_SOURCE_PATH_NOT_QUALIFIED",)


@pytest.mark.parametrize("age", [1, 899, 900, 901, 86400])
def test_status_has_no_900_second_validity_rule(age):
    saved, _, evidence, path = status_case(at=NOW - timedelta(seconds=age))
    assert B58SourceRegistry((path,)).qualify(saved, evidence).status == "NOT_QUALIFIED"


@pytest.mark.parametrize("status", ["CLOSED", "SUSPENDED", "UNKNOWN"])
def test_negative_status_never_qualifies_open(status):
    saved, _, evidence, path = status_case(status=status)
    assert B58SourceRegistry((path,)).qualify(saved, evidence).status == "NOT_QUALIFIED"


def test_only_synthetic_registered_point_is_qualified_without_continuity_condition():
    saved, _, evidence, path = status_case()
    result = B58SourceRegistry((path,)).qualify(saved, evidence)
    assert result.status == "QUALIFIED"
    assert result.qualification_reference.startswith("https://example.invalid/")
    assert saved.quote.original_evidence.bid.observed_at < evidence.event_at
    assert evidence.status_validity_interval == "NOT_ESTABLISHED"
    assert evidence.source_qualification == "NOT_INDEPENDENTLY_VERIFIED"


def test_conflict_gap_and_route_change_fail_closed():
    saved, point, _, path = status_case()
    opposite = replace(
        point,
        id=uuid4(),
        fingerprint="c" * 64,
        original=replace(point.original, status="CLOSED", original_status_text="CLOSED"),
    )
    gap = replace(point, id=uuid4(), fingerprint="d" * 64, original=None, reason="TRANSPORT_ERROR")
    policy = B58SourceRegistry((path,))
    for observations in ((point, opposite), (point, gap)):
        evidence = resolve_status_observations(
            observations, route=point.route, event_at=NOW, known_at=NOW
        )
        assert policy.qualify(saved, evidence).status == "NOT_QUALIFIED"
    evidence = resolve_status_observations(
        (point,), route=replace(point.route, identity_key="e" * 64), event_at=NOW, known_at=NOW
    )
    assert policy.qualify(saved, evidence).status == "NOT_QUALIFIED"


class SqlSession:
    """Real SQLite statements in one pytest tmp_path; no outbound adapter exists."""

    def __init__(self, session):
        self.session = session

    async def scalar(self, statement):
        return self.session.scalar(statement)

    async def scalars(self, statement):
        return self.session.scalars(statement)

    async def execute(self, statement):
        return self.session.execute(statement)

    def add(self, model):
        self.session.add(model)

    async def flush(self):
        self.session.flush()

    async def commit(self):
        self.session.commit()


@pytest.fixture
def durable(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/synthetic_b04_only.db")
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
        "economic_basis": {"cost_basis_currency": "EUR"},
        "warrant_name": "Synthetic warrant",
        "warrant_isin": saved.quote.isin,
        "warrant_wkn": "TEST01",
        "source_qualification": {"qualification_reference": "synthetic-only"},
    }
    inputs = LossInputs(
        saved.route.workspace_id,
        uuid4(),
        saved.route.position_id,
        saved.route.warrant_id,
        "1" * 64,
        False,
        saved,
        material,
        (),
    )
    yield engine, inputs
    engine.dispose()


async def persist(engine, inputs, value, index, previous=None, duplicate=False):
    with Session(engine, expire_on_commit=False) as raw:
        return await HebeltraderLossService(SqlSession(raw))._persist(
            inputs,
            value,
            str(index).zfill(64),
            previous,
            duplicate,
            NOW + timedelta(seconds=index),
            True,
        )


@pytest.mark.asyncio
async def test_loss_gap_recovery_reentry_restart_and_full_sale_keep_exact_history(durable):
    engine, inputs = durable
    first = await persist(engine, inputs, decision(), 1)
    replay = await persist(engine, inputs, decision(), 1, first.assessment_id, True)
    assert first.alert_created and first.notification_created
    assert replay.unchanged and not replay.alert_created and not replay.notification_created
    assert replay.episode_id == first.episode_id
    gap = await persist(
        engine, inputs, decision(input_problems=("DATA_GAP",)), 2, first.assessment_id
    )
    assert gap.episode_active and gap.episode_id == first.episode_id
    recovered = await persist(engine, inputs, decision(bid=Decimal("2")), 3, gap.assessment_id)
    assert not recovered.episode_active
    second = await persist(engine, inputs, decision(), 4, recovered.assessment_id)
    assert second.episode_id != first.episode_id and second.alert_created
    closed = await persist(
        engine,
        inputs,
        decision(closed=True, remaining_quantity=0, input_problems=("NO_SOURCE",)),
        5,
        second.assessment_id,
    )
    assert not closed.episode_active and closed.outcome == "CLOSED"
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Assessment)) == 5
        assert session.scalar(select(func.count()).select_from(Episode)) == 2
        assert session.scalar(select(func.count()).select_from(AlertModel)) == 2
        notifications = session.scalars(select(NotificationModel)).all()
        assert len(notifications) == 2 and {n.status for n in notifications} == {"FAILED"}
        attempts = session.scalars(select(NotificationDeliveryAttemptModel)).all()
        assert {a.error_code for a in attempts} == {"B04_ALERT_RESOLVED", "B04_POSITION_CLOSED"}
        assert all(not a.retryable for a in attempts)
        assert all(a.status == "RESOLVED" for a in session.scalars(select(AlertModel)).all())


@pytest.mark.asyncio
async def test_correction_new_assessment_preserves_active_episode_and_notification(durable):
    engine, inputs = durable
    first = await persist(engine, inputs, decision(), 1)
    corrected = await persist(
        engine,
        replace(inputs, owner_basis_id="9" * 64),
        decision(gross_entry=Decimal("3"), remaining_quantity=60),
        2,
        first.assessment_id,
    )
    assert corrected.episode_active and corrected.episode_id == first.episode_id
    assert not corrected.alert_created and not corrected.notification_created
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(Assessment)) == 2
        assert session.scalar(select(func.count()).select_from(AlertModel)) == 1
        assert (
            session.scalar(
                select(Assessment.owner_basis_id).where(Assessment.id == corrected.assessment_id)
            )
            == "9" * 64
        )


def test_ordering_rejects_older_and_conflicting_quotes_but_evaluates_owner_corrections():
    saved = saved_example()
    inputs = LossInputs(
        uuid4(),
        uuid4(),
        uuid4(),
        uuid4(),
        "b" * 64,
        False,
        saved,
        {
            "bid": {"price": "1", "original_bid_at": NOW.isoformat()},
            "underlying_sessions": {"count": {"completed_sessions": 20}},
            "economic_basis": {"position": {"average_entry_price": "2", "open_quantity": 10}},
        },
        (),
    )
    last = SimpleNamespace(bid_at=NOW + timedelta(seconds=1), inputs={"bid": {"price": "1"}})
    assert "B04_OUT_OF_ORDER_BID" in HebeltraderLossService._decision(inputs, (), last).reasons
    last.bid_at = NOW
    last.inputs["bid"]["price"] = "2"
    assert (
        "B04_CONFLICTING_BID_AT_SAME_TIME"
        in HebeltraderLossService._decision(inputs, (), last).reasons
    )
    last.inputs["bid"]["price"] = "1"
    assert HebeltraderLossService._decision(inputs, (), last).outcome == "LOSS"
