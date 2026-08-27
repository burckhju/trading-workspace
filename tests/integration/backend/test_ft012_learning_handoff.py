from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.features.learning.application.learning_evidence_query_service import (
    LearningEvidenceQueryService,
)
from app.features.learning.application.lesson_service import (
    LessonEvidenceInput,
    LessonService,
)
from app.features.learning.domain import (
    FT011Evidence,
    LearningEvidence,
    LearningEvidenceType,
    LessonEvidenceRelation,
    LessonState,
)
from app.features.learning.persistence.repositories import LearningEvidenceProjection

NOW = datetime(2026, 8, 27, 12, 30, tzinfo=UTC)


class Clock:
    def now(self) -> datetime:
        return NOW


class Ids:
    def new_uuid(self) -> UUID:
        return uuid4()


class EvidenceRepo:
    def __init__(self, projection: LearningEvidenceProjection) -> None:
        self.projection = projection

    async def get(self, workspace_id, evidence_id):
        if (
            workspace_id == self.projection.evidence.workspace_id
            and evidence_id == self.projection.evidence.id
        ):
            return self.projection
        return None

    async def list_for_workspace(self, workspace_id):
        if workspace_id == self.projection.evidence.workspace_id:
            return (self.projection,)
        return ()


class CaptureRepo:
    def __init__(self) -> None:
        self.values = []

    async def add(self, value):
        self.values.append(value)


class Uow:
    def __init__(self, projection: LearningEvidenceProjection) -> None:
        self.learning_evidence = EvidenceRepo(projection)
        self.lessons = CaptureRepo()
        self.lesson_versions = CaptureRepo()
        self.lesson_evidence_links = CaptureRepo()

    async def flush(self):
        return None


@pytest.mark.asyncio
async def test_finalized_ft011_evidence_is_consumed_by_current_lesson() -> None:
    workspace_id = uuid4()
    trade_id = uuid4()
    observation_id = uuid4()
    exit_review_id = uuid4()
    finalized_exit_review_version_id = uuid4()
    evidence_id = uuid4()
    actor_id = uuid4()

    projection = LearningEvidenceProjection(
        evidence=LearningEvidence(
            id=evidence_id,
            workspace_id=workspace_id,
            evidence_type=LearningEvidenceType.FT011,
            created_at=NOW,
        ),
        source=FT011Evidence(
            learning_evidence_id=evidence_id,
            trade_id=trade_id,
            post_trade_observation_id=observation_id,
            exit_review_id=exit_review_id,
            exit_review_version_id=finalized_exit_review_version_id,
        ),
    )
    uow = Uow(projection)

    evidence_query = LearningEvidenceQueryService(uow=uow)  # type: ignore[arg-type]
    loaded = await evidence_query.get(
        workspace_id=workspace_id,
        evidence_id=evidence_id,
    )
    assert loaded == projection
    assert loaded.source.exit_review_version_id == finalized_exit_review_version_id

    lesson_service = LessonService(
        uow=uow,  # type: ignore[arg-type]
        clock=Clock(),
        id_factory=Ids(),
    )
    result = await lesson_service.create(
        workspace_id=workspace_id,
        title="Exit discipline",
        main_category="PROCESS",
        content="Keep the approved exit discipline when the setup remains valid.",
        evidence=(
            LessonEvidenceInput(
                learning_evidence_id=evidence_id,
                relation=LessonEvidenceRelation.SUPPORTS,
            ),
        ),
        actor_id=actor_id,
    )

    assert result.lesson.current_state is LessonState.CURRENT
    assert result.version.version == 1
    assert result.lesson.current_version_id == result.version.id
    assert len(result.evidence_links) == 1
    assert result.evidence_links[0].learning_evidence_id == evidence_id
    assert result.evidence_links[0].relation is LessonEvidenceRelation.SUPPORTS

    later_exit_review_version_id = uuid4()
    assert later_exit_review_version_id != finalized_exit_review_version_id
    assert projection.source.exit_review_version_id == finalized_exit_review_version_id
    assert result.evidence_links[0].learning_evidence_id == evidence_id
