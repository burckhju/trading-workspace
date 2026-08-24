from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.features.learning.application.lesson_service import (
    LessonErrorCode,
    LessonService,
    LessonServiceError,
)
from app.features.learning.domain import (
    Lesson,
    LessonState,
)

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
        self.transitioned = False

    async def lock(self, workspace_id, lesson_id):
        return workspace_id == self.lesson.workspace_id and lesson_id == self.lesson.id

    async def get(self, workspace_id, lesson_id):
        if await self.lock(workspace_id, lesson_id):
            return self.lesson
        return None

    async def transition_state(self, **kwargs):
        self.transitioned = True
        return kwargs["expected_state"] is self.lesson.current_state


class Transitions:
    def __init__(self) -> None:
        self.added = []

    async def add(self, transition):
        self.added.append(transition)


class Uow:
    def __init__(self, lesson: Lesson) -> None:
        self.lessons = LessonRepo(lesson)
        self.lesson_state_transitions = Transitions()
        self.flushed = False

    async def flush(self):
        self.flushed = True


@pytest.mark.asyncio
async def test_transition_current_to_review_recommended() -> None:
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
    ).transition_state(
        workspace_id=lesson.workspace_id,
        lesson_id=lesson.id,
        expected_state=LessonState.CURRENT,
        new_state=LessonState.REVIEW_RECOMMENDED,
        reason="REVIEW_REQUIRED",
        related_lesson_version_id=None,
        actor_id=actor_id,
    )

    assert result.lesson.current_state is LessonState.REVIEW_RECOMMENDED
    assert result.transition.from_state is LessonState.CURRENT
    assert result.transition.to_state is LessonState.REVIEW_RECOMMENDED
    assert len(uow.lesson_state_transitions.added) == 1
    assert uow.lessons.transitioned
    assert uow.flushed


@pytest.mark.asyncio
async def test_transition_retired_to_current_requires_new_version() -> None:
    actor_id = uuid4()
    lesson = Lesson(
        id=uuid4(),
        workspace_id=uuid4(),
        title="Lesson",
        current_version_id=uuid4(),
        current_state=LessonState.RETIRED,
        created_at=NOW,
        created_by=actor_id,
        updated_at=NOW,
        updated_by=actor_id,
    )

    with pytest.raises(LessonServiceError) as exc:
        await LessonService(
            uow=Uow(lesson),  # type: ignore[arg-type]
            clock=Clock(),
            id_factory=Ids(),
        ).transition_state(
            workspace_id=lesson.workspace_id,
            lesson_id=lesson.id,
            expected_state=LessonState.RETIRED,
            new_state=LessonState.CURRENT,
            reason="REACTIVATED",
            related_lesson_version_id=None,
            actor_id=actor_id,
        )

    assert exc.value.code is LessonErrorCode.LESSON_STATE_TRANSITION_INVALID
