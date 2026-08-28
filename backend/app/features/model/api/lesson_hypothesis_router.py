"""Explicit FT-012 Lesson -> FT-013 Hypothesis handoff API."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.model.api.dtos import HypothesisResponse
from app.features.model.api.errors import translate_model_governance_error
from app.features.model.domain.enums import HypothesisStatus
from app.features.model.domain.models import Hypothesis
from app.features.model.persistence.models import HypothesisRecord
from app.features.model.service.lesson_hypothesis_handoff import LessonHypothesisHandoffService

router = APIRouter(prefix="/api/v1/model-governance", tags=["model-governance"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
LOCAL_ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")


class CreateLessonHypothesisRequest(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    statement: str = Field(min_length=1)


async def get_lesson_hypothesis_handoff_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AsyncIterator[LessonHypothesisHandoffService]:
    yield LessonHypothesisHandoffService(session)


def _raise(error: ValueError) -> NoReturn:
    raise translate_model_governance_error(error) from error


def _response(value: Hypothesis | HypothesisRecord) -> HypothesisResponse:
    return HypothesisResponse(
        id=value.id,
        title=value.title,
        statement=value.statement,
        status=HypothesisStatus(value.status),
        source_lesson_version_id=value.source_lesson_version_id,
        created_at=value.created_at,
        created_by=value.created_by,
    )


@router.get(
    "/lesson-versions/{lesson_version_id}/hypotheses",
    response_model=list[HypothesisResponse],
)
async def list_lesson_hypotheses(
    lesson_version_id: UUID,
    service: Annotated[
        LessonHypothesisHandoffService,
        Depends(get_lesson_hypothesis_handoff_service),
    ],
) -> list[HypothesisResponse]:
    try:
        values = await service.list_for_lesson_version(
            workspace_id=WORKSPACE_ID,
            lesson_version_id=lesson_version_id,
        )
        return [_response(value) for value in values]
    except ValueError as exc:
        _raise(exc)


@router.post(
    "/lesson-versions/{lesson_version_id}/hypotheses",
    response_model=HypothesisResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_lesson_hypothesis(
    lesson_version_id: UUID,
    request: CreateLessonHypothesisRequest,
    service: Annotated[
        LessonHypothesisHandoffService,
        Depends(get_lesson_hypothesis_handoff_service),
    ],
    actor_id: Annotated[UUID | None, Header(alias="X-Actor-ID")] = None,
) -> HypothesisResponse:
    try:
        value = await service.create_from_lesson_version(
            workspace_id=WORKSPACE_ID,
            lesson_version_id=lesson_version_id,
            title=request.title,
            statement=request.statement,
            actor=actor_id or LOCAL_ACTOR_ID,
        )
        return _response(value)
    except ValueError as exc:
        _raise(exc)
