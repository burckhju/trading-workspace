from __future__ import annotations

from uuid import uuid4

import pytest

from app.features.learning.application.lesson_evidence_read_service import LessonEvidenceReadService
from app.features.learning.domain import LessonState
from app.features.learning.persistence.lesson_evidence_read_repository import LessonEvidenceReference


class Repository:
    def __init__(self) -> None:
        self.workspace_id = uuid4()
        self.evidence_id = uuid4()
        self.lesson_id = uuid4()
        self.version_id = uuid4()

    async def list_for_evidence(self, *, workspace_id, learning_evidence_id):
        assert workspace_id == self.workspace_id
        assert learning_evidence_id == self.evidence_id
        return (
            LessonEvidenceReference(
                lesson_id=self.lesson_id,
                current_version_id=self.version_id,
                current_state=LessonState.CURRENT,
                title="Exit discipline",
            ),
        )


@pytest.mark.asyncio
async def test_lists_lesson_references_for_evidence() -> None:
    repository = Repository()
    service = LessonEvidenceReadService(repository=repository)

    result = await service.list_for_evidence(
        workspace_id=repository.workspace_id,
        learning_evidence_id=repository.evidence_id,
    )

    assert len(result) == 1
    assert result[0].lesson_id == repository.lesson_id
    assert result[0].current_version_id == repository.version_id
    assert result[0].current_state is LessonState.CURRENT
    assert result[0].title == "Exit discipline"
