from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Environment, Settings
from app.main import create_application


def _test_settings() -> Settings:
    return Settings(
        _env_file=None,
        environment=Environment.TEST,
        documentation_enabled=False,
        log_level="CRITICAL",
    )


def test_health_endpoint_reports_liveness_and_request_id() -> None:
    with TestClient(create_application(_test_settings())) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    UUID(response.headers["x-request-id"])


def test_valid_request_id_is_preserved() -> None:
    request_id = "4f50400d-40e2-4c67-bb0e-e6b6eb76f4fd"

    with TestClient(create_application(_test_settings())) as client:
        response = client.get("/health", headers={"X-Request-ID": request_id})

    assert response.headers["x-request-id"] == request_id


def test_documentation_is_disabled_when_configured() -> None:
    with TestClient(create_application(_test_settings())) as client:
        docs_response = client.get("/docs")
        openapi_response = client.get("/openapi.json")

    assert docs_response.status_code == 404
    assert openapi_response.status_code == 404


def test_unknown_route_uses_standard_error_contract() -> None:
    with TestClient(create_application(_test_settings())) as client:
        response = client.get("/unknown")

    payload = response.json()
    assert response.status_code == 404
    assert payload["code"] == "HTTP_404"
    assert payload["message"] == "Not Found"
    assert payload["details"] == []
    assert payload["timestamp"].endswith("+00:00")
