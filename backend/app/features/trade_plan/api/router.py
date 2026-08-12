"""FT-007 product-neutral TradePlan REST API."""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated, Any, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status

from app.features.trade_plan.api.dependencies import (
    get_trade_plan_query_service,
    get_trade_plan_service,
)
from app.features.trade_plan.api.dtos import (
    AmendTradePlanRequest,
    ApprovalResponse,
    CandidateEvaluationProvenanceResponse,
    CandidateEvaluationSourceResponse,
    CreateTradePlanRequest,
    EntryPlanResponse,
    InvalidationPlanResponse,
    LifecycleEventResponse,
    LifecycleReasonRequest,
    RiskAssumptionsResponse,
    TargetResponse,
    TradePlanDetailResponse,
    TradePlanSummaryResponse,
    TradePlanVersionResponse,
)
from app.features.trade_plan.api.errors import translate_trade_plan_error
from app.features.trade_plan.domain.enums import TradePlanOriginType
from app.features.trade_plan.domain.models import (
    EntryPlan,
    InvalidationPlan,
    RiskAssumptions,
    Target,
    TradePlan,
    TradePlanVersion,
)
from app.features.trade_plan.service.application import TradePlanService
from app.features.trade_plan.service.queries import (
    TradePlanQueryService,
    TradePlanVersionView,
)

