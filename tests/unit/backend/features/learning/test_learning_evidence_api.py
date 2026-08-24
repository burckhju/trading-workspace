from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from test_trade_link_api import _make_app

from app.features.learning.api.dependencies import (
    get_learning_evidence_query_service,
)
from app.features.learning.domain import (
    LearningEvidence,
    LearningEvidenceType,
    TradeJournalVersionEvidence,
)
from app.features.learning.persistence.repositories import (
    LearningEvidenceProjection,
)

NOW = datetime(2026, 8, 23, tzinfo=UTC)


class FakeEvidenceQuery:
    def __init__(self, projection):
        self.projection = projection

    async def get(self, **kwargs):
        del kwargs
        return self.projection

    async def list(self, **kwargs):
        del kwargs
        return (self.projection,)


def _projection() -> LearningEvidenceProjection:
    evidence_id = uuid4()
    return LearningEvidenceProjection(
        evidence=LearningEvidence(
            id=evidence_id,
            workspace_id=uuid4(),
            evidence_type=LearningEvidenceType.TRADE_JOURNAL_VERSION,
            created_at=NOW,
        ),
        source=TradeJournalVersionEvidence(
            learning_evidence_id=evidence_id,
            trade_journal_version_id=uuid4(),
        ),
    )


def test_get_learning_evidence() -> None:
    projection = _projection()
    app = _make_app()
    app.dependency_overrides[get_learning_evidence_query_service] = lambda: FakeEvidenceQuery(
        projection
    )

    response = TestClient(app).get(f"/api/v1/learning/learning-evidence/{projection.evidence.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["evidence_id"] == str(projection.evidence.id)
    assert body["provenance_class"] == "TRADE_JOURNAL_VERSION"
    assert body["source"]["type"] == "TRADE_JOURNAL_VERSION"


def test_list_learning_evidence() -> None:
    projection = _projection()
    app = _make_app()
    app.dependency_overrides[get_learning_evidence_query_service] = lambda: FakeEvidenceQuery(
        projection
    )

    response = TestClient(app).get("/api/v1/learning/learning-evidence")

    assert response.status_code == 200
    assert len(response.json()) == 1
