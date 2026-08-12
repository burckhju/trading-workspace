"""Mapping between immutable FT-007 domain snapshots and SQLAlchemy rows."""

from __future__ import annotations

from uuid import UUID, uuid4

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
from app.features.trade_plan.persistence.models import (
    TradePlanModel,
    TradePlanTargetModel,
    TradePlanVersionModel,
)


def trade_plan_to_model(plan: TradePlan) -> TradePlanModel:
    return TradePlanModel(
        id=plan.id,
        workspace_id=plan.workspace_id,
        underlying_id=plan.underlying_id,
        origin_type=plan.origin_type.value,
        candidate_id=plan.candidate_id,
        candidate_evaluation_id=plan.candidate_evaluation_id,
        created_at=plan.created_at,
        created_by=str(plan.created_by),
    )


def trade_plan_from_model(model: TradePlanModel) -> TradePlan:
    return TradePlan(
        id=model.id,
        workspace_id=model.workspace_id,
        underlying_id=model.underlying_id,
        origin_type=TradePlanOriginType(model.origin_type),
        candidate_id=model.candidate_id,
        candidate_evaluation_id=model.candidate_evaluation_id,
        created_at=model.created_at,
        created_by=UUID(model.created_by),
    )


def trade_plan_version_to_models(
    version: TradePlanVersion,
) -> tuple[TradePlanVersionModel, tuple[TradePlanTargetModel, ...]]:
    entry = version.entry
    invalidation = version.invalidation
    risk = version.risk_assumptions
    version_model = TradePlanVersionModel(
        id=version.id,
        trade_plan_id=version.trade_plan_id,
        version=version.version,
        direction=version.direction.value,
        thesis=version.thesis,
        entry_type=entry.type.value,
        entry_currency=entry.currency,
        entry_price=entry.price,
        entry_price_from=entry.price_from,
        entry_price_to=entry.price_to,
        entry_trigger=entry.trigger,
        entry_reference_price=entry.reference_price,
        entry_valid_until=entry.valid_until,
        entry_rationale=entry.rationale,
        stop_price=invalidation.stop_price,
        invalidation_rule=invalidation.invalidation_rule,
        invalidation_rationale=invalidation.rationale,
        risk_thesis=risk.thesis_risk,
        risk_max_loss_assumption=risk.max_loss_assumption,
        risk_notes=risk.notes,
        status=version.status.value,
        created_at=version.created_at,
        created_by=str(version.created_by),
        previous_version_id=version.previous_version_id,
        change_reason=version.change_reason,
    )
    targets = tuple(
        TradePlanTargetModel(
            id=uuid4(),
            trade_plan_version_id=version.id,
            sequence=target.sequence,
            price=target.price,
            rationale=target.rationale,
        )
        for target in version.targets
    )
    return version_model, targets


def trade_plan_version_from_models(
    model: TradePlanVersionModel,
    target_models: tuple[TradePlanTargetModel, ...],
) -> TradePlanVersion:
    targets = tuple(
        Target(sequence=target.sequence, price=target.price, rationale=target.rationale)
        for target in sorted(target_models, key=lambda item: item.sequence)
    )
    return TradePlanVersion(
        id=model.id,
        trade_plan_id=model.trade_plan_id,
        version=model.version,
        direction=TradeDirection(model.direction),
        thesis=model.thesis,
        entry=EntryPlan(
            type=EntryType(model.entry_type),
            currency=model.entry_currency,
            price=model.entry_price,
            price_from=model.entry_price_from,
            price_to=model.entry_price_to,
            trigger=model.entry_trigger,
            reference_price=model.entry_reference_price,
            valid_until=model.entry_valid_until,
            rationale=model.entry_rationale,
        ),
        invalidation=InvalidationPlan(
            stop_price=model.stop_price,
            invalidation_rule=model.invalidation_rule,
            rationale=model.invalidation_rationale,
        ),
        targets=targets,
        risk_assumptions=RiskAssumptions(
            thesis_risk=model.risk_thesis,
            max_loss_assumption=model.risk_max_loss_assumption,
            notes=model.risk_notes,
        ),
        status=TradePlanStatus(model.status),
        created_at=model.created_at,
        created_by=UUID(model.created_by),
        previous_version_id=model.previous_version_id,
        change_reason=model.change_reason,
    )
