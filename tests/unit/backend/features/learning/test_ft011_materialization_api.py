from __future__ import annotations

from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from test_trade_link_api import _make_app

from app.features.learning.api.materialization_dependencies import (
    get_ft011_materialization_service,
)
from app.features.learning.application.ft011_materialization_service import (
    Ft011MaterializationError,
    Ft011MaterializationErrorCode,
    MaterializeFt011LearningEvidenceResult,
)


class FakeMaterializationService:
    def __init__(self, *, error: Ft011MaterializationError | None = None) -> None:
        self.error = error
        self.calls: list[dict[str, object]] = []
        self.evidence_id = uuid4()
        self.version_id = uuid4()

    async def execute(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return MaterializeFt011LearningEvidenceResult(
            learning_evidence_id=self.evidence_id,
            exit_review_version_id=self.version_id,
            created=True,
            replayed=False,
        )


def test_materialize_ft011_learning_evidence_requires_idempotency_key() -> None:
    app = _make_app()
    app.dependency_overrides[get_ft011_materialization_service] = FakeMaterializationService
    client = TestClient(app)

    response = client.post(f"/api/v1/learning/trades/{uuid4()}/ft011-evidence/materialize")

    assert response.status_code == 422


def test_materialize_ft011_learning_evidence_invokes_application_command() -> None:
    service = FakeMaterializationService()
    app = _make_app()
    app.dependency_overrides[get_ft011_materialization_service] = lambda: service
    client = TestClient(app)
    trade_id = uuid4()

    response = client.post(
        f"/api/v1/learning/trades/{trade_id}/ft011-evidence/materialize",
        headers={"Idempotency-Key": "materialize-1"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "learning_evidence_id": str(service.evidence_id),
        "exit_review_version_id": str(service.version_id),
        "created": True,
        "replayed": False,
    }
    assert len(service.calls) == 1
    assert service.calls[0]["trade_id"] == trade_id
    assert service.calls[0]["idempotency_key"] == "materialize-1"
    assert isinstance(service.calls[0]["workspace_id"], UUID)


def test_materialize_ft011_learning_evidence_translates_conflict() -> None:
    service = FakeMaterializationService(
        error=Ft011MaterializationError(
            Ft011MaterializationErrorCode.SOURCE_NOT_READY,
            "FT-011 source is not ready for FT-012: EXIT_REVIEW_STALE",
            source_reason="EXIT_REVIEW_STALE",
        )
    )
    app = _make_app()
    app.dependency_overrides[get_ft011_materialization_service] = lambda: service
    client = TestClient(app)

    response = client.post(
        f"/api/v1/learning/trades/{uuid4()}/ft011-evidence/materialize",
        headers={"Idempotency-Key": "materialize-2"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "SOURCE_NOT_READY"
