from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from test_trade_link_api import _make_app

from app.features.learning.api.dependencies import get_lesson_query_service
from app.features.learning.application.lesson_query_service import (
    LessonProjection,
    LessonVersionProjection,
)
from app.features.learning.domain import (
    Lesson,
    LessonEvidenceLink,
    LessonEvidenceRelation,
    LessonState,
    LessonVersion,
)

NOW = datetime(2026, 8, 23, tzinfo=UTC)


def _data():
    lesson_id = uuid4()
    workspace_id = uuid4()
    actor_id = uuid4()
    v1_id = uuid4()
    v2_id = uuid4()
    evidence_id = uuid4()

    lesson = Lesson(
        id=lesson_id,
        workspace_id=workspace_id,
        title="Lesson",
        current_version_id=v2_id,
        current_state=LessonState.CURRENT,
        created_at=NOW,
        created_by=actor_id,
        updated_at=NOW,
        updated_by=actor_id,
    )
    v1 = LessonVersion(
        id=v1_id,
        lesson_id=lesson_id,
        version=1,
        main_category="PROCESS",
        content="v1",
        created_at=NOW,
        created_by=actor_id,
    )
    v2 = LessonVersion(
        id=v2_id,
        lesson_id=lesson_id,
        version=2,
        main_category="PROCESS",
        content="v2",
        created_at=NOW,
        created_by=actor_id,
        supersedes_version_id=v1_id,
    )
    link = LessonEvidenceLink(
        id=uuid4(),
        lesson_version_id=v2_id,
        learning_evidence_id=evidence_id,
        relation=LessonEvidenceRelation.SUPPORTS,
        created_at=NOW,
        created_by=actor_id,
    )
    return lesson, v1, v2, link


class FakeQuery:
    def __init__(self):
        self.lesson, self.v1, self.v2, self.link = _data()

    async def history(self, **kwargs):
        del kwargs
        return (
            LessonVersionProjection(version=self.v1, evidence_links=()),
            LessonVersionProjection(
                version=self.v2,
                evidence_links=(self.link,),
            ),
        )

    async def get(self, **kwargs):
        del kwargs
        return LessonProjection(
            lesson=self.lesson,
            version=self.v2,
            evidence_links=(self.link,),
        )


def test_lesson_history_returns_ordered_versions() -> None:
    fake = FakeQuery()
    app = _make_app()
    app.dependency_overrides[get_lesson_query_service] = lambda: fake

    response = TestClient(app).get(f"/api/v1/learning/lessons/{fake.lesson.id}/history")

    assert response.status_code == 200
    body = response.json()
    assert [item["version"] for item in body["versions"]] == [1, 2]
    assert body["versions"][1]["evidence"][0]["relation"] == "SUPPORTS"


def test_lesson_evidence_returns_current_snapshot() -> None:
    fake = FakeQuery()
    app = _make_app()
    app.dependency_overrides[get_lesson_query_service] = lambda: fake

    response = TestClient(app).get(f"/api/v1/learning/lessons/{fake.lesson.id}/evidence")

    assert response.status_code == 200
    body = response.json()
    assert body["current_version_id"] == str(fake.v2.id)
    assert body["evidence"][0]["learning_evidence_id"] == str(fake.link.learning_evidence_id)
