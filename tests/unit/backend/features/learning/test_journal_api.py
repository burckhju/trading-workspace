"""Journal wire validation does not substitute for command or PostgreSQL tests."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from app.core.config import Environment, Settings
from app.main import create_application
from app.features.learning.api.journal_dependencies import get_journal_service
from app.features.learning.application.journal_service import JournalError, JournalReceipt


@pytest.fixture
def api():
    service = SimpleNamespace(
        execute=AsyncMock(return_value=JournalReceipt(uuid4(), "TRADE_JOURNAL_VERSION", False)),
        history=AsyncMock(),
        version=AsyncMock(),
    )
    app = create_application(Settings(_env_file=None, environment=Environment.TEST))
    app.dependency_overrides[get_journal_service] = lambda: service
    return TestClient(app), service


def create():
    return dict(
        operation="CREATE_DRAFT",
        expected_latest_version_id=None,
        expected_exit_review_version_id=str(uuid4()),
        confirmed=True,
    )


@pytest.mark.parametrize(
    "change",
    [
        {"confirmed": False},
        {"expected_edit_revision": 1},
        {"expected_exit_review_version_id": "bad"},
        {"operation": "AUTO_LESSON"},
        {"unexpected": "field"},
    ],
)
def test_invalid_body_never_calls_writer(api, change):
    client, service = api
    response = client.post(
        f"/api/v1/learning/trades/{uuid4()}/journal/commands",
        json=create() | change,
        headers={"Idempotency-Key": "once"},
    )
    assert response.status_code == 422, response.text
    service.execute.assert_not_awaited()


@pytest.mark.parametrize(
    "missing", ["expected_latest_version_id", "confirmed", "expected_exit_review_version_id"]
)
def test_required_confirmation_and_preconditions(api, missing):
    client, service = api
    body = create()
    body.pop(missing)
    response = client.post(
        f"/api/v1/learning/trades/{uuid4()}/journal/commands",
        json=body,
        headers={"Idempotency-Key": "once"},
    )
    assert response.status_code == 422, response.text
    service.execute.assert_not_awaited()


def test_absent_idempotency_header_and_missing_save_revision(api):
    client, service = api
    url = f"/api/v1/learning/trades/{uuid4()}/journal/commands"
    assert client.post(url, json=create()).status_code == 422
    assert (
        client.post(
            url,
            json=dict(
                operation="SAVE_DRAFT",
                version_id=str(uuid4()),
                what_went_well=None,
                would_do_differently=None,
                additional_notes=None,
            ),
            headers={"Idempotency-Key": "save"},
        ).status_code
        == 422
    )
    service.execute.assert_not_awaited()


def test_body_identity_is_forbidden_and_current_actor_is_passed(api):
    client, service = api
    trade = uuid4()
    url = f"/api/v1/learning/trades/{trade}/journal/commands"
    response = client.post(
        url, json=create() | {"actor_id": str(uuid4())}, headers={"Idempotency-Key": "once"}
    )
    assert response.status_code == 422
    response = client.post(url, json=create(), headers={"Idempotency-Key": "once"})
    assert response.status_code == 200, response.text
    kwargs = service.execute.call_args.kwargs
    assert (
        kwargs["trade_id"] == trade
        and str(kwargs["actor_id"]) == "00000000-0000-4000-8000-000000000002"
    )


@pytest.mark.parametrize(
    "code,status",
    [
        ("JOURNAL_CONFLICT", 409),
        ("SOURCE_VERSION_MISMATCH", 409),
        ("JOURNAL_NOT_FOUND", 404),
        ("JOURNAL_INVALID_REQUEST", 422),
    ],
)
def test_domain_errors_preserve_structured_codes(api, code, status):
    client, service = api
    service.execute.side_effect = JournalError(code, "explicit failure")
    response = client.post(
        f"/api/v1/learning/trades/{uuid4()}/journal/commands",
        json=create(),
        headers={"Idempotency-Key": "once"},
    )
    assert response.status_code == status, response.text
    assert response.json()["code"] == code
