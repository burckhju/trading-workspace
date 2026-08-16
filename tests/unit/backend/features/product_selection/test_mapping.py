from datetime import UTC, datetime
from uuid import uuid4

from app.features.product_selection.domain.enums import (
    CriterionOutcome,
    DataAvailability,
    EligibilityStatus,
    MetricOrigin,
)
from app.features.product_selection.domain.models import (
    CriterionResult,
    EvaluationInput,
    EvaluationMetric,
    ModelReference,
    ProductEvaluation,
    ProductSelection,
    ProductSelectionRun,
)
from app.features.product_selection.persistence.mapping import (
    evaluation_from_models,
    evaluation_to_models,
    run_from_model,
    run_to_model,
    selection_from_model,
    selection_to_model,
)
from app.features.trade_plan.domain.enums import TradePlanStatus

NOW = datetime(2026, 8, 16, 8, 0, tzinfo=UTC)
MODEL = ModelReference("ft008", "1")


def test_run_mapping_round_trip_preserves_model_versions_and_exact_trade_plan_version():
    run = ProductSelectionRun(
        id=uuid4(),
        workspace_id=uuid4(),
        trade_plan_id=uuid4(),
        trade_plan_version_id=uuid4(),
        trade_plan_version_status=TradePlanStatus.APPROVED,
        underlying_id=uuid4(),
        evaluated_at=NOW,
        universe_model=MODEL,
        eligibility_model=MODEL,
        evaluation_model=MODEL,
        created_at=NOW,
        created_by=uuid4(),
    )
    assert run_from_model(run_to_model(run)) == run


def test_evaluation_mapping_round_trip_preserves_ordered_explainability_snapshot():
    ev = ProductEvaluation(
        id=uuid4(),
        run_id=uuid4(),
        warrant_id=uuid4(),
        warrant_terms_version_id=uuid4(),
        warrant_listing_id=uuid4(),
        evaluated_at=NOW,
        eligibility_model=MODEL,
        evaluation_model=MODEL,
        inputs=(EvaluationInput("quote", None, DataAvailability.MISSING, "TC-001"),),
        criteria=(
            CriterionResult(
                "quote-present",
                CriterionOutcome.NOT_EVALUABLE,
                "Quote missing",
                data_availability=DataAvailability.MISSING,
            ),
        ),
        metrics=(
            EvaluationMetric(
                "spread",
                None,
                "%",
                MetricOrigin.CALCULATED,
                "FT008",
                data_availability=DataAvailability.MISSING,
            ),
        ),
        eligibility_status=EligibilityStatus.NOT_EVALUABLE,
        reasons=("Quote missing",),
    )
    root, inputs, criteria, metrics, reasons = evaluation_to_models(ev)
    assert evaluation_from_models(root, inputs, criteria, metrics, reasons) == ev


def test_selection_mapping_round_trip_preserves_explicit_user_decision():
    selection = ProductSelection(
        id=uuid4(),
        run_id=uuid4(),
        product_evaluation_id=uuid4(),
        selected_at=NOW,
        selected_by=uuid4(),
        rationale="User chose listing",
    )
    assert selection_from_model(selection_to_model(selection)) == selection
