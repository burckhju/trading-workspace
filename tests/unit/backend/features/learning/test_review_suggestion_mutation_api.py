from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from test_trade_link_api import _make_app

from app.features.learning.api.dependencies import (
    get_lesson_review_service,
    get_lesson_suggestion_service,
)
from app.features.learning.domain import (
    LessonEvidenceRelation,
    LessonReviewSignalStatus,
    LessonState,
    LessonSuggestionStatus,
)

NOW = datetime(2026, 8, 23, tzinfo=UTC)


class ReviewService:
    def __init__(self) -> None:
        self.signal = SimpleNamespace(
            id=uuid4(),
            lesson_id=uuid4(),
            lesson_version_id=uuid4(),
            status=LessonReviewSignalStatus.OPEN,
            raised_at=NOW,
            opened_by=uuid4(),
            resolution=None,
            resolved_at=None,
            resolved_by=None,
            resulting_lesson_version_id=None,
        )

    async def open_signal(self, **kwargs):
        self.signal.lesson_id = kwargs["lesson_id"]
        return SimpleNamespace(signal=self.signal)


class SuggestionService:
    async def reject(self, **kwargs):
        return SimpleNamespace(
            id=kwargs["suggestion_id"],
            workspace_id=uuid4(),
            status=LessonSuggestionStatus.REJECTED,
            proposed_title="Title",
            proposed_main_category="PROCESS",
            proposed_content="Content",
            created_at=NOW,
            created_by=None,
            decided_at=NOW,
            decided_by=kwargs["actor_id"],
            resulting_lesson_id=None,
        )

    async def confirm(self, **kwargs):
        lesson_id = uuid4()
        version_id = uuid4()
        return SimpleNamespace(
            suggestion=SimpleNamespace(
                id=kwargs["suggestion_id"],
                workspace_id=uuid4(),
                status=LessonSuggestionStatus.CONFIRMED,
                proposed_title="Title",
                proposed_main_category="PROCESS",
                proposed_content="Content",
                created_at=NOW,
                created_by=None,
                decided_at=NOW,
                decided_by=kwargs["actor_id"],
                resulting_lesson_id=lesson_id,
            ),
            lesson=SimpleNamespace(
                id=lesson_id,
                title=kwargs["title"] or "Title",
                current_state=LessonState.CURRENT,
            ),
            version=SimpleNamespace(
                id=version_id,
                version=1,
                main_category=kwargs["main_category"] or "PROCESS",
                content=kwargs["content"] or "Content",
            ),
            evidence_links=(
                SimpleNamespace(
                    id=uuid4(),
                    learning_evidence_id=uuid4(),
                    relation=LessonEvidenceRelation.SUPPORTS,
                ),
            ),
        )


def test_open_review_signal_api() -> None:
    review = ReviewService()
    app = _make_app()
    app.dependency_overrides[get_lesson_review_service] = lambda: review

    lesson_id = uuid4()
    response = TestClient(app).post(
        f"/api/v1/learning/lessons/{lesson_id}/review-signals",
        json={"contradiction_link_ids": [str(uuid4())]},
        headers={"X-Actor-ID": str(uuid4())},
    )

    assert response.status_code == 201
    assert response.json()["lesson_id"] == str(lesson_id)
    assert response.json()["status"] == "OPEN"


def test_reject_suggestion_api() -> None:
    service = SuggestionService()
    app = _make_app()
    app.dependency_overrides[get_lesson_suggestion_service] = lambda: service

    suggestion_id = uuid4()
    response = TestClient(app).post(
        f"/api/v1/learning/lesson-suggestions/{suggestion_id}/reject",
        headers={"X-Actor-ID": str(uuid4())},
    )

    assert response.status_code == 200
    assert response.json()["suggestion_id"] == str(suggestion_id)
    assert response.json()["status"] == "REJECTED"


def test_confirm_suggestion_api() -> None:
    service = SuggestionService()
    app = _make_app()
    app.dependency_overrides[get_lesson_suggestion_service] = lambda: service

    suggestion_id = uuid4()
    response = TestClient(app).post(
        f"/api/v1/learning/lesson-suggestions/{suggestion_id}/confirm",
        json={
            "evidence_links": [
                {
                    "learning_evidence_id": str(uuid4()),
                    "relation": "SUPPORTS",
                }
            ]
        },
        headers={"X-Actor-ID": str(uuid4())},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["suggestion"]["status"] == "CONFIRMED"
    assert body["version"] == 1
    assert body["current_state"] == "CURRENT"
