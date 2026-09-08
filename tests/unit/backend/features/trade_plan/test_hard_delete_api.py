from unittest.mock import AsyncMock
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Environment, Settings
from app.features.trade_plan.api.dependencies import get_trade_plan_hard_delete_service
from app.features.trade_plan.service.hard_delete import TradePlanDeletionSummary
from app.main import create_application

PLAN_ID = UUID("20000000-0000-4000-8000-000000000001")
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")


def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment=Environment.TEST,
        documentation_enabled=True,
        log_level="CRITICAL",
    )


def test_delete_trade_plan_delegates_and_returns_summary() -> None:
    service = AsyncMock()
    service.delete.return_value = TradePlanDeletionSummary(
        trade_plan_id=PLAN_ID,
        trade_plan_versions=2,
        product_selection_runs=1,
        trades=1,
        positions=1,
        alerts=1,
        notifications=1,
        post_trade_observations=1,
        exit_reviews=1,
        trade_journals=1,
        learning_evidence=2,
        external_observation_trade_links=1,
    )
    application = create_application(settings())
    application.dependency_overrides[get_trade_plan_hard_delete_service] = lambda: service

    with TestClient(application) as client:
        response = client.delete(f"/api/v1/trade-plans/{PLAN_ID}")

    assert response.status_code == 200
    assert response.json() == {
        "trade_plan_id": str(PLAN_ID),
        "trade_plan_versions": 2,
        "product_selection_runs": 1,
        "trades": 1,
        "positions": 1,
        "alerts": 1,
        "notifications": 1,
        "post_trade_observations": 1,
        "exit_reviews": 1,
        "trade_journals": 1,
        "learning_evidence": 2,
        "external_observation_trade_links": 1,
    }
    service.delete.assert_awaited_once_with(workspace_id=WORKSPACE_ID, trade_plan_id=PLAN_ID)


def test_delete_trade_plan_translates_missing_plan() -> None:
    service = AsyncMock()
    service.delete.side_effect = ValueError("trade plan not found")
    application = create_application(settings())
    application.dependency_overrides[get_trade_plan_hard_delete_service] = lambda: service

    with TestClient(application) as client:
        response = client.delete(f"/api/v1/trade-plans/{PLAN_ID}")

    assert response.status_code == 404
