from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient
from test_trade_link_api import _make_app

from app.features.learning.api.dependencies import (
    get_review_suggestion_query_service,
)
from app.features.learning.domain import (
    LessonReviewSignalStatus,
    LessonSuggestionStatus,
)

NOW = datetime(2026, 8, 23, tzinfo=UTC)


class Query:
    def __init__(self) -> None:
        self.suggestion = SimpleNamespace(
            id=uuid4(),
            workspace_id=uuid4(),
            status=LessonSuggestionStatus.SUGGESTED,
            proposed_title="Title",
            proposed_main_category="PROCESS",
            proposed_content="Content",
            created_at=NOW,
            created_by=None,
            decided_at=None,
            decided_by=None,
            resulting_lesson_id=None,
        )

    async def list_review_signal_projections(self, **kwargs):
        return (
            SimpleNamespace(
                signal=SimpleNamespace(
                    id=uuid4(),
                    lesson_id=kwargs["lesson_id"],
                    lesson_version_id=uuid4(),
                    status=LessonReviewSignalStatus.OPEN,
                    raised_at=NOW,
                    opened_by=uuid4(),
                    resolution=None,
                    resolved_at=None,
                    resolved_by=None,
                    resulting_lesson_version_id=None,
                ),
                trigger_evidence_link_ids=(uuid4(),),
            ),
        )

    async def get_suggestion(self, **kwargs):
        if kwargs["suggestion_id"] == self.suggestion.id:
            return self.suggestion
        return None

    async def list_suggestions(self, **kwargs):
        del kwargs
        return (self.suggestion,)


def test_list_review_signals_api() -> None:
    query = Query()
    app = _make_app()
    app.dependency_overrides[get_review_suggestion_query_service] = lambda: query

    lesson_id = uuid4()
    response = TestClient(app).get(f"/api/v1/learning/lessons/{lesson_id}/review-signals")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["lesson_id"] == str(lesson_id)
    assert len(body[0]["trigger_evidence"]) == 1
    assert body[0]["opened_at"] is not None
    assert body[0]["opened_by"] is not None


def test_get_suggestion_api() -> None:
    query = Query()
    app = _make_app()
    app.dependency_overrides[get_review_suggestion_query_service] = lambda: query

    response = TestClient(app).get(f"/api/v1/learning/lesson-suggestions/{query.suggestion.id}")

    assert response.status_code == 200
    assert response.json()["status"] == "SUGGESTED"


def test_list_suggestions_api() -> None:
    query = Query()
    app = _make_app()
    app.dependency_overrides[get_review_suggestion_query_service] = lambda: query

    response = TestClient(app).get("/api/v1/learning/lesson-suggestions")

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1
