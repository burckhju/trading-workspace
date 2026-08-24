from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.features.learning.application.lesson_service import (
    LessonErrorCode,
    LessonEvidenceInput,
    LessonService,
    LessonServiceError,
)
from app.features.learning.domain import LessonEvidenceRelation

NOW = datetime(2026, 8, 23, tzinfo=UTC)


class Clock:
    def now(self) -> datetime:
        return NOW


class Ids:
    def new_uuid(self) -> UUID:
        return uuid4()


class EvidenceRepo:
    async def get(self, workspace_id, evidence_id):
        del workspace_id, evidence_id
        return object()


class DummyRepo:
    async def add(self, value):
        del value


class Uow:
    def __init__(self):
        self.learning_evidence = EvidenceRepo()
        self.lessons = DummyRepo()
        self.lesson_versions = DummyRepo()
        self.lesson_evidence_links = DummyRepo()

    async def flush(self):
        return None


@pytest.mark.asyncio
async def test_create_requires_evidence() -> None:
    service = LessonService(uow=Uow(), clock=Clock(), id_factory=Ids())  # type: ignore[arg-type]

    with pytest.raises(LessonServiceError) as exc:
        await service.create(
            workspace_id=uuid4(),
            title="Title",
            main_category="PROCESS",
            content="Content",
            evidence=(),
            actor_id=uuid4(),
        )

    assert exc.value.code is LessonErrorCode.LESSON_EVIDENCE_REQUIRED


@pytest.mark.asyncio
async def test_create_requires_supporting_evidence() -> None:
    service = LessonService(uow=Uow(), clock=Clock(), id_factory=Ids())  # type: ignore[arg-type]

    with pytest.raises(LessonServiceError) as exc:
        await service.create(
            workspace_id=uuid4(),
            title="Title",
            main_category="PROCESS",
            content="Content",
            evidence=(
                LessonEvidenceInput(
                    learning_evidence_id=uuid4(),
                    relation=LessonEvidenceRelation.CONTEXTUAL,
                ),
            ),
            actor_id=uuid4(),
        )

    assert exc.value.code is LessonErrorCode.LESSON_SUPPORTING_EVIDENCE_REQUIRED
