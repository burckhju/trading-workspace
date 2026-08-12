"""Integration tests for database readiness handling."""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.core.config import Environment, Settings
from app.main import create_application


def make_application():
    settings = Settings(
        environment=Environment.TEST,
        database_url="postgresql+asyncpg://localhost/trading_workspace_test",
    )
    return create_application(settings)


def test_readiness_returns_ready_when_database_ping_succeeds() -> None:
    application = make_application()
    application.state.container.database.ping = AsyncMock(return_value=None)

    with TestClient(application) as client:
        response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readiness_returns_service_unavailable_when_database_ping_fails() -> None:
    application = make_application()
    application.state.container.database.ping = AsyncMock(
        side_effect=RuntimeError("offline")
    )

    with TestClient(application) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    payload = response.json()
    assert payload["code"] == "HTTP_503"
    assert payload["message"] == "Database is unavailable"
