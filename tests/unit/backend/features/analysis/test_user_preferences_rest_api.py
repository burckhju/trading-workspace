from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Environment, Settings
from app.features.user_preferences.api.dependencies import get_user_preference_service
from app.main import create_application

PREFERENCE_ID = UUID("50000000-0000-4000-8000-000000000001")
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 8, 6, 19, 0, tzinfo=UTC)


def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment=Environment.TEST,
        documentation_enabled=True,
        log_level="CRITICAL",
    )


def preference():
    return SimpleNamespace(
        id=PREFERENCE_ID,
        kind="analysis-overview-view",
        name="Meine Ansicht",
        value={"status": "COMPLETED"},
        created_at=NOW,
        updated_at=NOW,
    )


def test_preferences_are_scoped_by_actor_header() -> None:
    service = AsyncMock()
    service.list.return_value = (preference(),)
    application = create_application(settings())
    application.dependency_overrides[get_user_preference_service] = lambda: service
    with TestClient(application) as client:
        response = client.get(
            "/api/v1/user-preferences/analysis-overview-view",
            headers={"X-Actor-ID": "user-42"},
        )
    assert response.status_code == 200
    assert response.json()[0]["name"] == "Meine Ansicht"
    service.list.assert_awaited_once_with(
        WORKSPACE_ID, "user-42", "analysis-overview-view"
    )


def test_create_preference_uses_local_actor_fallback() -> None:
    service = AsyncMock()
    service.create.return_value = preference()
    application = create_application(settings())
    application.dependency_overrides[get_user_preference_service] = lambda: service
    with TestClient(application) as client:
        response = client.post(
            "/api/v1/user-preferences/analysis-overview-view",
            json={"name": "Meine Ansicht", "value": {"status": "COMPLETED"}},
        )
    assert response.status_code == 201
    service.create.assert_awaited_once_with(
        WORKSPACE_ID,
        "local-user",
        "analysis-overview-view",
        "Meine Ansicht",
        {"status": "COMPLETED"},
    )


def test_delete_preference_keeps_actor_scope() -> None:
    service = AsyncMock()
    service.delete.return_value = True
    application = create_application(settings())
    application.dependency_overrides[get_user_preference_service] = lambda: service
    with TestClient(application) as client:
        response = client.delete(
            f"/api/v1/user-preferences/analysis-overview-view/{PREFERENCE_ID}",
            headers={"X-Actor-ID": "user-42"},
        )
    assert response.status_code == 204
    service.delete.assert_awaited_once_with(WORKSPACE_ID, "user-42", PREFERENCE_ID)
