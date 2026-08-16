"""FT-008 transparent Product Selection REST API."""

from __future__ import annotations

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, status

from app.features.product_selection.api.dependencies import (
    get_product_selection_command_service,
    get_product_selection_persistence_service,
    get_product_selection_query_service,
    get_product_selection_service,
)
from app.features.product_selection.api.dtos import (
    CriterionResultResponse,
    EvaluationInputResponse,
    EvaluationMetricResponse,
    ModelReferenceResponse,
    ProductEvaluationResponse,
    ProductSelectionResponse,
    ProductSelectionRunDetailResponse,
    ProductSelectionRunSummaryResponse,
    SelectProductRequest,
    StartProductSelectionRunRequest,
    UniverseOmissionResponse,
)
from app.features.product_selection.api.errors import translate_product_selection_error
from app.features.product_selection.domain.models import (
    ModelReference,
    ProductEvaluation,
    ProductSelection,
    ProductSelectionRun,
)
from app.features.product_selection.service.application import (
    ProductSelectionModels,
    ProductSelectionService,
)
from app.features.product_selection.service.commands import ProductSelectionCommandService
from app.features.product_selection.service.persistence import (
    ProductSelectionPersistenceService,
)
from app.features.product_selection.service.queries import (
    ProductSelectionQueryService,
    ProductSelectionRunView,
)
from app.features.product_selection.service.universe import UniverseOmission

