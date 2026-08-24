from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.features.learning.application.lesson_service import LessonEvidenceInput
from app.features.learning.application.lesson_suggestion_service import (
    LessonSuggestionService,
)
from app.features.learning.domain import (
    LessonEvidenceRelation,
    LessonSuggestion,
    LessonSuggestionStatus,
)

NOW = datetime(2026, 8, 23, tzinfo=UTC)


class Clock:
    def now(self):
        return NOW


class Ids:
    def new_uuid(self) -> UUID:
        return uuid4()


class Suggestions:
    def __init__(self, suggestion):
        self.suggestion = suggestion
        self.confirmed_lesson_id = None
        self.rejected = False

    async def lock(self, workspace_id, suggestion_id):
        return workspace_id == self.suggestion.workspace_id and suggestion_id == self.suggestion.id

    async def get(self, workspace_id, suggestion_id):
        if await self.lock(workspace_id, suggestion_id):
            return self.suggestion
        return None

    async def reject(self, **kwargs):
        self.rejected = True
        return True

    async def confirm(self, **kwargs):
        self.confirmed_lesson_id = kwargs["resulting_lesson_id"]
        return True


class Evidence:
    async def get(self, workspace_id, evidence_id):
        del workspace_id, evidence_id
        return object()


class Collect:
    def __init__(self):
        self.items = []

    async def add(self, item):
        self.items.append(item)


class Links:
    def __init__(self):
        self.snapshot = ()

    async def add_snapshot(self, version_id, links):
        self.snapshot = tuple(links)
        assert all(link.lesson_version_id == version_id for link in links)


class Uow:
    def __init__(self, suggestion):
        self.lesson_suggestions = Suggestions(suggestion)
        self.learning_evidence = Evidence()
        self.lessons = Collect()
        self.lesson_versions = Collect()
        self.lesson_evidence_links = Links()
        self.lesson_state_transitions = Collect()
        self.flushed = False

    async def flush(self):
        self.flushed = True


def _suggestion():
    return LessonSuggestion(
        id=uuid4(),
        workspace_id=uuid4(),
        status=LessonSuggestionStatus.SUGGESTED,
        proposed_title="Suggested lesson",
        proposed_main_category="PROCESS",
        proposed_content="Do the thing",
        created_at=NOW,
        created_by=None,
    )


@pytest.mark.asyncio
async def test_reject_is_one_way_decision() -> None:
    suggestion = _suggestion()
    uow = Uow(suggestion)

    result = await LessonSuggestionService(
        uow=uow,  # type: ignore[arg-type]
        clock=Clock(),
        id_factory=Ids(),
    ).reject(
        workspace_id=suggestion.workspace_id,
        suggestion_id=suggestion.id,
        actor_id=uuid4(),
    )

    assert result.status is LessonSuggestionStatus.REJECTED
    assert uow.lesson_suggestions.rejected
    assert uow.flushed


@pytest.mark.asyncio
async def test_confirm_creates_lesson_v1_snapshot_and_initial_transition() -> None:
    suggestion = _suggestion()
    uow = Uow(suggestion)

    result = await LessonSuggestionService(
        uow=uow,  # type: ignore[arg-type]
        clock=Clock(),
        id_factory=Ids(),
    ).confirm(
        workspace_id=suggestion.workspace_id,
        suggestion_id=suggestion.id,
        evidence=(
            LessonEvidenceInput(
                learning_evidence_id=uuid4(),
                relation=LessonEvidenceRelation.SUPPORTS,
            ),
        ),
        actor_id=uuid4(),
    )

    assert result.suggestion.status is LessonSuggestionStatus.CONFIRMED
    assert result.suggestion.resulting_lesson_id == result.lesson.id
    assert result.version.version == 1
    assert len(result.evidence_links) == 1
    assert len(uow.lessons.items) == 1
    assert len(uow.lesson_versions.items) == 1
    assert len(uow.lesson_state_transitions.items) == 1
    assert uow.lesson_suggestions.confirmed_lesson_id == result.lesson.id
    assert uow.flushed
