from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.features.learning.application.lesson_service import LessonService
from app.features.learning.domain import Lesson, LessonState

NOW = datetime(2026, 8, 23, tzinfo=UTC)


class Clock:
    def now(self) -> datetime:
        return NOW


class Ids:
    def new_uuid(self) -> UUID:
        return uuid4()


class LessonRepo:
    def __init__(self, lesson: Lesson) -> None:
        self.lesson = lesson
        self.calls: list[dict[str, object]] = []

    async def get(self, workspace_id, lesson_id):
        if workspace_id == self.lesson.workspace_id and lesson_id == self.lesson.id:
            return self.lesson
        return None

    async def update_title(self, **kwargs):
        self.calls.append(kwargs)


class Uow:
    def __init__(self, lesson: Lesson) -> None:
        self.lessons = LessonRepo(lesson)
        self.flush_count = 0

    async def flush(self) -> None:
        self.flush_count += 1


@pytest.mark.asyncio
async def test_title_update_does_not_create_new_version() -> None:
    actor_id = uuid4()
    version_id = uuid4()
    lesson = Lesson(
        id=uuid4(),
        workspace_id=uuid4(),
        title="Old title",
        current_version_id=version_id,
        current_state=LessonState.CURRENT,
        created_at=NOW,
        created_by=actor_id,
        updated_at=NOW,
        updated_by=actor_id,
    )
    uow = Uow(lesson)

    result = await LessonService(
        uow=uow,  # type: ignore[arg-type]
        clock=Clock(),
        id_factory=Ids(),
    ).update_title(
        workspace_id=lesson.workspace_id,
        lesson_id=lesson.id,
        title="New title",
        actor_id=actor_id,
    )

    assert result.title == "New title"
    assert result.current_version_id == version_id
    assert len(uow.lessons.calls) == 1
    assert uow.flush_count == 1
    assert not hasattr(uow, "lesson_versions")
