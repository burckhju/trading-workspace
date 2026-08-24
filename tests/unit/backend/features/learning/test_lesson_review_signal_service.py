from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.features.learning.application.lesson_review_service import (
    LessonReviewErrorCode,
    LessonReviewService,
    LessonReviewServiceError,
)
from app.features.learning.domain import (
    Lesson,
    LessonEvidenceLink,
    LessonEvidenceRelation,
    LessonReviewSignalStatus,
    LessonState,
)

NOW = datetime(2026, 8, 23, tzinfo=UTC)


class Clock:
    def now(self):
        return NOW


class Ids:
    def new_uuid(self) -> UUID:
        return uuid4()


class LessonRepo:
    def __init__(self, lesson):
        self.lesson = lesson

    async def lock(self, workspace_id, lesson_id):
        return workspace_id == self.lesson.workspace_id and lesson_id == self.lesson.id

    async def get(self, workspace_id, lesson_id):
        if await self.lock(workspace_id, lesson_id):
            return self.lesson
        return None

    async def transition_state(self, **kwargs):
        return kwargs["expected_state"] is self.lesson.current_state


class Links:
    def __init__(self, links):
        self.links = links

    async def list_for_version(self, version_id):
        return tuple(link for link in self.links if link.lesson_version_id == version_id)


class Signals:
    def __init__(self):
        self.open = None
        self.provenance = ()

    async def get_open_for_lesson(self, lesson_id):
        del lesson_id
        return self.open

    async def add_open(self, signal, trigger_links):
        self.open = signal
        self.provenance = tuple(trigger_links)


class Transitions:
    def __init__(self):
        self.items = []

    async def add(self, transition):
        self.items.append(transition)


class Uow:
    def __init__(self, lesson, links):
        self.lessons = LessonRepo(lesson)
        self.lesson_evidence_links = Links(links)
        self.lesson_review_signals = Signals()
        self.lesson_state_transitions = Transitions()
        self.flushed = False

    async def flush(self):
        self.flushed = True


@pytest.mark.asyncio
async def test_open_signal_requires_current_contradicting_evidence() -> None:
    actor = uuid4()
    version_id = uuid4()
    lesson = Lesson(
        id=uuid4(),
        workspace_id=uuid4(),
        title="Lesson",
        current_version_id=version_id,
        current_state=LessonState.CURRENT,
        created_at=NOW,
        created_by=actor,
        updated_at=NOW,
        updated_by=actor,
    )
    contradiction = LessonEvidenceLink(
        id=uuid4(),
        lesson_version_id=version_id,
        learning_evidence_id=uuid4(),
        relation=LessonEvidenceRelation.CONTRADICTS,
        created_at=NOW,
        created_by=actor,
    )
    uow = Uow(lesson, (contradiction,))

    result = await LessonReviewService(
        uow=uow,  # type: ignore[arg-type]
        clock=Clock(),
        id_factory=Ids(),
    ).open_signal(
        workspace_id=lesson.workspace_id,
        lesson_id=lesson.id,
        contradiction_link_ids=(contradiction.id,),
        actor_id=actor,
    )

    assert result.signal.status is LessonReviewSignalStatus.OPEN
    assert result.signal.lesson_version_id == version_id
    assert len(uow.lesson_review_signals.provenance) == 1
    assert len(uow.lesson_state_transitions.items) == 1
    assert uow.flushed


@pytest.mark.asyncio
async def test_open_signal_rejects_supporting_link() -> None:
    actor = uuid4()
    version_id = uuid4()
    lesson = Lesson(
        id=uuid4(),
        workspace_id=uuid4(),
        title="Lesson",
        current_version_id=version_id,
        current_state=LessonState.CURRENT,
        created_at=NOW,
        created_by=actor,
        updated_at=NOW,
        updated_by=actor,
    )
    supporting = LessonEvidenceLink(
        id=uuid4(),
        lesson_version_id=version_id,
        learning_evidence_id=uuid4(),
        relation=LessonEvidenceRelation.SUPPORTS,
        created_at=NOW,
        created_by=actor,
    )

    with pytest.raises(LessonReviewServiceError) as exc:
        await LessonReviewService(
            uow=Uow(lesson, (supporting,)),  # type: ignore[arg-type]
            clock=Clock(),
            id_factory=Ids(),
        ).open_signal(
            workspace_id=lesson.workspace_id,
            lesson_id=lesson.id,
            contradiction_link_ids=(supporting.id,),
            actor_id=actor,
        )

    assert exc.value.code is LessonReviewErrorCode.INVALID_REVIEW_TRIGGER
