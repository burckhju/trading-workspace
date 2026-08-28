"""REST readback for Lessons referencing LearningEvidence."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.features.learning.api.lesson_evidence_dependencies import (
    get_lesson_evidence_read_service,
)
from app.features.learning.application.lesson_evidence_read_service import (
    LessonEvidenceReadService,
)
from app.features.learning.domain import LessonState

router = APIRouter(prefix="/api/v1/learning", tags=["learning"])
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


class LessonEvidenceReferenceResponse(BaseModel):
    lesson_id: UUID
    current_version_id: UUID
    current_state: LessonState
    title: str


@router.get(
    "/learning-evidence/{learning_evidence_id}/lessons",
    response_model=list[LessonEvidenceReferenceResponse],
)
async def list_lessons_for_learning_evidence(
    learning_evidence_id: UUID,
    service: Annotated[
        LessonEvidenceReadService,
        Depends(get_lesson_evidence_read_service),
    ],
) -> list[LessonEvidenceReferenceResponse]:
    items = await service.list_for_evidence(
        workspace_id=WORKSPACE_ID,
        learning_evidence_id=learning_evidence_id,
    )
    return [
        LessonEvidenceReferenceResponse(
            lesson_id=item.lesson_id,
            current_version_id=item.current_version_id,
            current_state=item.current_state,
            title=item.title,
        )
        for item in items
    ]
