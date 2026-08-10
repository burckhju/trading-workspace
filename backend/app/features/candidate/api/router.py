"""FT-005 candidate REST API."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.features.candidate.api.dependencies import (
    get_candidate_live_workflow_service,
    get_candidate_service,
)
from app.features.candidate.api.dtos import (
    AutoEvaluateCandidateRequest,
    CandidateCriterionResponse,
    CandidateEvaluationDetailResponse,
    CandidateEvaluationResponse,
    CandidateResponse,
    CandidateLiveWorkflowResponse,
    CandidateLiveWorkflowStepResponse,
    ChangeCandidateStatusRequest,
    CreateCandidateRequest,
    EvaluateCandidateRequest,
)
from app.features.candidate.service.application import CandidateService
from app.features.candidate.service.live_workflow import CandidateLiveWorkflowService
from app.features.candidate.service.orchestration import StoredAnalysisReference

router = APIRouter(prefix="/api/v1/candidates", tags=["candidates"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


def _candidate(model: Any) -> CandidateResponse:
    return CandidateResponse(
        id=model.id,
        underlying_id=model.underlying_id,
        status=model.status,
        created_at=model.created_at,
        created_by=model.created_by,
    )


def _evaluation(model: Any) -> CandidateEvaluationResponse:
    return CandidateEvaluationResponse(
        id=model.id,
        version=model.version,
        direction=model.direction,
        model_id=model.model_id,
        model_version=model.model_version,
        qualification=model.qualification,
        quality_status=model.quality_status,
        warnings=model.warnings,
        evaluated_at=model.evaluated_at,
    )


@router.post("", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    request: CreateCandidateRequest,
    service: Annotated[CandidateService, Depends(get_candidate_service)],
    actor: Annotated[str | None, Header(alias="X-Actor-Name")] = None,
) -> CandidateResponse:
    try:
        return _candidate(
            await service.create(
                WORKSPACE_ID, request.underlying_id, actor or "Trading Workspace User"
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[CandidateResponse])
async def list_candidates(
    service: Annotated[CandidateService, Depends(get_candidate_service)],
) -> list[CandidateResponse]:
    return [_candidate(item) for item in await service.list(WORKSPACE_ID)]


@router.get(
    "/{candidate_id}/live-workflow",
    response_model=CandidateLiveWorkflowResponse,
)
async def candidate_live_workflow(
    candidate_id: UUID,
    service: Annotated[CandidateLiveWorkflowService, Depends(get_candidate_live_workflow_service)],
) -> CandidateLiveWorkflowResponse:
    """Return the exact next operator action for the live top-down path."""
    try:
        value = await service.inspect(workspace_id=WORKSPACE_ID, candidate_id=candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CandidateLiveWorkflowResponse(
        candidate_id=value.candidate_id,
        underlying_id=value.underlying_id,
        as_of=value.as_of,
        ready=value.ready,
        can_evaluate=value.can_evaluate,
        next_action=value.next_action,
        steps=[CandidateLiveWorkflowStepResponse(**{
            "code": step.code, "label": step.label, "status": step.status,
            "detail": step.detail, "action": step.action, "resource_id": step.resource_id,
            "action_params": getattr(step, "action_params", None)
        }) for step in value.steps],
    )


@router.post(
    "/{candidate_id}/evaluations/auto",
    response_model=CandidateEvaluationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def evaluate_candidate_auto(
    candidate_id: UUID,
    request: AutoEvaluateCandidateRequest,
    service: Annotated[CandidateService, Depends(get_candidate_service)],
) -> CandidateEvaluationResponse:
    """Evaluate using only server-resolved semantic top-down sources."""
    try:
        return _evaluation(
            await service.evaluate_auto(WORKSPACE_ID, candidate_id, request.as_of)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/{candidate_id}/evaluations",
    response_model=CandidateEvaluationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def evaluate_candidate(
    candidate_id: UUID,
    request: EvaluateCandidateRequest,
    service: Annotated[CandidateService, Depends(get_candidate_service)],
) -> CandidateEvaluationResponse:
    try:
        model = await service.evaluate_from_analyses(
            WORKSPACE_ID,
            candidate_id,
            StoredAnalysisReference(
                request.market_source.analysis_id, request.market_source.version
            ),
            StoredAnalysisReference(
                request.sector_source.analysis_id, request.sector_source.version
            ),
            StoredAnalysisReference(
                request.underlying_source.analysis_id, request.underlying_source.version
            ),
        )
        return _evaluation(model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{candidate_id}/evaluations", response_model=list[CandidateEvaluationDetailResponse])
async def list_candidate_evaluations(
    candidate_id: UUID,
    service: Annotated[CandidateService, Depends(get_candidate_service)],
) -> list[CandidateEvaluationDetailResponse]:
    await service.get(WORKSPACE_ID, candidate_id)
    output: list[CandidateEvaluationDetailResponse] = []
    for model in await service.list_evaluations(candidate_id):
        criteria = await service.list_criteria(model.id)
        output.append(
            CandidateEvaluationDetailResponse(
                **_evaluation(model).model_dump(),
                criteria=[
                    CandidateCriterionResponse(
                        criterion_id=item.criterion_id,
                        group=item.criterion_group,
                        severity=item.severity,
                        evaluation=item.evaluation,
                        source=item.source,
                        actual_value=item.actual_value,
                        expected_value=item.expected_value,
                        numeric_value=None
                        if item.numeric_value is None
                        else str(item.numeric_value),
                        explanation=item.explanation,
                    )
                    for item in criteria
                ],
            )
        )
    return output


@router.post("/{candidate_id}/status", response_model=CandidateResponse)
async def change_candidate_status(
    candidate_id: UUID,
    request: ChangeCandidateStatusRequest,
    service: Annotated[CandidateService, Depends(get_candidate_service)],
    actor: Annotated[str | None, Header(alias="X-Actor-Name")] = None,
) -> CandidateResponse:
    try:
        return _candidate(
            await service.change_status(
                WORKSPACE_ID,
                candidate_id,
                request.status,
                actor or "Trading Workspace User",
                request.reason,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
