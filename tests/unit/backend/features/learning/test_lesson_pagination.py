from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.features.learning.application.lesson_query_service import (
    LessonPageError,
    LessonPageErrorCode,
    LessonQueryService,
)
from app.features.learning.domain import Lesson, LessonState, LessonVersion

NOW = datetime(2026, 8, 23, tzinfo=UTC)


class LessonRepo:
    def __init__(self, lessons):
        self._lessons = lessons

    async def list_for_workspace(self, workspace_id):
        del workspace_id
        return self._lessons


class VersionRepo:
    async def get(self, version_id):
        return LessonVersion(
            id=version_id,
            lesson_id=uuid4(),
            version=1,
            main_category="PROCESS",
            content="content",
            created_at=NOW,
            created_by=uuid4(),
        )


class EvidenceLinks:
    async def list_for_version(self, version_id):
        del version_id
        return ()


class Uow:
    def __init__(self, lessons):
        self.lessons = LessonRepo(lessons)
        self.lesson_versions = VersionRepo()
        self.lesson_evidence_links = EvidenceLinks()


def _lesson(*, updated_at):
    return Lesson(
        id=uuid4(),
        workspace_id=uuid4(),
        title="Lesson",
        current_version_id=uuid4(),
        current_state=LessonState.CURRENT,
        created_at=updated_at - timedelta(minutes=10),
        created_by=uuid4(),
        updated_at=updated_at,
        updated_by=uuid4(),
    )


@pytest.mark.asyncio
async def test_lesson_page_cursor_round_trip() -> None:
    lessons = (
        _lesson(updated_at=NOW),
        _lesson(updated_at=NOW - timedelta(minutes=1)),
        _lesson(updated_at=NOW - timedelta(minutes=2)),
    )
    query = LessonQueryService(uow=Uow(lessons))  # type: ignore[arg-type]

    first = await query.page(workspace_id=uuid4(), limit=2)
    assert len(first.items) == 2
    assert first.next_cursor is not None

    second = await query.page(
        workspace_id=uuid4(),
        limit=2,
        cursor=first.next_cursor,
    )
    assert len(second.items) == 1
    assert second.next_cursor is None


@pytest.mark.asyncio
async def test_lesson_page_rejects_invalid_limit() -> None:
    query = LessonQueryService(uow=Uow(()))  # type: ignore[arg-type]

    with pytest.raises(LessonPageError) as exc:
        await query.page(workspace_id=uuid4(), limit=0)

    assert exc.value.code is LessonPageErrorCode.INVALID_PAGE_REQUEST


@pytest.mark.asyncio
async def test_lesson_page_rejects_invalid_cursor() -> None:
    query = LessonQueryService(uow=Uow(()))  # type: ignore[arg-type]

    with pytest.raises(LessonPageError) as exc:
        await query.page(
            workspace_id=uuid4(),
            cursor="not-a-valid-cursor",
        )

    assert exc.value.code is LessonPageErrorCode.INVALID_CURSOR
