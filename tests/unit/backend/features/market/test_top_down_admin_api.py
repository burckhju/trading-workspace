from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Environment, Settings
from app.features.market.api.dependencies import (
    get_top_down_reference_administration_service,
)
from app.features.market.service.top_down_administration import TopDownV1BootstrapResult
from app.main import create_application

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
REF_ID = UUID("10000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 8, 10, 15, 0, tzinfo=UTC)


def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment=Environment.TEST,
        documentation_enabled=True,
        log_level="CRITICAL",
    )


def reference(code: str = "SP500") -> SimpleNamespace:
    return SimpleNamespace(
        id=REF_ID,
        workspace_id=WORKSPACE_ID,
        code=code,
        name="S&P 500",
        reference_type="INDEX",
        region="US",
        role="BROAD_MARKET",
        reference_version="TOP_DOWN_V1",
        active=True,
        created_at=NOW,
    )


def test_openapi_contains_top_down_reference_admin_routes() -> None:
    with TestClient(create_application(settings())) as client:
        paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/top-down-reference-data/bootstrap-v1" in paths
    assert (
        "/api/v1/top-down-reference-data/market-references/{reference_id}/listing-assignments"
        in paths
    )
    assert (
        "/api/v1/top-down-reference-data/underlyings/{underlying_id}/benchmark-assignments" in paths
    )
    assert "/api/v1/top-down-reference-data/underlyings/{underlying_id}/sector-assignments" in paths


def test_bootstrap_v1_delegates_and_returns_semantic_references() -> None:
    service = AsyncMock()
    service.bootstrap_v1.return_value = TopDownV1BootstrapResult((reference(),))
    application = create_application(settings())
    application.dependency_overrides[get_top_down_reference_administration_service] = (
        lambda: service
    )

    with TestClient(application) as client:
        response = client.post("/api/v1/top-down-reference-data/bootstrap-v1")

    assert response.status_code == 200
    assert response.json()[0]["code"] == "SP500"
    service.bootstrap_v1.assert_awaited_once_with(WORKSPACE_ID)


def test_eodhd_reference_suggestions_are_provider_boundary_hints() -> None:
    with TestClient(create_application(settings())) as client:
        response = client.get("/api/v1/top-down-reference-data/provider-suggestions/eodhd")

    assert response.status_code == 200
    values = {item["reference_code"]: item for item in response.json()}
    assert values["DAX"]["provider_symbol"] == "GDAXI"
    assert values["DAX"]["provider_exchange_code"] == "INDX"
    assert values["SP500"]["provider_symbol"] == "GSPC"
    assert values["NASDAQ100"]["provider_symbol"] is None
    assert values["NASDAQ100"]["verification_status"] == "REQUIRES_PROVIDER_VALIDATION"


def test_readiness_endpoint_returns_configuration_blockers() -> None:
    service = AsyncMock()
    service.reference_readiness.return_value = (
        SimpleNamespace(
            reference_id=REF_ID,
            reference_code="SP500",
            reference_type="INDEX",
            listing_id=None,
            provider_mapping_id=None,
            provider_mapping_active=False,
            daily_price_count=0,
            latest_price_date=None,
            completed_analysis_id=None,
            completed_analysis_version=None,
            ready=False,
            blockers=("NO_ACTIVE_LISTING_ASSIGNMENT", "NO_EODHD_PROVIDER_MAPPING"),
        ),
    )
    application = create_application(settings())
    application.dependency_overrides[get_top_down_reference_administration_service] = (
        lambda: service
    )

    with TestClient(application) as client:
        response = client.get("/api/v1/top-down-reference-data/readiness")

    assert response.status_code == 200
    assert response.json()[0]["ready"] is False
    assert "NO_ACTIVE_LISTING_ASSIGNMENT" in response.json()[0]["blockers"]
    service.reference_readiness.assert_awaited_once_with(WORKSPACE_ID)
