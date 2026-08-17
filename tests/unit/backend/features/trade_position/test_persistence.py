from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from app.features.trade_position.persistence.models import (
    ExecutionRecordModel,
    PositionModel,
    TradeModel,
)


def _names(model, kind):
    return {
        constraint.name
        for constraint in model.__table__.constraints
        if isinstance(constraint, kind)
    }


def test_ft009_uses_separate_trade_execution_and_position_tables() -> None:
    assert TradeModel.__tablename__ == "trades"
    assert ExecutionRecordModel.__tablename__ == "execution_records"
    assert PositionModel.__tablename__ == "positions"


def test_trade_origin_provenance_is_protected_at_database_boundary() -> None:
    assert "ck_trades_origin_provenance" in _names(
        TradeModel,
        CheckConstraint,
    )


def test_execution_values_are_positive_at_database_boundary() -> None:
    names = _names(ExecutionRecordModel, CheckConstraint)

    assert "ck_execution_records_side_valid" in names
    assert "ck_execution_records_quantity_positive" in names
    assert "ck_execution_records_price_positive" in names
    assert "ck_execution_records_recorded_not_before_executed" in names


def test_position_aggregates_are_positive_at_database_boundary() -> None:
    names = _names(PositionModel, CheckConstraint)

    assert "ck_positions_open_quantity_positive" in names
    assert "ck_positions_cost_basis_positive" in names
    assert "ck_positions_average_entry_price_positive" in names
    assert "ck_positions_last_execution_not_before_opened" in names


def test_position_is_unique_per_trade() -> None:
    assert "uq_positions_trade" in _names(
        PositionModel,
        UniqueConstraint,
    )


def test_execution_records_do_not_forbid_identical_real_purchases() -> None:
    unique_constraints = [
        tuple(column.name for column in constraint.columns)
        for constraint in ExecutionRecordModel.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    ]

    assert ("trade_id", "quantity", "price_per_unit") not in unique_constraints


def test_historical_trade_references_use_foreign_keys() -> None:
    names = _names(TradeModel, ForeignKeyConstraint)

    assert "fk_trades_trade_plan" in names
    assert "fk_trades_trade_plan_version" in names
    assert "fk_trades_product_selection" in names
    assert "fk_trades_product_evaluation" in names
