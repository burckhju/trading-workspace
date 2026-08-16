from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from app.features.product_selection.persistence.models import (
    ProductEvaluationModel,
    ProductSelectionModel,
    ProductSelectionRunModel,
)


def _names(model, kind):
    return {c.name for c in model.__table__.constraints if isinstance(c, kind)}


def test_ft008_persistence_tables_keep_run_evaluation_selection_separate():
    assert ProductSelectionRunModel.__tablename__ == "product_selection_runs"
    assert ProductEvaluationModel.__tablename__ == "product_evaluations"
    assert ProductSelectionModel.__tablename__ == "product_selections"


def test_run_requires_approved_trade_plan_version_at_database_boundary():
    assert "ck_product_selection_runs_approved_trade_plan_version" in _names(
        ProductSelectionRunModel, CheckConstraint
    )


def test_selection_is_unique_per_run_and_bound_to_evaluation_from_same_run():
    assert "uq_product_selections_run" in _names(ProductSelectionModel, UniqueConstraint)
    assert "fk_product_selections_evaluation_same_run" in _names(
        ProductSelectionModel, ForeignKeyConstraint
    )
    assert "uq_product_evaluations_id_run" in _names(ProductEvaluationModel, UniqueConstraint)
