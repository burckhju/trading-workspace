"""Read adapter for Lessons that reference one LearningEvidence."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.learning.domain import LessonState
from app.features.learning.persistence.models import (
    LessonEvidenceLinkModel,
    LessonModel,
    LessonVersionModel,
)


@dataclass(frozen=True, slots=True)
class LessonEvidenceReference:
    lesson_id: UUID
    current_version_id: UUID
    current_state: LessonState
    title: str


class SqlAlchemyLessonEvidenceReadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_evidence(
        self,
        *,
        workspace_id: UUID,
        learning_evidence_id: UUID,
    ) -> tuple[LessonEvidenceReference, ...]:
        rows = (
            await self._session.execute(
                select(
                    LessonModel.id,
                    LessonModel.current_version_id,
                    LessonModel.current_state,
                    LessonModel.title,
                )
                .join(LessonVersionModel, LessonVersionModel.lesson_id == LessonModel.id)
                .join(
                    LessonEvidenceLinkModel,
                    LessonEvidenceLinkModel.lesson_version_id == LessonVersionModel.id,
                )
                .where(
                    LessonModel.workspace_id == workspace_id,
                    LessonEvidenceLinkModel.learning_evidence_id == learning_evidence_id,
                )
                .distinct()
                .order_by(LessonModel.updated_at.desc(), LessonModel.id)
            )
        ).all()
        return tuple(
            LessonEvidenceReference(
                lesson_id=row.id,
                current_version_id=row.current_version_id,
                current_state=LessonState(row.current_state),
                title=row.title,
            )
            for row in rows
        )
