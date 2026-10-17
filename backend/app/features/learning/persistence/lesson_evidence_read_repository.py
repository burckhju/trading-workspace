"""Read adapter for Lessons that reference one LearningEvidence."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.learning.domain import LessonEvidenceRelation, LessonState
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


@dataclass(frozen=True, slots=True)
class HistoricalLessonEvidenceReference:
    link_id: UUID
    lesson_id: UUID
    lesson_title: str
    lesson_version_id: UUID
    lesson_version: int
    relation: LessonEvidenceRelation
    is_current_version: bool


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
                    # PostgreSQL requires every DISTINCT ORDER BY expression
                    # in the projection. This is not an extra API field.
                    LessonModel.updated_at,
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

    async def list_version_references_for_evidence(
        self, *, workspace_id: UUID, learning_evidence_id: UUID
    ) -> tuple[HistoricalLessonEvidenceReference, ...]:
        rows = (
            await self._session.execute(
                select(LessonModel, LessonVersionModel, LessonEvidenceLinkModel)
                .join(LessonVersionModel, LessonVersionModel.lesson_id == LessonModel.id)
                .join(
                    LessonEvidenceLinkModel,
                    LessonEvidenceLinkModel.lesson_version_id == LessonVersionModel.id,
                )
                .where(
                    LessonModel.workspace_id == workspace_id,
                    LessonEvidenceLinkModel.learning_evidence_id == learning_evidence_id,
                )
                .order_by(
                    LessonModel.id, LessonVersionModel.version.desc(), LessonEvidenceLinkModel.id
                )
            )
        ).all()
        return tuple(
            HistoricalLessonEvidenceReference(
                link.id,
                lesson.id,
                lesson.title,
                version.id,
                version.version,
                LessonEvidenceRelation(link.relation),
                version.id == lesson.current_version_id,
            )
            for lesson, version, link in rows
        )
