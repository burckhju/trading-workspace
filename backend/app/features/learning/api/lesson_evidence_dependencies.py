"""Dependencies for Lesson readback by LearningEvidence."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.dependencies import get_database_session
from app.features.learning.application.lesson_evidence_read_service import (
    LessonEvidenceReadService,
)
from app.features.learning.persistence.lesson_evidence_read_repository import (
    SqlAlchemyLessonEvidenceReadRepository,
)


def get_lesson_evidence_read_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> LessonEvidenceReadService:
    return LessonEvidenceReadService(
        repository=SqlAlchemyLessonEvidenceReadRepository(session),
    )
