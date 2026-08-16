from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

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
from app.features.trade_plan.domain.enums import TradePlanStatus

NOW = datetime.now(UTC)
MODEL = ModelReference("FT008_ELIGIBILITY", "1.0.0")
EVAL_MODEL = ModelReference("FT008_EVALUATION", "1.0.0")
UNIVERSE_MODEL = ModelReference("FT008_UNIVERSE", "1.0.0")


def _run(status: TradePlanStatus = TradePlanStatus.APPROVED) -> ProductSelectionRun:
    return ProductSelectionRun(
        id=uuid4(),
        workspace_id=uuid4(),
        trade_plan_id=uuid4(),
        trade_plan_version_id=uuid4(),
        trade_plan_version_status=status,
        underlying_id=uuid4(),
        evaluated_at=NOW,
        universe_model=UNIVERSE_MODEL,
        eligibility_model=MODEL,
        evaluation_model=EVAL_MODEL,
        created_at=NOW,
        created_by=uuid4(),
    )


def _evaluation(
    run: ProductSelectionRun,
    status: EligibilityStatus = EligibilityStatus.ELIGIBLE,
) -> ProductEvaluation:
    if status is EligibilityStatus.ELIGIBLE:
        criterion = CriterionResult(
            "terms-valid",
            CriterionOutcome.FULFILLED,
            "Terms are valid at evaluation time",
        )
        reasons: tuple[str, ...] = ()
    elif status is EligibilityStatus.INELIGIBLE:
        criterion = CriterionResult(
            "maturity-valid",
            CriterionOutcome.NOT_FULFILLED,
            "Product is already matured",
            actual_value="2026-08-15",
            expected_value="> 2026-08-16",
        )
        reasons = ("Product is already matured",)
    else:
        criterion = CriterionResult(
            "quote-available",
            CriterionOutcome.NOT_EVALUABLE,
            "Bid/ask quote is missing",
            data_availability=DataAvailability.MISSING,
        )
        reasons = ("Bid/ask quote is missing",)
    return ProductEvaluation(
        id=uuid4(),
        run_id=run.id,
        warrant_id=uuid4(),
        warrant_terms_version_id=uuid4(),
        warrant_listing_id=uuid4(),
        evaluated_at=NOW,
        eligibility_model=MODEL,
        evaluation_model=EVAL_MODEL,
        inputs=(),
        criteria=(criterion,),
        metrics=(),
        eligibility_status=status,
        reasons=reasons,
    )


def test_run_requires_approved_trade_plan_version():
    _run()
    with pytest.raises(ValueError, match="APPROVED"):
        _run(TradePlanStatus.DRAFT)
    with pytest.raises(ValueError, match="APPROVED"):
        _run(TradePlanStatus.READY_FOR_REVIEW)


def test_model_reference_requires_explicit_id_and_version():
    with pytest.raises(ValueError, match="model_id"):
        ModelReference("  ", "1.0.0")
    with pytest.raises(ValueError, match="model_version"):
        ModelReference("FT008", "  ")


def test_missing_input_cannot_carry_a_value_and_available_input_requires_one():
    EvaluationInput("bid", "1.23", DataAvailability.AVAILABLE, "provider:EODHD")
    with pytest.raises(ValueError, match="AVAILABLE input"):
        EvaluationInput("bid", None, DataAvailability.AVAILABLE, "provider:EODHD")
    with pytest.raises(ValueError, match="MISSING input"):
        EvaluationInput("bid", "1.23", DataAvailability.MISSING, "provider:EODHD")


def test_not_evaluable_criterion_requires_missing_or_insufficient_data():
    CriterionResult(
        "quote-available",
        CriterionOutcome.NOT_EVALUABLE,
        "Quote missing",
        data_availability=DataAvailability.MISSING,
    )
    with pytest.raises(ValueError, match="NOT_EVALUABLE"):
        CriterionResult(
            "quote-available",
            CriterionOutcome.NOT_EVALUABLE,
            "Quote missing",
            data_availability=DataAvailability.AVAILABLE,
        )


def test_calculated_metric_requires_formula_but_provider_metric_does_not():
    EvaluationMetric(
        "spread_pct",
        Decimal("2.5"),
        "%",
        MetricOrigin.CALCULATED,
        "bid/ask snapshot",
        formula_or_rule="(ask-bid)/mid*100",
    )
    EvaluationMetric(
        "delta",
        Decimal("0.42"),
        None,
        MetricOrigin.PROVIDER,
        "provider:EODHD",
    )
    with pytest.raises(ValueError, match="formula_or_rule"):
        EvaluationMetric(
            "spread_pct",
            Decimal("2.5"),
            "%",
            MetricOrigin.CALCULATED,
            "bid/ask snapshot",
        )


def test_evaluation_preserves_warrant_terms_and_listing_identity():
    run = _run()
    evaluation = _evaluation(run)
    assert evaluation.warrant_id
    assert evaluation.warrant_terms_version_id
    assert evaluation.warrant_listing_id
    assert evaluation.run_id == run.id


def test_ineligible_evaluation_requires_failed_criterion_and_reason():
    run = _run()
    _evaluation(run, EligibilityStatus.INELIGIBLE)
    with pytest.raises(ValueError, match="failed criterion"):
        ProductEvaluation(
            id=uuid4(),
            run_id=run.id,
            warrant_id=uuid4(),
            warrant_terms_version_id=uuid4(),
            warrant_listing_id=uuid4(),
            evaluated_at=NOW,
            eligibility_model=MODEL,
            evaluation_model=EVAL_MODEL,
            inputs=(),
            criteria=(
                CriterionResult(
                    "terms-valid",
                    CriterionOutcome.FULFILLED,
                    "Terms valid",
                ),
            ),
            metrics=(),
            eligibility_status=EligibilityStatus.INELIGIBLE,
            reasons=("Excluded",),
        )


def test_not_evaluable_evaluation_keeps_missing_data_visible():
    run = _run()
    evaluation = _evaluation(run, EligibilityStatus.NOT_EVALUABLE)
    assert evaluation.criteria[0].data_availability is DataAvailability.MISSING
    assert evaluation.reasons == ("Bid/ask quote is missing",)


def test_user_selection_must_reference_eligible_evaluation_from_same_run():
    run = _run()
    eligible = _evaluation(run)
    selection = ProductSelection.from_user_decision(
        id=uuid4(),
        run=run,
        evaluation=eligible,
        selected_at=NOW,
        selected_by=uuid4(),
        rationale=" preferred issuer ",
    )
    assert selection.run_id == run.id
    assert selection.product_evaluation_id == eligible.id
    assert selection.rationale == "preferred issuer"

    other_run = _run()
    with pytest.raises(ValueError, match="belong"):
        ProductSelection.from_user_decision(
            id=uuid4(),
            run=other_run,
            evaluation=eligible,
            selected_at=NOW,
            selected_by=uuid4(),
        )


def test_v1_user_selection_rejects_ineligible_and_not_evaluable_without_override() -> None:
    run = _run()
    for status in (EligibilityStatus.INELIGIBLE, EligibilityStatus.NOT_EVALUABLE):
        evaluation = _evaluation(run, status)
        with pytest.raises(ValueError, match="requires an ELIGIBLE"):
            ProductSelection.from_user_decision(
                id=uuid4(),
                run=run,
                evaluation=evaluation,
                selected_at=NOW,
                selected_by=uuid4(),
                rationale="manual override attempt",
            )
