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

    async def get(self, workspace_id, lesson_id):
        if workspace_id == self.lesson.workspace_id and lesson_id == self.lesson.id:
            return self.lesson
        return None


class TagRepo:
    def __init__(self) -> None:
        self.by_norm = {}
        self.assignments = set()
        self.created = []

    async def get_by_normalized_name(self, workspace_id, normalized_name):
        del workspace_id
        return self.by_norm.get(normalized_name)

    async def add(self, tag):
        self.by_norm[tag.normalized_name] = tag
        self.created.append(tag)

    async def list_for_lesson(self, lesson_id):
        del lesson_id
        return tuple(tag for tag in self.by_norm.values() if tag.id in self.assignments)

    async def assign(self, **kwargs):
        self.assignments.add(kwargs["tag_id"])

    async def unassign(self, **kwargs):
        self.assignments.discard(kwargs["tag_id"])


class Uow:
    def __init__(self, lesson: Lesson) -> None:
        self.lessons = LessonRepo(lesson)
        self.lesson_tags = TagRepo()
        self.flushed = False

    async def flush(self):
        self.flushed = True


@pytest.mark.asyncio
async def test_replace_tags_normalizes_and_does_not_create_version() -> None:
    actor_id = uuid4()
    lesson = Lesson(
        id=uuid4(),
        workspace_id=uuid4(),
        title="Lesson",
        current_version_id=uuid4(),
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
    ).replace_tags(
        workspace_id=lesson.workspace_id,
        lesson_id=lesson.id,
        tags=("  Risk  ", "risk", "Process"),
        actor_id=actor_id,
    )

    assert [tag.normalized_name for tag in result] == ["process", "risk"]
    assert len(uow.lesson_tags.created) == 2
    assert len(uow.lesson_tags.assignments) == 2
    assert uow.flushed
    assert not hasattr(uow, "lesson_versions")