router = APIRouter(prefix="/api/v1/product-selection-runs", tags=["product-selection"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
LOCAL_ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")
V1_MODELS = ProductSelectionModels(
    universe=ModelReference("ft008-product-universe", "1.0.0"),
    eligibility=ModelReference("ft008-reference-eligibility", "1.0.0"),
    evaluation=ModelReference("ft008-product-evaluation", "1.0.0"),
    direction_rule=None,
)


def _raise(error: ValueError) -> NoReturn:
    raise translate_product_selection_error(error) from error


def _model(value: ModelReference) -> ModelReferenceResponse:
    return ModelReferenceResponse(
        model_id=value.model_id,
        model_version=value.model_version,
    )


def _run(value: ProductSelectionRun) -> ProductSelectionRunSummaryResponse:
    return ProductSelectionRunSummaryResponse(
        id=value.id,
        trade_plan_id=value.trade_plan_id,
        trade_plan_version_id=value.trade_plan_version_id,
        trade_plan_version_status=value.trade_plan_version_status,
        underlying_id=value.underlying_id,
        evaluated_at=value.evaluated_at,
        universe_model=_model(value.universe_model),
        eligibility_model=_model(value.eligibility_model),
        evaluation_model=_model(value.evaluation_model),
        created_at=value.created_at,
        created_by=value.created_by,
    )


def _evaluation(value: ProductEvaluation) -> ProductEvaluationResponse:
    return ProductEvaluationResponse(
        id=value.id,
        run_id=value.run_id,
        warrant_id=value.warrant_id,
        warrant_terms_version_id=value.warrant_terms_version_id,
        warrant_listing_id=value.warrant_listing_id,
        evaluated_at=value.evaluated_at,
        eligibility_model=_model(value.eligibility_model),
        evaluation_model=_model(value.evaluation_model),
        inputs=[
            EvaluationInputResponse(
                name=item.name,
                value=item.value,
                availability=item.availability,
                source=item.source,
                observed_at=item.observed_at,
                quality=item.quality,
            )
            for item in value.inputs
        ],
        criteria=[
            CriterionResultResponse(
                criterion_id=item.criterion_id,
                outcome=item.outcome,
                explanation=item.explanation,
                actual_value=item.actual_value,
                expected_value=item.expected_value,
                data_availability=item.data_availability,
            )
            for item in value.criteria
        ],
        metrics=[
            EvaluationMetricResponse(
                metric_id=item.metric_id,
                value=item.value,
                unit=item.unit,
                origin=item.origin,
                source=item.source,
                formula_or_rule=item.formula_or_rule,
                data_availability=item.data_availability,
            )
            for item in value.metrics
        ],
        eligibility_status=value.eligibility_status,
        reasons=list(value.reasons),
    )


def _omission(value: UniverseOmission) -> UniverseOmissionResponse:
    return UniverseOmissionResponse(
        warrant_id=value.warrant_id,
        reason=value.reason.value,
        explanation=value.explanation,
    )


def _selection(value: ProductSelection | None) -> ProductSelectionResponse | None:
    if value is None:
        return None
    return ProductSelectionResponse(
        id=value.id,
        run_id=value.run_id,
        product_evaluation_id=value.product_evaluation_id,
        selected_at=value.selected_at,
        selected_by=value.selected_by,
        rationale=value.rationale,
    )


def _view(value: ProductSelectionRunView) -> ProductSelectionRunDetailResponse:
    return ProductSelectionRunDetailResponse(
        run=_run(value.run),
        evaluations=[_evaluation(item) for item in value.evaluations],
        universe_omissions=[_omission(item) for item in value.universe_omissions],
        selection=_selection(value.selection),
    )


@router.post(
    "",
    response_model=ProductSelectionRunDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_product_selection_run(
    request: StartProductSelectionRunRequest,
    service: Annotated[ProductSelectionService, Depends(get_product_selection_service)],
    persistence: Annotated[
        ProductSelectionPersistenceService,
        Depends(get_product_selection_persistence_service),
    ],
    query: Annotated[
        ProductSelectionQueryService,
        Depends(get_product_selection_query_service),
    ],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> ProductSelectionRunDetailResponse:
    try:
        result = await service.start_run(
            workspace_id=WORKSPACE_ID,
            trade_plan_id=request.trade_plan_id,
            trade_plan_version_id=request.trade_plan_version_id,
            actor=actor_id or LOCAL_ACTOR_ID,
            models=V1_MODELS,
            evaluated_at=request.evaluated_at,
        )
        await persistence.persist_run(result)
        return _view(await query.get_run(WORKSPACE_ID, result.run.id))
    except ValueError as exc:
        _raise(exc)


@router.get("", response_model=list[ProductSelectionRunSummaryResponse])
async def list_product_selection_runs(
    query: Annotated[
        ProductSelectionQueryService,
        Depends(get_product_selection_query_service),
    ],
    trade_plan_version_id: Annotated[UUID, Query()],
) -> list[ProductSelectionRunSummaryResponse]:
    try:
        runs = await query.list_for_trade_plan_version(
            WORKSPACE_ID,
            trade_plan_version_id,
        )
        return [_run(item) for item in runs]
    except ValueError as exc:
        _raise(exc)


@router.get("/{run_id}", response_model=ProductSelectionRunDetailResponse)
async def get_product_selection_run(
    run_id: UUID,
    query: Annotated[
        ProductSelectionQueryService,
        Depends(get_product_selection_query_service),
    ],
) -> ProductSelectionRunDetailResponse:
    try:
        return _view(await query.get_run(WORKSPACE_ID, run_id))
    except ValueError as exc:
        _raise(exc)


@router.get(
    "/{run_id}/evaluations/{evaluation_id}",
    response_model=ProductEvaluationResponse,
)
async def get_product_evaluation(
    run_id: UUID,
    evaluation_id: UUID,
    query: Annotated[
        ProductSelectionQueryService,
        Depends(get_product_selection_query_service),
    ],
) -> ProductEvaluationResponse:
    try:
        evaluation = await query.get_evaluation(
            WORKSPACE_ID,
            run_id,
            evaluation_id,
        )
        return _evaluation(evaluation)
    except ValueError as exc:
        _raise(exc)


@router.post(
    "/{run_id}/selection",
    response_model=ProductSelectionRunDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def select_product(
    run_id: UUID,
    request: SelectProductRequest,
    command: Annotated[
        ProductSelectionCommandService,
        Depends(get_product_selection_command_service),
    ],
    query: Annotated[
        ProductSelectionQueryService,
        Depends(get_product_selection_query_service),
    ],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> ProductSelectionRunDetailResponse:
    try:
        await command.select_product(
            workspace_id=WORKSPACE_ID,
            run_id=run_id,
            evaluation_id=request.product_evaluation_id,
            actor=actor_id or LOCAL_ACTOR_ID,
            rationale=request.rationale,
        )
        return _view(await query.get_run(WORKSPACE_ID, run_id))
    except ValueError as exc:
        _raise(exc)