router = APIRouter(prefix="/api/v1/trade-plans", tags=["trade-plans"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
LOCAL_ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")


def _actor(value: UUID | None) -> UUID:
    return value or LOCAL_ACTOR_ID


def _content(
    request: CreateTradePlanRequest | AmendTradePlanRequest,
) -> tuple[str, EntryPlan, InvalidationPlan, tuple[Target, ...], RiskAssumptions]:
    return (
        request.thesis,
        EntryPlan(**request.entry.model_dump()),
        InvalidationPlan(**request.invalidation.model_dump()),
        tuple(Target(**item.model_dump()) for item in request.targets),
        RiskAssumptions(**request.risk_assumptions.model_dump()),
    )


def _plan(plan: TradePlan) -> TradePlanSummaryResponse:
    return TradePlanSummaryResponse(
        id=plan.id,
        underlying_id=plan.underlying_id,
        origin_type=plan.origin_type,
        candidate_id=plan.candidate_id,
        candidate_evaluation_id=plan.candidate_evaluation_id,
        created_at=plan.created_at,
        created_by=plan.created_by,
    )


def _version(version: TradePlanVersion) -> TradePlanVersionResponse:
    return TradePlanVersionResponse(
        id=version.id,
        trade_plan_id=version.trade_plan_id,
        version=version.version,
        direction=version.direction,
        thesis=version.thesis,
        entry=EntryPlanResponse(**vars_from_slots(version.entry)),
        invalidation=InvalidationPlanResponse(**vars_from_slots(version.invalidation)),
        targets=[TargetResponse(**vars_from_slots(item)) for item in version.targets],
        risk_assumptions=RiskAssumptionsResponse(
            **vars_from_slots(version.risk_assumptions)
        ),
        status=version.status,
        created_at=version.created_at,
        created_by=version.created_by,
        previous_version_id=version.previous_version_id,
        change_reason=version.change_reason,
    )


def vars_from_slots(value: Any) -> dict[str, Any]:
    return asdict(value)


def _view(view: TradePlanVersionView) -> TradePlanVersionResponse:
    response = _version(view.version)
    candidate = view.candidate_evaluation
    approval = view.approval
    return response.model_copy(
        update={
            "candidate_evaluation": (
                None
                if candidate is None
                else CandidateEvaluationProvenanceResponse(
                    candidate_id=candidate.candidate_id,
                    evaluation_id=candidate.evaluation_id,
                    evaluation_version=candidate.evaluation_version,
                    direction=candidate.direction,
                    model_id=candidate.model_id,
                    model_version=candidate.model_version,
                    qualification=candidate.qualification,
                    quality_status=candidate.quality_status,
                    evaluated_at=candidate.evaluated_at,
                    sources=[
                        CandidateEvaluationSourceResponse(**vars_from_slots(item))
                        for item in candidate.sources
                    ],
                )
            ),
            "approval": (
                None
                if approval is None
                else ApprovalResponse(**vars_from_slots(approval))
            ),
            "events": [
                LifecycleEventResponse(**vars_from_slots(item)) for item in view.events
            ],
        }
    )


def _raise(error: ValueError) -> NoReturn:
    raise translate_trade_plan_error(error) from error


@router.post(
    "", response_model=TradePlanDetailResponse, status_code=status.HTTP_201_CREATED
)
async def create_trade_plan(
    request: CreateTradePlanRequest,
    service: Annotated[TradePlanService, Depends(get_trade_plan_service)],
    query: Annotated[TradePlanQueryService, Depends(get_trade_plan_query_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
    correlation_id: Annotated[str | None, Header(alias="X-Correlation-ID")] = None,
) -> TradePlanDetailResponse:
    try:
        thesis, entry, invalidation, targets, risk_assumptions = _content(request)
        if request.origin_type is TradePlanOriginType.MANUAL:
            if request.underlying_id is None:
                raise ValueError("manual trade plan requires underlying_id")
            plan, version = await service.create_manual(
                workspace_id=WORKSPACE_ID,
                underlying_id=request.underlying_id,
                actor=_actor(actor_id),
                thesis=thesis,
                entry=entry,
                invalidation=invalidation,
                targets=targets,
                risk_assumptions=risk_assumptions,
                correlation_id=correlation_id,
            )
        else:
            if request.candidate_id is None or request.candidate_evaluation_id is None:
                raise ValueError(
                    "candidate-originated trade plan requires candidate provenance"
                )
            plan, version = await service.create_from_candidate(
                workspace_id=WORKSPACE_ID,
                candidate_id=request.candidate_id,
                candidate_evaluation_id=request.candidate_evaluation_id,
                actor=_actor(actor_id),
                thesis=thesis,
                entry=entry,
                invalidation=invalidation,
                targets=targets,
                risk_assumptions=risk_assumptions,
                correlation_id=correlation_id,
            )
        view = await query.get_version(WORKSPACE_ID, plan.id, version.id)
        return TradePlanDetailResponse(plan=_plan(plan), latest_version=_view(view))
    except ValueError as exc:
        _raise(exc)


@router.get("/{trade_plan_id}", response_model=TradePlanDetailResponse)
async def get_trade_plan(
    trade_plan_id: UUID,
    query: Annotated[TradePlanQueryService, Depends(get_trade_plan_query_service)],
) -> TradePlanDetailResponse:
    try:
        versions = await query.list_versions(WORKSPACE_ID, trade_plan_id)
        if not versions:
            raise ValueError("trade plan has no versions")
        latest = max(versions, key=lambda item: item.version.version)
        return TradePlanDetailResponse(
            plan=_plan(latest.plan), latest_version=_view(latest)
        )
    except ValueError as exc:
        _raise(exc)


@router.get("/{trade_plan_id}/versions", response_model=list[TradePlanVersionResponse])
async def list_trade_plan_versions(
    trade_plan_id: UUID,
    query: Annotated[TradePlanQueryService, Depends(get_trade_plan_query_service)],
) -> list[TradePlanVersionResponse]:
    try:
        return [
            _view(item)
            for item in await query.list_versions(WORKSPACE_ID, trade_plan_id)
        ]
    except ValueError as exc:
        _raise(exc)


@router.get(
    "/{trade_plan_id}/versions/{version_id}", response_model=TradePlanVersionResponse
)
async def get_trade_plan_version(
    trade_plan_id: UUID,
    version_id: UUID,
    query: Annotated[TradePlanQueryService, Depends(get_trade_plan_query_service)],
) -> TradePlanVersionResponse:
    try:
        return _view(await query.get_version(WORKSPACE_ID, trade_plan_id, version_id))
    except ValueError as exc:
        _raise(exc)


@router.post(
    "/{trade_plan_id}/versions/{base_version_id}/amendments",
    response_model=TradePlanVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def amend_trade_plan(
    trade_plan_id: UUID,
    base_version_id: UUID,
    request: AmendTradePlanRequest,
    service: Annotated[TradePlanService, Depends(get_trade_plan_service)],
    query: Annotated[TradePlanQueryService, Depends(get_trade_plan_query_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
    correlation_id: Annotated[str | None, Header(alias="X-Correlation-ID")] = None,
) -> TradePlanVersionResponse:
    try:
        thesis, entry, invalidation, targets, risk_assumptions = _content(request)
        version = await service.amend(
            workspace_id=WORKSPACE_ID,
            trade_plan_id=trade_plan_id,
            base_version_id=base_version_id,
            actor=_actor(actor_id),
            change_reason=request.change_reason,
            thesis=thesis,
            entry=entry,
            invalidation=invalidation,
            targets=targets,
            risk_assumptions=risk_assumptions,
            correlation_id=correlation_id,
        )
        return _view(await query.get_version(WORKSPACE_ID, trade_plan_id, version.id))
    except ValueError as exc:
        _raise(exc)


async def _lifecycle(
    action: str,
    service: TradePlanService,
    query: TradePlanQueryService,
    trade_plan_id: UUID,
    version_id: UUID,
    actor_id: UUID | None,
    correlation_id: str | None,
    reason: str | None = None,
) -> TradePlanVersionResponse:
    try:
        actor = _actor(actor_id)
        if action == "submit-review":
            version = await service.submit_for_review(
                WORKSPACE_ID, trade_plan_id, version_id, actor, correlation_id
            )
        elif action == "return-draft":
            version = await service.return_to_draft(
                WORKSPACE_ID, trade_plan_id, version_id, actor, reason, correlation_id
            )
        elif action == "abandon":
            version = await service.abandon(
                WORKSPACE_ID, trade_plan_id, version_id, actor, reason, correlation_id
            )
        else:
            version = await service.approve(
                WORKSPACE_ID, trade_plan_id, version_id, actor, correlation_id
            )
        return _view(await query.get_version(WORKSPACE_ID, trade_plan_id, version.id))
    except ValueError as exc:
        _raise(exc)


@router.post(
    "/{trade_plan_id}/versions/{version_id}/submit-review",
    response_model=TradePlanVersionResponse,
)
async def submit_trade_plan_for_review(
    trade_plan_id: UUID,
    version_id: UUID,
    service: Annotated[TradePlanService, Depends(get_trade_plan_service)],
    query: Annotated[TradePlanQueryService, Depends(get_trade_plan_query_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
    correlation_id: Annotated[str | None, Header(alias="X-Correlation-ID")] = None,
) -> TradePlanVersionResponse:
    return await _lifecycle(
        "submit-review",
        service,
        query,
        trade_plan_id,
        version_id,
        actor_id,
        correlation_id,
    )


@router.post(
    "/{trade_plan_id}/versions/{version_id}/return-draft",
    response_model=TradePlanVersionResponse,
)
async def return_trade_plan_to_draft(
    trade_plan_id: UUID,
    version_id: UUID,
    request: LifecycleReasonRequest,
    service: Annotated[TradePlanService, Depends(get_trade_plan_service)],
    query: Annotated[TradePlanQueryService, Depends(get_trade_plan_query_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
    correlation_id: Annotated[str | None, Header(alias="X-Correlation-ID")] = None,
) -> TradePlanVersionResponse:
    return await _lifecycle(
        "return-draft",
        service,
        query,
        trade_plan_id,
        version_id,
        actor_id,
        correlation_id,
        request.reason,
    )


@router.post(
    "/{trade_plan_id}/versions/{version_id}/abandon",
    response_model=TradePlanVersionResponse,
)
async def abandon_trade_plan(
    trade_plan_id: UUID,
    version_id: UUID,
    request: LifecycleReasonRequest,
    service: Annotated[TradePlanService, Depends(get_trade_plan_service)],
    query: Annotated[TradePlanQueryService, Depends(get_trade_plan_query_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
    correlation_id: Annotated[str | None, Header(alias="X-Correlation-ID")] = None,
) -> TradePlanVersionResponse:
    return await _lifecycle(
        "abandon",
        service,
        query,
        trade_plan_id,
        version_id,
        actor_id,
        correlation_id,
        request.reason,
    )


@router.post(
    "/{trade_plan_id}/versions/{version_id}/approve",
    response_model=TradePlanVersionResponse,
)
async def approve_trade_plan(
    trade_plan_id: UUID,
    version_id: UUID,
    service: Annotated[TradePlanService, Depends(get_trade_plan_service)],
    query: Annotated[TradePlanQueryService, Depends(get_trade_plan_query_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
    correlation_id: Annotated[str | None, Header(alias="X-Correlation-ID")] = None,
) -> TradePlanVersionResponse:
    return await _lifecycle(
        "approve", service, query, trade_plan_id, version_id, actor_id, correlation_id
    )
