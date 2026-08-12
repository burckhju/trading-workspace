from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.features.trade_plan.domain.enums import (
    EntryType,
    TradeDirection,
    TradePlanOriginType,
    TradePlanStatus,
)
from app.features.trade_plan.domain.lifecycle import ensure_transition
from app.features.trade_plan.domain.models import (
    EntryPlan,
    InvalidationPlan,
    RiskAssumptions,
    Target,
    TradePlan,
    TradePlanVersion,
)

NOW = datetime.now(UTC)


def test_origin_invariants():
    with pytest.raises(ValueError):
        TradePlan(
            uuid4(),
            uuid4(),
            uuid4(),
            TradePlanOriginType.MANUAL,
            NOW,
            uuid4(),
            candidate_id=uuid4(),
        )
    TradePlan(
        uuid4(),
        uuid4(),
        uuid4(),
        TradePlanOriginType.CANDIDATE_EVALUATION,
        NOW,
        uuid4(),
        uuid4(),
        uuid4(),
    )


def test_entry_variants_validate():
    EntryPlan(EntryType.PRICE, "EUR", price=Decimal("100"))
    EntryPlan(EntryType.PRICE_RANGE, "EUR", price_from=Decimal("99"), price_to=Decimal("101"))
    EntryPlan(
        EntryType.TRIGGER,
        "EUR",
        trigger="breakout above resistance",
        reference_price=Decimal("100"),
    )
    with pytest.raises(ValueError):
        EntryPlan(
            EntryType.PRICE_RANGE,
            "EUR",
            price_from=Decimal("101"),
            price_to=Decimal("99"),
        )


def _version(status=TradePlanStatus.DRAFT, **kw):
    data = dict(
        id=uuid4(),
        trade_plan_id=uuid4(),
        version=1,
        direction=TradeDirection.LONG,
        thesis="Trend continuation",
        entry=EntryPlan(EntryType.PRICE, "EUR", price=Decimal("100")),
        invalidation=InvalidationPlan(stop_price=Decimal("95")),
        targets=(Target(1, Decimal("110")), Target(2, Decimal("120"))),
        risk_assumptions=RiskAssumptions("Setup invalid below support"),
        status=status,
        created_at=NOW,
        created_by=uuid4(),
    )
    data.update(kw)
    return TradePlanVersion(**data)


def test_long_price_geometry_and_target_order():
    _version()
    with pytest.raises(ValueError):
        _version(invalidation=InvalidationPlan(stop_price=Decimal("101")))
    with pytest.raises(ValueError):
        _version(targets=(Target(1, Decimal("99")),))
    with pytest.raises(ValueError):
        _version(targets=(Target(2, Decimal("110")),))


def test_lifecycle_and_approval_guards():
    ensure_transition(TradePlanStatus.DRAFT, TradePlanStatus.READY_FOR_REVIEW)
    ensure_transition(TradePlanStatus.READY_FOR_REVIEW, TradePlanStatus.APPROVED)
    with pytest.raises(ValueError):
        ensure_transition(TradePlanStatus.DRAFT, TradePlanStatus.APPROVED)
    _version().ensure_ready_for_review()
    _version(TradePlanStatus.READY_FOR_REVIEW).ensure_approvable()
    with pytest.raises(ValueError):
        _version().ensure_approvable()


def test_rule_only_invalidation_needs_rationale():
    with pytest.raises(ValueError):
        InvalidationPlan(invalidation_rule="trend breaks")
    InvalidationPlan(invalidation_rule="trend breaks", rationale="invalidates thesis")


def test_version_lineage_requires_explicit_previous_snapshot_and_reason():
    plan_id = uuid4()
    previous_id = uuid4()
    _version(
        trade_plan_id=plan_id,
        version=2,
        previous_version_id=previous_id,
        change_reason="adjust entry after approved plan",
    )

    with pytest.raises(ValueError, match="requires a previous version"):
        _version(trade_plan_id=plan_id, version=2)
    with pytest.raises(ValueError, match="requires a change reason"):
        _version(
            trade_plan_id=plan_id,
            version=2,
            previous_version_id=previous_id,
            change_reason="  ",
        )


def test_initial_version_and_lineage_cannot_point_back_illegally():
    with pytest.raises(ValueError, match="initial trade plan version"):
        _version(version=1, previous_version_id=uuid4(), change_reason="not allowed")

    version_id = uuid4()
    with pytest.raises(ValueError, match="cannot reference itself"):
        _version(
            id=version_id,
            version=2,
            previous_version_id=version_id,
            change_reason="cycle",
        )
