from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Environment, Settings
from app.features.candidate.api.dependencies import get_candidate_live_workflow_service
from app.main import create_application

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
CANDIDATE_ID = UUID("20000000-0000-4000-8000-000000000001")
UNDERLYING_ID = UUID("30000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 8, 10, 18, 0, tzinfo=UTC)


def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment=Environment.TEST,
        documentation_enabled=True,
        log_level="CRITICAL",
    )


def test_live_workflow_returns_next_operator_action() -> None:
    service = AsyncMock()
    service.inspect.return_value = SimpleNamespace(
        candidate_id=CANDIDATE_ID,
        underlying_id=UNDERLYING_ID,
        as_of=NOW,
        ready=False,
        can_evaluate=False,
        next_action="CREATE_EODHD_MAPPING",
        steps=(
            SimpleNamespace(
                code="MARKET_PROVIDER_MAPPING",
                label="Market EODHD mapping",
                status="BLOCKED",
                detail="No EODHD mapping exists.",
                action="CREATE_EODHD_MAPPING",
                resource_id=None,
                action_params={"listing_id": "40000000-0000-4000-8000-000000000001"},
            ),
        ),
    )
    app = create_application(settings())
    app.dependency_overrides[get_candidate_live_workflow_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(f"/api/v1/candidates/{CANDIDATE_ID}/live-workflow")

    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is False
    assert body["next_action"] == "CREATE_EODHD_MAPPING"
    assert body["steps"][0]["status"] == "BLOCKED"
    assert body["steps"][0]["action_params"]["listing_id"] == "40000000-0000-4000-8000-000000000001"
    service.inspect.assert_awaited_once_with(
        workspace_id=WORKSPACE_ID,
        candidate_id=CANDIDATE_ID,
    )


def test_openapi_contains_candidate_live_workflow() -> None:
    with TestClient(create_application(settings())) as client:
        paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/candidates/{candidate_id}/live-workflow" in paths
