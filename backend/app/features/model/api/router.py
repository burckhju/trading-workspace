"""FT-013 controlled model-governance REST API.

This API intentionally has no activation endpoint. Approval creates immutable
approved model versions but does not switch runtime consumers.
"""

from __future__ import annotations

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status

from app.features.model.api.dependencies import get_model_governance_service
from app.features.model.api.dtos import (
    ApprovalResponse,
    CreateHypothesisRequest,
    CreateModelRequest,
    CreateProposalRequest,
    HypothesisResponse,
    ModelDetailResponse,
    ModelResponse,
    ModelVersionResponse,
    ProposalApprovalResponse,
    ProposalResponse,
    ValidateProposalRequest,
    ValidationResponse,
)
from app.features.model.api.errors import translate_model_governance_error
from app.features.model.domain.enums import (
    HypothesisStatus,
    ModelVersionStatus,
    ProposalStatus,
    ValidationConclusion,
    ValidationMethod,
)
from app.features.model.domain.models import (
    GovernedModel,
    Hypothesis,
    ModelApproval,
    ModelChangeProposal,
    ModelValidation,
    ModelVersion,
)
from app.features.model.persistence.models import (
    GovernedModelRecord,
    ModelChangeProposalRecord,
    ModelVersionRecord,
)
from app.features.model.service.application import ModelGovernanceService

