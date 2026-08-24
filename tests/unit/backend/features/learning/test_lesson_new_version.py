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
from app.features.learning.domain import (
    Lesson,
    LessonEvidenceRelation,
    LessonState,
)

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


class LessonRepo:
    def __init__(self, lesson: Lesson) -> None:
        self.lesson = lesson
        self.advanced = False

    async def lock(self, workspace_id, lesson_id):
        return workspace_id == self.lesson.workspace_id and lesson_id == self.lesson.id

    async def get(self, workspace_id, lesson_id):
        if await self.lock(workspace_id, lesson_id):
            return self.lesson
        return None

    async def advance_current(self, **kwargs):
        self.advanced = True
        return (
            kwargs["expected_current_version_id"] == self.lesson.current_version_id
            and kwargs["expected_current_state"] is self.lesson.current_state
        )


class VersionRepo:
    def __init__(self) -> None:
        self.added = []

    async def next_version_number(self, workspace_id, lesson_id):
        del workspace_id, lesson_id
        return 2

    async def add(self, version):
        self.added.append(version)


class Links:
    def __init__(self) -> None:
        self.snapshot = ()

    async def add_snapshot(self, version_id, links):
        assert all(link.lesson_version_id == version_id for link in links)
        self.snapshot = tuple(links)


class Uow:
    def __init__(self, lesson: Lesson) -> None:
        self.lessons = LessonRepo(lesson)
        self.lesson_versions = VersionRepo()
        self.lesson_evidence_links = Links()
        self.learning_evidence = EvidenceRepo()
        self.flushed = False

    async def flush(self):
        self.flushed = True


@pytest.mark.asyncio
async def test_create_new_version_advances_pointer_and_snapshots_evidence() -> None:
    actor_id = uuid4()
    old_version_id = uuid4()
    lesson = Lesson(
        id=uuid4(),
        workspace_id=uuid4(),
        title="Lesson",
        current_version_id=old_version_id,
        current_state=LessonState.CURRENT,
        created_at=NOW,
        created_by=actor_id,
        updated_at=NOW,
        updated_by=actor_id,
    )
    uow = Uow(lesson)
    evidence_id = uuid4()

    result = await LessonService(
        uow=uow,  # type: ignore[arg-type]
        clock=Clock(),
        id_factory=Ids(),
    ).create_new_version(
        workspace_id=lesson.workspace_id,
        lesson_id=lesson.id,
        main_category="RISK",
        content="v2",
        evidence=(
            LessonEvidenceInput(
                learning_evidence_id=evidence_id,
                relation=LessonEvidenceRelation.SUPPORTS,
            ),
        ),
        expected_current_version_id=old_version_id,
        expected_current_state=LessonState.CURRENT,
        actor_id=actor_id,
    )

    assert result.version.version == 2
    assert result.version.supersedes_version_id == old_version_id
    assert result.lesson.current_version_id == result.version.id
    assert len(uow.lesson_evidence_links.snapshot) == 1
    assert uow.lessons.advanced
    assert uow.flushed


@pytest.mark.asyncio
async def test_create_new_version_rejects_stale_pointer() -> None:
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
    service = LessonService(
        uow=Uow(lesson),  # type: ignore[arg-type]
        clock=Clock(),
        id_factory=Ids(),
    )

    with pytest.raises(LessonServiceError) as exc:
        await service.create_new_version(
            workspace_id=lesson.workspace_id,
            lesson_id=lesson.id,
            main_category="RISK",
            content="v2",
            evidence=(
                LessonEvidenceInput(
                    learning_evidence_id=uuid4(),
                    relation=LessonEvidenceRelation.SUPPORTS,
                ),
            ),
            expected_current_version_id=uuid4(),
            expected_current_state=LessonState.CURRENT,
            actor_id=actor_id,
        )

    assert exc.value.code is LessonErrorCode.CONCURRENT_MODIFICATION
