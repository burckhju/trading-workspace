"""Registered application API tests; require the complete repository test environment."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_ft011_materialization_api import FakeMaterializationService
from test_trade_link_api import _make_app

from app.features.learning.api.materialization_dependencies import get_ft011_materialization_service
from app.features.learning.application.ft011_materialization_service import (
    Ft011MaterializationError,
    Ft011MaterializationErrorCode,
)


def test_api_forwards_the_explicit_review_version() -> None:
    service = FakeMaterializationService()
    app = _make_app()
    app.dependency_overrides[get_ft011_materialization_service] = lambda: service
    trade_id = uuid4()
    version_id = service.version_id
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/learning/trades/{trade_id}/ft011-evidence/materialize",
            headers={"Idempotency-Key": "confirmed-version"},
            json={"expected_exit_review_version_id": str(version_id)},
        )
    assert response.status_code == 200
    assert len(service.calls) == 1
    assert service.calls[0]["expected_exit_review_version_id"] == version_id
    assert service.calls[0]["trade_id"] == trade_id
    assert response.json()["exit_review_version_id"] == str(version_id)


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"expected_exit_review_version_id": None},
        {"expected_exit_review_version_id": "not-a-uuid"},
        {"expectedReviewVersionId": str(uuid4())},
        {"expected_exit_review_version_id": str(uuid4()), "unknown": True},
    ],
)
def test_malformed_explicit_confirmation_never_falls_back_to_latest(
    body: dict[str, object],
) -> None:
    service = FakeMaterializationService()
    app = _make_app()
    app.dependency_overrides[get_ft011_materialization_service] = lambda: service
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/learning/trades/{uuid4()}/ft011-evidence/materialize",
            headers={"Idempotency-Key": "malformed-confirmation"},
            json=body,
        )
    assert response.status_code == 422
    assert service.calls == []


def test_pin_conflict_is_a_structured_409() -> None:
    service = FakeMaterializationService(
        error=Ft011MaterializationError(
            Ft011MaterializationErrorCode.SOURCE_VERSION_MISMATCH,
            "review version changed",
        )
    )
    app = _make_app()
    app.dependency_overrides[get_ft011_materialization_service] = lambda: service
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/learning/trades/{uuid4()}/ft011-evidence/materialize",
            headers={"Idempotency-Key": "pinned-conflict"},
            json={"expected_exit_review_version_id": str(uuid4())},
        )
    assert response.status_code == 409
    assert response.json()["code"] == "SOURCE_VERSION_MISMATCH"
