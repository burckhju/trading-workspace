"""Explicit FT-013 APPROVED ModelVersion -> runtime activation API."""

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.model.api.dtos import ModelVersionResponse
from app.features.model.api.errors import translate_model_governance_error
from app.features.model.domain.enums import ModelVersionStatus
from app.features.model.persistence.models import ModelVersionRecord
from app.features.model.persistence.runtime_activation_models import ModelRuntimeActivationRecord
from app.features.model.service.runtime_activation_service import RuntimeActivationService

router = APIRouter(prefix="/api/v1/model-governance", tags=["model-governance"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
LOCAL_ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")


class RuntimeActivationResponse(BaseModel):
    id: UUID
    model_id: UUID
    model_version_id: UUID
    activated_at: datetime
    activated_by: UUID
    correlation_id: str | None = None
    model_version: ModelVersionResponse


async def get_runtime_activation_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AsyncIterator[RuntimeActivationService]:
    yield RuntimeActivationService(session)


def _raise(error: ValueError) -> NoReturn:
    raise translate_model_governance_error(error) from error


def _response(
    value: tuple[ModelRuntimeActivationRecord, ModelVersionRecord],
) -> RuntimeActivationResponse:
    activation, version = value
    return RuntimeActivationResponse(
        id=activation.id,
        model_id=activation.model_id,
        model_version_id=activation.model_version_id,
        activated_at=activation.activated_at,
        activated_by=activation.activated_by,
        correlation_id=activation.correlation_id,
        model_version=ModelVersionResponse(
            id=version.id,
            model_id=version.model_id,
            version=version.version,
            status=ModelVersionStatus(version.status),
            definition=version.definition,
            change_summary=version.change_summary,
            created_at=version.created_at,
            created_by=version.created_by,
            previous_version_id=version.previous_version_id,
        ),
    )


@router.get(
    "/models/{model_id}/runtime-activation",
    response_model=RuntimeActivationResponse | None,
)
async def get_runtime_activation(
    model_id: UUID,
    service: Annotated[RuntimeActivationService, Depends(get_runtime_activation_service)],
) -> RuntimeActivationResponse | None:
    try:
        current = await service.get_current(workspace_id=WORKSPACE_ID, model_id=model_id)
        return None if current is None else _response(current)
    except ValueError as exc:
        _raise(exc)


@router.post(
    "/models/{model_id}/versions/{version_id}/activate",
    response_model=RuntimeActivationResponse,
)
async def activate_model_version(
    model_id: UUID,
    version_id: UUID,
    service: Annotated[RuntimeActivationService, Depends(get_runtime_activation_service)],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
    correlation_id: Annotated[str | None, Header(alias="X-Correlation-ID")] = None,
) -> RuntimeActivationResponse:
    try:
        result = await service.activate(
            workspace_id=WORKSPACE_ID,
            model_id=model_id,
            model_version_id=version_id,
            actor=actor_id or LOCAL_ACTOR_ID,
            correlation_id=correlation_id,
        )
        return _response(result)
    except ValueError as exc:
        _raise(exc)
