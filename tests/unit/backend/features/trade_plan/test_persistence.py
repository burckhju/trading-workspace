from sqlalchemy import CheckConstraint, UniqueConstraint

from app.features.trade_plan.persistence.models import (
    TradePlanApprovalModel,
    TradePlanEventModel,
    TradePlanModel,
    TradePlanTargetModel,
    TradePlanVersionModel,
)


def _constraint_names(model, kind):
    return {c.name for c in model.__table__.constraints if isinstance(c, kind)}


def test_trade_plan_persistence_tables_and_origin_constraint() -> None:
    assert TradePlanModel.__tablename__ == "trade_plans"
    assert TradePlanVersionModel.__tablename__ == "trade_plan_versions"
    assert TradePlanTargetModel.__tablename__ == "trade_plan_targets"
    assert TradePlanEventModel.__tablename__ == "trade_plan_events"
    assert TradePlanApprovalModel.__tablename__ == "trade_plan_approvals"
    assert "ck_trade_plans_trade_plan_origin_provenance" in _constraint_names(
        TradePlanModel, CheckConstraint
    )


def test_version_and_approval_uniqueness_are_versionspecific() -> None:
    assert "uq_trade_plan_versions_plan_version" in _constraint_names(
        TradePlanVersionModel, UniqueConstraint
    )
    assert "uq_trade_plan_targets_version_sequence" in _constraint_names(
        TradePlanTargetModel, UniqueConstraint
    )
    assert "uq_trade_plan_approvals_version" in _constraint_names(
        TradePlanApprovalModel, UniqueConstraint
    )


def test_persistence_remains_product_neutral() -> None:
    all_columns = {
        column.name
        for model in (TradePlanModel, TradePlanVersionModel, TradePlanTargetModel)
        for column in model.__table__.columns
    }
    forbidden = {
        "warrant_id",
        "issuer_id",
        "leverage",
        "spread",
        "ratio",
        "expiry",
        "quantity",
    }
    assert not all_columns.intersection(forbidden)
