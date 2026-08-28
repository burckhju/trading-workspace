from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.features.model.domain.enums import HypothesisStatus
from app.features.model.domain.models import Hypothesis
from app.features.model.persistence.models import HypothesisRecord
from app.features.model.service.lesson_hypothesis_handoff import LessonHypothesisHandoffService


class ScalarResult:
    def __init__(self, values):
        self._values = values

    def __iter__(self):
        return iter(self._values)


class Session:
    def __init__(self, *, lesson_exists=True, hypotheses=()) -> None:
        self.lesson_exists = lesson_exists
        self.hypotheses = hypotheses

    async def scalar(self, statement):
        del statement
        return uuid4() if self.lesson_exists else None

    async def scalars(self, statement):
        del statement
        return ScalarResult(self.hypotheses)


class Governance:
    def __init__(self) -> None:
        self.calls = []

    async def create_hypothesis(self, **kwargs):
        self.calls.append(kwargs)
        return Hypothesis(
            id=uuid4(),
            workspace_id=kwargs["workspace_id"],
            title=kwargs["title"],
            statement=kwargs["statement"],
            status=HypothesisStatus.OPEN,
            source_lesson_version_id=kwargs["source_lesson_version_id"],
            created_at=datetime.now(UTC),
            created_by=kwargs["actor"],
        )


@pytest.mark.asyncio
async def test_create_delegates_to_ft013_with_exact_lesson_version_provenance() -> None:
    session = Session()
    service = LessonHypothesisHandoffService(session)  # type: ignore[arg-type]
    governance = Governance()
    service._governance = governance  # type: ignore[assignment]
    workspace_id = uuid4()
    lesson_version_id = uuid4()
    actor = uuid4()

    result = await service.create_from_lesson_version(
        workspace_id=workspace_id,
        lesson_version_id=lesson_version_id,
        title="Exit discipline",
        statement="Late exits reduce expectancy.",
        actor=actor,
    )

    assert result.source_lesson_version_id == lesson_version_id
    assert governance.calls == [
        {
            "workspace_id": workspace_id,
            "title": "Exit discipline",
            "statement": "Late exits reduce expectancy.",
            "evidence_ids": (),
            "source_lesson_version_id": lesson_version_id,
            "actor": actor,
        }
    ]


@pytest.mark.asyncio
async def test_missing_workspace_scoped_lesson_version_is_rejected() -> None:
    service = LessonHypothesisHandoffService(Session(lesson_exists=False))  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="source lesson version not found"):
        await service.list_for_lesson_version(
            workspace_id=uuid4(),
            lesson_version_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_readback_returns_existing_hypotheses() -> None:
    record = HypothesisRecord(
        id=uuid4(),
        workspace_id=uuid4(),
        title="Exit discipline",
        statement="Late exits reduce expectancy.",
        status=HypothesisStatus.OPEN.value,
        source_lesson_version_id=uuid4(),
        created_at=datetime.now(UTC),
        created_by=uuid4(),
    )
    service = LessonHypothesisHandoffService(Session(hypotheses=(record,)))  # type: ignore[arg-type]

    result = await service.list_for_lesson_version(
        workspace_id=record.workspace_id,
        lesson_version_id=record.source_lesson_version_id,
    )

    assert result == [record]
