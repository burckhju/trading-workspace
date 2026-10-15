"""Wire preconditions; actual transaction/DB behaviour is qualified separately."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Environment, Settings
from app.features.learning.api.lesson_review_router import get_review_commands
from app.features.learning.application.lesson_review_commands import (
    LessonReviewReceipt,
    ReviewCommandError,
)
from app.main import create_application


@pytest.fixture
def api():
    service = SimpleNamespace(
        execute=AsyncMock(
            return_value=LessonReviewReceipt(uuid4(), uuid4(), "LESSON_STATE_TRANSITION", False)
        )
    )
    app = create_application(Settings(_env_file=None, environment=Environment.TEST))
    app.dependency_overrides[get_review_commands] = lambda: service
    return TestClient(app), service


def opening():
    return dict(
        operation="OPEN_SOURCE_REVIEW",
        expected_current_version_id=str(uuid4()),
        expected_current_state="CURRENT",
        expected_open_signal_id=None,
        reviewed_evidence_ids=[str(uuid4())],
        reason="Deliberate review",
        confirmed=True,
    )


@pytest.mark.parametrize(
    "change",
    [
        {"confirmed": False},
        {"operation": "AUTO_REVALIDATE"},
        {"actor_id": str(uuid4())},
        {"workspace_id": str(uuid4())},
        {"expected_current_version_id": "latest"},
        {"reason": "x" * 201},
        {"expected_open_signal_id": "latest"},
        {"reviewed_evidence_ids": []},
        {"content": "silent interpretation"},
    ],
)
def test_invalid_inputs_never_call_writer(api, change):
    client, service = api
    response = client.post(
        f"/api/v1/learning/lessons/{uuid4()}/review-commands",
        json=opening() | change,
        headers={"Idempotency-Key": "k"},
    )
    assert response.status_code == 422, response.text
    service.execute.assert_not_awaited()


@pytest.mark.parametrize(
    "field",
    [
        "confirmed",
        "expected_current_version_id",
        "expected_current_state",
        "expected_open_signal_id",
        "reason",
    ],
)
def test_required_pins_even_explicit_null(api, field):
    client, service = api
    body = opening()
    body.pop(field)
    response = client.post(
        f"/api/v1/learning/lessons/{uuid4()}/review-commands",
        json=body,
        headers={"Idempotency-Key": "k"},
    )
    assert response.status_code == 422, response.text
    service.execute.assert_not_awaited()


def test_actor_pin_and_body_and_key_pass_exactly(api):
    client, service = api
    body = opening()
    lid = uuid4()
    actor = uuid4()
    response = client.post(
        f"/api/v1/learning/lessons/{lid}/review-commands",
        json=body,
        headers={"Idempotency-Key": "k", "X-Actor-ID": str(actor)},
    )
    assert response.status_code == 200, response.text
    values = service.execute.await_args.kwargs
    assert (
        values["lesson_id"] == lid
        and values["actor_id"] == actor
        and values["idempotency_key"] == "k"
    )
    assert str(values["command"].expected_current_version_id) == body["expected_current_version_id"]
    assert values["command"].expected_open_signal_id is None
    assert str(values["command"].reviewed_evidence_ids[0]) == body["reviewed_evidence_ids"][0]


@pytest.mark.parametrize(
    "code,status",
    [
        ("LESSON_REVIEW_CONFLICT", 409),
        ("IDEMPOTENCY_KEY_REUSED", 409),
        ("LESSON_NOT_FOUND", 404),
        ("LESSON_REVIEW_INVALID", 422),
    ],
)
def test_structured_errors_preserve_owner_code(api, code, status):
    client, service = api
    service.execute.side_effect = ReviewCommandError(code, "Explicit failure")
    response = client.post(
        f"/api/v1/learning/lessons/{uuid4()}/review-commands",
        json=opening(),
        headers={"Idempotency-Key": "k"},
    )
    assert response.status_code == status, response.text
    assert response.json()["code"] == code


def test_absent_key_and_bad_actor_are_rejected(api):
    client, service = api
    path = f"/api/v1/learning/lessons/{uuid4()}/review-commands"
    assert client.post(path, json=opening()).status_code == 422
    assert (
        client.post(
            path, json=opening(), headers={"Idempotency-Key": "k", "X-Actor-ID": "not-a-uuid"}
        ).status_code
        == 422
    )
    service.execute.assert_not_awaited()
