"""Mapping between immutable FT-008 domain snapshots and SQLAlchemy rows."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID, uuid4

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
from app.features.product_selection.persistence.models import (
    ProductEvaluationCriterionModel,
    ProductEvaluationInputModel,
    ProductEvaluationMetricModel,
    ProductEvaluationModel,
    ProductEvaluationReasonModel,
    ProductSelectionModel,
    ProductSelectionRunModel,
    ProductUniverseOmissionModel,
)
from app.features.product_selection.service.universe import UniverseOmission, UniverseOmissionReason
from app.features.trade_plan.domain.enums import TradePlanStatus


def run_to_model(run: ProductSelectionRun) -> ProductSelectionRunModel:
    return ProductSelectionRunModel(
        id=run.id,
        workspace_id=run.workspace_id,
        trade_plan_id=run.trade_plan_id,
        trade_plan_version_id=run.trade_plan_version_id,
        trade_plan_version_status=run.trade_plan_version_status.value,
        underlying_id=run.underlying_id,
        evaluated_at=run.evaluated_at,
        universe_model_id=run.universe_model.model_id,
        universe_model_version=run.universe_model.model_version,
        eligibility_model_id=run.eligibility_model.model_id,
        eligibility_model_version=run.eligibility_model.model_version,
        evaluation_model_id=run.evaluation_model.model_id,
        evaluation_model_version=run.evaluation_model.model_version,
        created_at=run.created_at,
        created_by=run.created_by,
    )


def run_from_model(model: ProductSelectionRunModel) -> ProductSelectionRun:
    return ProductSelectionRun(
        id=model.id,
        workspace_id=model.workspace_id,
        trade_plan_id=model.trade_plan_id,
        trade_plan_version_id=model.trade_plan_version_id,
        trade_plan_version_status=TradePlanStatus(model.trade_plan_version_status),
        underlying_id=model.underlying_id,
        evaluated_at=model.evaluated_at,
        universe_model=ModelReference(model.universe_model_id, model.universe_model_version),
        eligibility_model=ModelReference(
            model.eligibility_model_id, model.eligibility_model_version
        ),
        evaluation_model=ModelReference(model.evaluation_model_id, model.evaluation_model_version),
        created_at=model.created_at,
        created_by=model.created_by,
    )


def evaluation_to_models(
    evaluation: ProductEvaluation,
) -> tuple[
    ProductEvaluationModel,
    tuple[ProductEvaluationInputModel, ...],
    tuple[ProductEvaluationCriterionModel, ...],
    tuple[ProductEvaluationMetricModel, ...],
    tuple[ProductEvaluationReasonModel, ...],
]:
    root = ProductEvaluationModel(
        id=evaluation.id,
        run_id=evaluation.run_id,
        warrant_id=evaluation.warrant_id,
        warrant_terms_version_id=evaluation.warrant_terms_version_id,
        warrant_listing_id=evaluation.warrant_listing_id,
        evaluated_at=evaluation.evaluated_at,
        eligibility_model_id=evaluation.eligibility_model.model_id,
        eligibility_model_version=evaluation.eligibility_model.model_version,
        evaluation_model_id=evaluation.evaluation_model.model_id,
        evaluation_model_version=evaluation.evaluation_model.model_version,
        eligibility_status=evaluation.eligibility_status.value,
    )
    inputs = tuple(
        ProductEvaluationInputModel(
            id=uuid4(),
            product_evaluation_id=evaluation.id,
            sequence=i,
            name=item.name,
            value=item.value,
            availability=item.availability.value,
            source=item.source,
            observed_at=item.observed_at,
            quality=item.quality,
        )
        for i, item in enumerate(evaluation.inputs, 1)
    )
    criteria = tuple(
        ProductEvaluationCriterionModel(
            id=uuid4(),
            product_evaluation_id=evaluation.id,
            sequence=i,
            criterion_id=item.criterion_id,
            outcome=item.outcome.value,
            explanation=item.explanation,
            actual_value=item.actual_value,
            expected_value=item.expected_value,
            data_availability=item.data_availability.value,
        )
        for i, item in enumerate(evaluation.criteria, 1)
    )
    metrics = tuple(
        ProductEvaluationMetricModel(
            id=uuid4(),
            product_evaluation_id=evaluation.id,
            sequence=i,
            metric_id=item.metric_id,
            value=item.value,
            unit=item.unit,
            origin=item.origin.value,
            source=item.source,
            formula_or_rule=item.formula_or_rule,
            data_availability=item.data_availability.value,
        )
        for i, item in enumerate(evaluation.metrics, 1)
    )
    reasons = tuple(
        ProductEvaluationReasonModel(
            id=uuid4(), product_evaluation_id=evaluation.id, sequence=i, reason=reason
        )
        for i, reason in enumerate(evaluation.reasons, 1)
    )
    return root, inputs, criteria, metrics, reasons


def evaluation_from_models(
    model: ProductEvaluationModel,
    inputs: Sequence[ProductEvaluationInputModel],
    criteria: Sequence[ProductEvaluationCriterionModel],
    metrics: Sequence[ProductEvaluationMetricModel],
    reasons: Sequence[ProductEvaluationReasonModel],
) -> ProductEvaluation:
    return ProductEvaluation(
        id=model.id,
        run_id=model.run_id,
        warrant_id=model.warrant_id,
        warrant_terms_version_id=model.warrant_terms_version_id,
        warrant_listing_id=model.warrant_listing_id,
        evaluated_at=model.evaluated_at,
        eligibility_model=ModelReference(
            model.eligibility_model_id, model.eligibility_model_version
        ),
        evaluation_model=ModelReference(model.evaluation_model_id, model.evaluation_model_version),
        inputs=tuple(
            EvaluationInput(
                name=x.name,
                value=x.value,
                availability=DataAvailability(x.availability),
                source=x.source,
                observed_at=x.observed_at,
                quality=x.quality,
            )
            for x in sorted(inputs, key=lambda x: x.sequence)
        ),
        criteria=tuple(
            CriterionResult(
                criterion_id=x.criterion_id,
                outcome=CriterionOutcome(x.outcome),
                explanation=x.explanation,
                actual_value=x.actual_value,
                expected_value=x.expected_value,
                data_availability=DataAvailability(x.data_availability),
            )
            for x in sorted(criteria, key=lambda x: x.sequence)
        ),
        metrics=tuple(
            EvaluationMetric(
                metric_id=x.metric_id,
                value=x.value,
                unit=x.unit,
                origin=MetricOrigin(x.origin),
                source=x.source,
                formula_or_rule=x.formula_or_rule,
                data_availability=DataAvailability(x.data_availability),
            )
            for x in sorted(metrics, key=lambda x: x.sequence)
        ),
        eligibility_status=EligibilityStatus(model.eligibility_status),
        reasons=tuple(x.reason for x in sorted(reasons, key=lambda x: x.sequence)),
    )


def omission_to_model(run_id: UUID, omission: UniverseOmission) -> ProductUniverseOmissionModel:
    return ProductUniverseOmissionModel(
        id=uuid4(),
        run_id=run_id,
        warrant_id=omission.warrant_id,
        reason=omission.reason.value,
        explanation=omission.explanation,
    )


def omission_from_model(model: ProductUniverseOmissionModel) -> UniverseOmission:
    return UniverseOmission(
        model.warrant_id, UniverseOmissionReason(model.reason), model.explanation
    )


def selection_to_model(selection: ProductSelection) -> ProductSelectionModel:
    return ProductSelectionModel(
        id=selection.id,
        run_id=selection.run_id,
        product_evaluation_id=selection.product_evaluation_id,
        selected_at=selection.selected_at,
        selected_by=selection.selected_by,
        rationale=selection.rationale,
    )


def selection_from_model(model: ProductSelectionModel) -> ProductSelection:
    return ProductSelection(
        id=model.id,
        run_id=model.run_id,
        product_evaluation_id=model.product_evaluation_id,
        selected_at=model.selected_at,
        selected_by=model.selected_by,
        rationale=model.rationale,
    )