router = APIRouter(prefix="/api/v1/model-governance", tags=["model-governance"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
LOCAL_ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")


def _actor(value: UUID | None) -> UUID:
    return value or LOCAL_ACTOR_ID


def _raise(error: ValueError) -> NoReturn:
    raise translate_model_governance_error(error) from error


def _model(value: GovernedModel | GovernedModelRecord) -> ModelResponse:
    return ModelResponse(
        id=value.id,
        model_key=value.model_key,
        name=value.name,
        purpose=value.purpose,
        created_at=value.created_at,
        created_by=value.created_by,
    )


def _version(value: ModelVersion | ModelVersionRecord) -> ModelVersionResponse:
    return ModelVersionResponse(
        id=value.id,
        model_id=value.model_id,
        version=value.version,
        status=ModelVersionStatus(value.status),
        definition=value.definition,
        change_summary=value.change_summary,
        created_at=value.created_at,
        created_by=value.created_by,
        previous_version_id=value.previous_version_id,
    )


def _hypothesis(value: Hypothesis) -> HypothesisResponse:
    return HypothesisResponse(
        id=value.id,
        title=value.title,
        statement=value.statement,
        status=HypothesisStatus(value.status),
        source_lesson_version_id=value.source_lesson_version_id,
        created_at=value.created_at,
        created_by=value.created_by,
    )


def _proposal(value: ModelChangeProposal | ModelChangeProposalRecord) -> ProposalResponse:
    return ProposalResponse(
        id=value.id,
        model_id=value.model_id,
        base_model_version_id=value.base_model_version_id,
        hypothesis_id=value.hypothesis_id,
        status=ProposalStatus(value.status),
        proposed_definition=value.proposed_definition,
        rationale=value.rationale,
        created_at=value.created_at,
        created_by=value.created_by,
    )


def _validation(value: ModelValidation) -> ValidationResponse:
    return ValidationResponse(
        id=value.id,
        proposal_id=value.proposal_id,
        method=ValidationMethod(value.method),
        evidence_cutoff_at=value.evidence_cutoff_at,
        conclusion=ValidationConclusion(value.conclusion),
        metrics=value.metrics,
        notes=value.notes,
        created_at=value.created_at,
        created_by=value.created_by,
    )


def _approval(value: ModelApproval) -> ApprovalResponse:
    return ApprovalResponse(
        id=value.id,
        proposal_id=value.proposal_id,
        model_version_id=value.model_version_id,
        approved_at=value.approved_at,
        approved_by=value.approved_by,
        correlation_id=value.correlation_id,
    )


@router.post("/models", response_model=ModelDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_model(
    request: CreateModelRequest,
    service: Annotated[ModelGovernanceService, Depends(get_model_governance_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> ModelDetailResponse:
    try:
        model, version = await service.create_model(
            workspace_id=WORKSPACE_ID,
            model_key=request.model_key,
            name=request.name,
            purpose=request.purpose,
            initial_definition=request.initial_definition,
            actor=_actor(actor_id),
        )
        return ModelDetailResponse(model=_model(model), initial_version=_version(version))
    except ValueError as exc:
        _raise(exc)


@router.get("/models", response_model=list[ModelResponse])
async def list_models(
    service: Annotated[ModelGovernanceService, Depends(get_model_governance_service)],
) -> list[ModelResponse]:
    return [_model(item) for item in await service.list_models(WORKSPACE_ID)]


@router.get("/models/{model_id}/versions", response_model=list[ModelVersionResponse])
async def list_model_versions(
    model_id: UUID,
    service: Annotated[ModelGovernanceService, Depends(get_model_governance_service)],
) -> list[ModelVersionResponse]:
    try:
        return [_version(item) for item in await service.list_versions(WORKSPACE_ID, model_id)]
    except ValueError as exc:
        _raise(exc)


@router.post(
    "/models/{model_id}/versions/{version_id}/approve",
    response_model=ApprovalResponse,
)
async def approve_initial_model_version(
    model_id: UUID,
    version_id: UUID,
    service: Annotated[ModelGovernanceService, Depends(get_model_governance_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
    correlation_id: Annotated[str | None, Header(alias="X-Correlation-ID")] = None,
) -> ApprovalResponse:
    try:
        approval = await service.approve_initial_version(
            workspace_id=WORKSPACE_ID,
            model_id=model_id,
            version_id=version_id,
            actor=_actor(actor_id),
            correlation_id=correlation_id,
        )
        return _approval(approval)
    except ValueError as exc:
        _raise(exc)


@router.post(
    "/hypotheses",
    response_model=HypothesisResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_hypothesis(
    request: CreateHypothesisRequest,
    service: Annotated[ModelGovernanceService, Depends(get_model_governance_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> HypothesisResponse:
    try:
        value = await service.create_hypothesis(
            workspace_id=WORKSPACE_ID,
            title=request.title,
            statement=request.statement,
            evidence_ids=tuple(request.evidence_ids),
            source_lesson_version_id=request.source_lesson_version_id,
            actor=_actor(actor_id),
        )
        return _hypothesis(value)
    except ValueError as exc:
        _raise(exc)


@router.post(
    "/proposals",
    response_model=ProposalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_proposal(
    request: CreateProposalRequest,
    service: Annotated[ModelGovernanceService, Depends(get_model_governance_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> ProposalResponse:
    try:
        value = await service.create_proposal(
            workspace_id=WORKSPACE_ID,
            model_id=request.model_id,
            base_model_version_id=request.base_model_version_id,
            hypothesis_id=request.hypothesis_id,
            proposed_definition=request.proposed_definition,
            rationale=request.rationale,
            actor=_actor(actor_id),
        )
        return _proposal(value)
    except ValueError as exc:
        _raise(exc)


@router.get("/proposals/{proposal_id}", response_model=ProposalResponse)
async def get_proposal(
    proposal_id: UUID,
    service: Annotated[ModelGovernanceService, Depends(get_model_governance_service)],
) -> ProposalResponse:
    try:
        return _proposal(await service.get_proposal(WORKSPACE_ID, proposal_id))
    except ValueError as exc:
        _raise(exc)


@router.post(
    "/proposals/{proposal_id}/validations",
    response_model=ValidationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def validate_proposal(
    proposal_id: UUID,
    request: ValidateProposalRequest,
    service: Annotated[ModelGovernanceService, Depends(get_model_governance_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> ValidationResponse:
    try:
        value = await service.validate_proposal(
            workspace_id=WORKSPACE_ID,
            proposal_id=proposal_id,
            evidence_ids=tuple(request.evidence_ids),
            evidence_cutoff_at=request.evidence_cutoff_at,
            conclusion=request.conclusion,
            metrics=request.metrics,
            notes=request.notes,
            actor=_actor(actor_id),
        )
        return _validation(value)
    except ValueError as exc:
        _raise(exc)


@router.post(
    "/proposals/{proposal_id}/approve",
    response_model=ProposalApprovalResponse,
)
async def approve_proposal(
    proposal_id: UUID,
    service: Annotated[ModelGovernanceService, Depends(get_model_governance_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
    correlation_id: Annotated[str | None, Header(alias="X-Correlation-ID")] = None,
) -> ProposalApprovalResponse:
    try:
        version, approval = await service.approve_proposal(
            workspace_id=WORKSPACE_ID,
            proposal_id=proposal_id,
            actor=_actor(actor_id),
            correlation_id=correlation_id,
        )
        return ProposalApprovalResponse(
            model_version=_version(version),
            approval=_approval(approval),
        )
    except ValueError as exc:
        _raise(exc)
