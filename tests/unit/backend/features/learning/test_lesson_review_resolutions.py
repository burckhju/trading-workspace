from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.features.learning.application.lesson_review_service import (
    LessonReviewService,
)
from app.features.learning.application.lesson_service import LessonEvidenceInput
from app.features.learning.domain import (
    Lesson,
    LessonEvidenceRelation,
    LessonReviewResolution,
    LessonReviewSignal,
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


class EvidenceRepo:
    async def get(self, workspace_id, evidence_id):
        del workspace_id, evidence_id
        return object()


class LessonRepo:
    def __init__(self, lesson):
        self.lesson = lesson
        self.advanced = False
        self.transitioned = False

    async def lock(self, workspace_id, lesson_id):
        return workspace_id == self.lesson.workspace_id and lesson_id == self.lesson.id

    async def get(self, workspace_id, lesson_id):
        if await self.lock(workspace_id, lesson_id):
            return self.lesson
        return None

    async def advance_current(self, **kwargs):
        self.advanced = True
        return True

    async def transition_state(self, **kwargs):
        self.transitioned = True
        return True


class SignalRepo:
    def __init__(self, signal):
        self.signal = signal
        self.resulting_version_id = None

    async def get(self, signal_id):
        return self.signal if signal_id == self.signal.id else None

    async def resolve(self, **kwargs):
        self.resulting_version_id = kwargs["resulting_lesson_version_id"]
        return True


class VersionRepo:
    def __init__(self):
        self.added = []

    async def next_version_number(self, workspace_id, lesson_id):
        del workspace_id, lesson_id
        return 2

    async def add(self, version):
        self.added.append(version)


class LinkRepo:
    def __init__(self):
        self.snapshot = ()

    async def add_snapshot(self, version_id, links):
        assert all(link.lesson_version_id == version_id for link in links)
        self.snapshot = tuple(links)


class TransitionRepo:
    def __init__(self):
        self.items = []

    async def add(self, transition):
        self.items.append(transition)


class Uow:
    def __init__(self, lesson, signal):
        self.lessons = LessonRepo(lesson)
        self.lesson_review_signals = SignalRepo(signal)
        self.lesson_versions = VersionRepo()
        self.lesson_evidence_links = LinkRepo()
        self.lesson_state_transitions = TransitionRepo()
        self.learning_evidence = EvidenceRepo()
        self.flushed = False

    async def flush(self):
        self.flushed = True


def _setup():
    actor = uuid4()
    version_id = uuid4()
    lesson = Lesson(
        id=uuid4(),
        workspace_id=uuid4(),
        title="Lesson",
        current_version_id=version_id,
        current_state=LessonState.REVIEW_RECOMMENDED,
        created_at=NOW,
        created_by=actor,
        updated_at=NOW,
        updated_by=actor,
    )
    signal = LessonReviewSignal(
        id=uuid4(),
        lesson_id=lesson.id,
        lesson_version_id=version_id,
        status=LessonReviewSignalStatus.OPEN,
        raised_at=NOW,
        opened_by=actor,
    )
    return actor, lesson, signal


@pytest.mark.asyncio
async def test_resolve_with_new_version_is_atomic_projection() -> None:
    actor, lesson, signal = _setup()
    uow = Uow(lesson, signal)

    result = await LessonReviewService(
        uow=uow,  # type: ignore[arg-type]
        clock=Clock(),
        id_factory=Ids(),
    ).resolve_with_new_version(
        workspace_id=lesson.workspace_id,
        lesson_id=lesson.id,
        signal_id=signal.id,
        main_category="RISK",
        content="v2",
        evidence=(
            LessonEvidenceInput(
                learning_evidence_id=uuid4(),
                relation=LessonEvidenceRelation.SUPPORTS,
            ),
        ),
        actor_id=actor,
    )

    assert result.signal.resolution is LessonReviewResolution.NEW_VERSION_CREATED
    assert result.signal.resulting_lesson_version_id is not None
    assert result.version.id == result.signal.resulting_lesson_version_id
    assert len(uow.lesson_versions.added) == 1
    assert len(uow.lesson_evidence_links.snapshot) == 1
    assert uow.lessons.advanced
    assert len(uow.lesson_state_transitions.items) == 1
    assert uow.flushed


@pytest.mark.asyncio
async def test_resolve_retired_transitions_and_resolves() -> None:
    actor, lesson, signal = _setup()
    uow = Uow(lesson, signal)

    result = await LessonReviewService(
        uow=uow,  # type: ignore[arg-type]
        clock=Clock(),
        id_factory=Ids(),
    ).resolve_retired(
        workspace_id=lesson.workspace_id,
        lesson_id=lesson.id,
        signal_id=signal.id,
        actor_id=actor,
    )

    assert result.resolution is LessonReviewResolution.LESSON_RETIRED
    assert uow.lessons.transitioned
    assert len(uow.lesson_state_transitions.items) == 1
    assert uow.lesson_review_signals.resulting_version_id is None
    assert uow.flushed
