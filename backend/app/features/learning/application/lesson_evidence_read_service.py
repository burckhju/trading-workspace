"""Read service for Lesson references to LearningEvidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.features.learning.domain import LessonState
from app.features.learning.persistence.lesson_evidence_read_repository import (
    LessonEvidenceReference,
)


class LessonEvidenceReferenceReader(Protocol):
    async def list_for_evidence(
        self,
        *,
        workspace_id: UUID,
        learning_evidence_id: UUID,
    ) -> tuple[LessonEvidenceReference, ...]: ...


@dataclass(frozen=True, slots=True)
class LessonEvidenceReadItem:
    lesson_id: UUID
    current_version_id: UUID
    current_state: LessonState
    title: str


class LessonEvidenceReadService:
    def __init__(self, *, repository: LessonEvidenceReferenceReader) -> None:
        self._repository = repository

    async def list_for_evidence(
        self,
        *,
        workspace_id: UUID,
        learning_evidence_id: UUID,
    ) -> tuple[LessonEvidenceReadItem, ...]:
        references = await self._repository.list_for_evidence(
            workspace_id=workspace_id,
            learning_evidence_id=learning_evidence_id,
        )
        return tuple(
            LessonEvidenceReadItem(
                lesson_id=item.lesson_id,
                current_version_id=item.current_version_id,
                current_state=item.current_state,
                title=item.title,
            )
            for item in references
        )
