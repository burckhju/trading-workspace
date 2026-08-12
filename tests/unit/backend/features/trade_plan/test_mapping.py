from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.features.trade_plan.domain.enums import (
    EntryType,
    TradeDirection,
    TradePlanOriginType,
    TradePlanStatus,
)
from app.features.trade_plan.domain.models import (
    EntryPlan,
    InvalidationPlan,
    RiskAssumptions,
    Target,
    TradePlan,
    TradePlanVersion,
)
from app.features.trade_plan.persistence.mapping import (
    trade_plan_from_model,
    trade_plan_to_model,
    trade_plan_version_from_models,
    trade_plan_version_to_models,
)


def test_trade_plan_mapping_round_trip_preserves_candidate_provenance() -> None:
    plan = TradePlan(
        id=uuid4(),
        workspace_id=uuid4(),
        underlying_id=uuid4(),
        origin_type=TradePlanOriginType.CANDIDATE_EVALUATION,
        candidate_id=uuid4(),
        candidate_evaluation_id=uuid4(),
        created_at=datetime.now(UTC),
        created_by=uuid4(),
    )
    assert trade_plan_from_model(trade_plan_to_model(plan)) == plan


def test_trade_plan_version_mapping_round_trip_preserves_snapshot() -> None:
    version = TradePlanVersion(
        id=uuid4(),
        trade_plan_id=uuid4(),
        version=2,
        direction=TradeDirection.LONG,
        thesis="Breakout continuation",
        entry=EntryPlan(
            type=EntryType.PRICE_RANGE,
            currency="EUR",
            price_from=Decimal("100"),
            price_to=Decimal("102"),
            valid_until=datetime.now(UTC),
            rationale="Retest zone",
        ),
        invalidation=InvalidationPlan(
            stop_price=Decimal("95"), invalidation_rule="Close below support"
        ),
        targets=(
            Target(sequence=1, price=Decimal("110"), rationale="First objective"),
            Target(sequence=2, price=Decimal("120")),
        ),
        risk_assumptions=RiskAssumptions(
            thesis_risk="Breakout fails", max_loss_assumption="Stop defines plan risk"
        ),
        status=TradePlanStatus.DRAFT,
        created_at=datetime.now(UTC),
        created_by=uuid4(),
        previous_version_id=uuid4(),
        change_reason="Entry refined",
    )
    model, target_models = trade_plan_version_to_models(version)
    restored = trade_plan_version_from_models(model, target_models)
    assert restored == version
