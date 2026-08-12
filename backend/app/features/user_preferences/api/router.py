"""Actor-scoped REST API for UI preferences."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.core.identity import RequestIdentity, get_request_identity
from app.features.user_preferences.api.dependencies import get_user_preference_service
from app.features.user_preferences.api.dtos import (
    CreatePreferenceRequest,
    PreferenceResponse,
)
from app.features.user_preferences.persistence.models import UserPreferenceModel
from app.features.user_preferences.service.application import UserPreferenceService

router = APIRouter(prefix="/api/v1/user-preferences", tags=["user-preferences"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


def _response(model: UserPreferenceModel) -> PreferenceResponse:
    return PreferenceResponse(
        id=model.id,
        kind=model.kind,
        name=model.name,
        value=model.value,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


@router.get("/{kind}", response_model=list[PreferenceResponse])
async def list_preferences(
    kind: str,
    service: Annotated[UserPreferenceService, Depends(get_user_preference_service)],
    identity: Annotated[RequestIdentity, Depends(get_request_identity)],
) -> list[PreferenceResponse]:
    return [
        _response(item)
        for item in await service.list(WORKSPACE_ID, identity.actor_id, kind)
    ]


@router.post(
    "/{kind}", response_model=PreferenceResponse, status_code=status.HTTP_201_CREATED
)
async def create_preference(
    kind: str,
    request: CreatePreferenceRequest,
    service: Annotated[UserPreferenceService, Depends(get_user_preference_service)],
    identity: Annotated[RequestIdentity, Depends(get_request_identity)],
) -> PreferenceResponse:
    return _response(
        await service.create(
            WORKSPACE_ID, identity.actor_id, kind, request.name, request.value
        )
    )


@router.delete("/{kind}/{preference_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_preference(
    kind: str,
    preference_id: UUID,
    service: Annotated[UserPreferenceService, Depends(get_user_preference_service)],
    identity: Annotated[RequestIdentity, Depends(get_request_identity)],
) -> Response:
    await service.delete(WORKSPACE_ID, identity.actor_id, preference_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
