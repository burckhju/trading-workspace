from datetime import UTC, date, datetime
from unittest.mock import AsyncMock
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Environment, Settings
from app.features.analysis.api.dependencies import get_market_analysis_service
from app.features.analysis.domain.errors import (
    AnalysisDataUnavailable,
    AnalysisNotFound,
)
from app.features.analysis.persistence.models import (
    MarketAnalysisModel,
    MarketAnalysisRunModel,
)
from app.main import create_application

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
ANALYSIS_ID = UUID("10000000-0000-4000-8000-000000000001")
UNDERLYING_ID = UUID("20000000-0000-4000-8000-000000000001")
LISTING_ID = UUID("30000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 8, 5, 15, 0, tzinfo=UTC)


def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment=Environment.TEST,
        documentation_enabled=True,
        log_level="CRITICAL",
    )


def analysis_model() -> MarketAnalysisModel:
    return MarketAnalysisModel(
        id=ANALYSIS_ID,
        workspace_id=WORKSPACE_ID,
        underlying_id=UNDERLYING_ID,
        listing_id=LISTING_ID,
        created_at=NOW,
        created_by="Test User",
    )


def run_model() -> MarketAnalysisRunModel:
    return MarketAnalysisRunModel(
        id=UUID("40000000-0000-4000-8000-000000000001"),
        analysis_id=ANALYSIS_ID,
        version=1,
        status="COMPLETED",
        quality_status="GOOD",
        model_id="EOD_TREND_MOMENTUM",
        model_version="1.0.0",
        parameters={},
        metrics={},
        notes=[],
        data_sources=["EODHD"],
        input_hash="a" * 64,
        observation_count=220,
        analysis_time=NOW,
        correlation_id="correlation-1",
        error_message=None,
    )


def test_openapi_exposes_ft006_contracts() -> None:
    with TestClient(create_application(settings())) as client:
        document = client.get("/openapi.json").json()

    assert "/api/v1/market-analyses" in document["paths"]
    assert "/api/v1/market-analyses/{analysis_id}/runs" in document["paths"]
    assert "/api/v1/market-analyses/{analysis_id}/runs/{version}" in document["paths"]
    assert "CreateAnalysisRequest" in document["components"]["schemas"]
    assert "AnalysisRunDetailResponse" in document["components"]["schemas"]


def test_create_delegates_actor_and_workspace() -> None:
    service = AsyncMock()
    service.create.return_value = analysis_model()
    application = create_application(settings())
    application.dependency_overrides[get_market_analysis_service] = lambda: service

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/market-analyses",
            headers={"X-Actor-Name": "Test User"},
            json={"underlying_id": str(UNDERLYING_ID), "listing_id": str(LISTING_ID)},
        )

    assert response.status_code == 201
    assert response.json()["id"] == str(ANALYSIS_ID)
    service.create.assert_awaited_once_with(
        WORKSPACE_ID,
        UNDERLYING_ID,
        LISTING_ID,
        "Test User",
    )


def test_run_delegates_correlation_id_and_resolved_parameters() -> None:
    service = AsyncMock()
    service.run.return_value = run_model()
    application = create_application(settings())
    application.dependency_overrides[get_market_analysis_service] = lambda: service

    with TestClient(application) as client:
        response = client.post(
            f"/api/v1/market-analyses/{ANALYSIS_ID}/runs",
            headers={"X-Correlation-ID": "correlation-1"},
            json={"start_date": "2025-01-01", "end_date": "2025-12-31"},
        )

    assert response.status_code == 201
    assert response.json()["input_hash"] == "a" * 64
    args = service.run.await_args.args
    assert args[0] == WORKSPACE_ID
    assert args[1] == ANALYSIS_ID
    assert args[2:4] == (date(2025, 1, 1), date(2025, 12, 31))
    assert args[4].long_window == 200
    assert args[5] == "correlation-1"


def test_run_rejects_reverse_date_range_before_service_call() -> None:
    service = AsyncMock()
    application = create_application(settings())
    application.dependency_overrides[get_market_analysis_service] = lambda: service

    with TestClient(application) as client:
        response = client.post(
            f"/api/v1/market-analyses/{ANALYSIS_ID}/runs",
            json={"start_date": "2026-02-01", "end_date": "2026-01-01"},
        )

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_DATE_RANGE"
    service.run.assert_not_awaited()


def test_not_found_maps_to_404_with_stable_code() -> None:
    service = AsyncMock()
    service.get.side_effect = AnalysisNotFound("analysis not found")
    application = create_application(settings())
    application.dependency_overrides[get_market_analysis_service] = lambda: service

    with TestClient(application) as client:
        response = client.get(f"/api/v1/market-analyses/{ANALYSIS_ID}")

    assert response.status_code == 404
    assert response.json()["code"] == "ANALYSIS_NOT_FOUND"


def test_unavailable_data_maps_to_422_with_stable_code() -> None:
    service = AsyncMock()
    service.run.side_effect = AnalysisDataUnavailable("no persisted market data")
    application = create_application(settings())
    application.dependency_overrides[get_market_analysis_service] = lambda: service

    with TestClient(application) as client:
        response = client.post(
            f"/api/v1/market-analyses/{ANALYSIS_ID}/runs",
            json={"start_date": "2025-01-01", "end_date": "2025-12-31"},
        )

    assert response.status_code == 422
    assert response.json()["code"] == "ANALYSIS_DATA_UNAVAILABLE"


def test_run_detail_can_omit_snapshot_without_breaking_response_contract() -> None:
    service = AsyncMock()
    service.details.return_value = (analysis_model(), run_model(), (), ())
    application = create_application(settings())
    application.dependency_overrides[get_market_analysis_service] = lambda: service

    with TestClient(application) as client:
        response = client.get(
            f"/api/v1/market-analyses/{ANALYSIS_ID}/runs/1?include_snapshot=false"
        )

    assert response.status_code == 200
    assert response.json()["snapshot"] == []
    service.details.assert_awaited_once_with(WORKSPACE_ID, ANALYSIS_ID, 1, False)


def test_snapshot_endpoint_exposes_stable_pagination_contract() -> None:
    from types import SimpleNamespace

    service = AsyncMock()
    row = SimpleNamespace(
        trading_date=date(2026, 8, 5),
        open=100,
        high=103,
        low=99,
        close=102,
        adjusted_close=102,
        volume=1000,
        currency="EUR",
        provider="EODHD",
        provider_symbol="SIE.XETRA",
        quality_status="GOOD",
        warnings=[],
    )
    service.snapshot.return_value = ((row,), 220)
    application = create_application(settings())
    application.dependency_overrides[get_market_analysis_service] = lambda: service

    with TestClient(application) as client:
        response = client.get(
            f"/api/v1/market-analyses/{ANALYSIS_ID}/runs/1/snapshot?offset=50&limit=25"
        )

    assert response.status_code == 200
    assert response.json()["total"] == 220
    assert response.json()["offset"] == 50
    assert response.json()["limit"] == 25
    assert response.json()["items"][0]["provider_symbol"] == "SIE.XETRA"
    service.snapshot.assert_awaited_once_with(WORKSPACE_ID, ANALYSIS_ID, 1, 50, 25)


def test_analysis_overview_page_exposes_readable_references_and_pagination() -> None:
    from types import SimpleNamespace

    service = AsyncMock()
    service.overview.return_value = (
        (
            SimpleNamespace(
                analysis=analysis_model(),
                underlying_name="Siemens AG",
                ticker="SIE",
                trading_venue_mic="XETR",
                trading_venue_name="Xetra",
                currency_code="EUR",
                latest_version=3,
                latest_status="COMPLETED",
                latest_quality_status="GOOD",
                latest_analysis_time=datetime(2026, 8, 6, 10, 0, tzinfo=UTC),
            ),
        ),
        42,
    )
    application = create_application(settings())
    application.dependency_overrides[get_market_analysis_service] = lambda: service

    with TestClient(application) as client:
        response = client.get(
            "/api/v1/market-analyses/page?offset=20&limit=10&status=COMPLETED&quality_status=GOOD&sort_by=latest_analysis_time&sort_direction=asc"
        )

    assert response.status_code == 200
    assert response.json()["total"] == 42
    assert response.json()["offset"] == 20
    assert response.json()["limit"] == 10
    assert response.json()["items"][0]["underlying_name"] == "Siemens AG"
    assert response.json()["items"][0]["ticker"] == "SIE"
    assert response.json()["items"][0]["trading_venue_name"] == "Xetra"
    assert response.json()["items"][0]["currency_code"] == "EUR"
    assert response.json()["items"][0]["latest_status"] == "COMPLETED"
    assert response.json()["items"][0]["latest_quality_status"] == "GOOD"
    filters = service.overview.await_args.args[3]
    assert filters.status == "COMPLETED"
    assert filters.quality_status == "GOOD"
    assert filters.sort_by == "latest_analysis_time"
    assert filters.sort_direction == "asc"


def test_analysis_overview_csv_export_uses_current_filters() -> None:
    from types import SimpleNamespace

    service = AsyncMock()
    service.overview.return_value = (
        (
            SimpleNamespace(
                analysis=analysis_model(),
                underlying_name="Siemens AG",
                ticker="SIE",
                trading_venue_mic="XETR",
                trading_venue_name="Xetra",
                currency_code="EUR",
                latest_version=3,
                latest_status="COMPLETED",
                latest_quality_status="GOOD",
                latest_analysis_time=datetime(2026, 8, 6, 10, 0, tzinfo=UTC),
            ),
        ),
        1,
    )
    application = create_application(settings())
    application.dependency_overrides[get_market_analysis_service] = lambda: service

    with TestClient(application) as client:
        response = client.get(
            "/api/v1/market-analyses/export.csv?status=COMPLETED&quality_status=GOOD"
            "&sort_by=latest_analysis_time&sort_direction=asc"
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "market-analyses.csv" in response.headers["content-disposition"]
    assert "Analyse-ID;Basiswert;Ticker" in response.text
    assert "Siemens AG;SIE;XETR;Xetra;EUR;3;COMPLETED;GOOD" in response.text
    filters = service.overview.await_args.args[3]
    assert service.overview.await_args.args[1:3] == (0, 10000)
    assert filters.status == "COMPLETED"
    assert filters.quality_status == "GOOD"
    assert filters.sort_by == "latest_analysis_time"
    assert filters.sort_direction == "asc"


def test_openapi_exposes_lifecycle_contracts() -> None:
    with TestClient(create_application(settings())) as client:
        document = client.get("/openapi.json").json()
    paths = document["paths"]
    assert "/api/v1/market-analyses/{analysis_id}/runs/{version}/retry" in paths
    assert "/api/v1/market-analyses/{analysis_id}/runs/{version}/supersede" in paths
    assert "/api/v1/market-analyses/{analysis_id}/events" in paths


def test_retry_delegates_without_new_market_data_parameters() -> None:
    service = AsyncMock()
    replacement = run_model()
    replacement.version = 2
    replacement.status = "COMPLETED"
    service.retry.return_value = replacement
    application = create_application(settings())
    application.dependency_overrides[get_market_analysis_service] = lambda: service

    with TestClient(application) as client:
        response = client.post(
            f"/api/v1/market-analyses/{ANALYSIS_ID}/runs/1/retry",
            headers={"X-Correlation-ID": "retry-correlation"},
            json={"reason": "same persisted snapshot"},
        )

    assert response.status_code == 201
    assert response.json()["version"] == 2
    service.retry.assert_awaited_once_with(
        WORKSPACE_ID, ANALYSIS_ID, 1, "retry-correlation", "same persisted snapshot"
    )


def test_supersede_delegates_replacement_version() -> None:
    from types import SimpleNamespace

    service = AsyncMock()
    service.supersede.return_value = SimpleNamespace(
        id=UUID("50000000-0000-4000-8000-000000000001"),
        version=1,
        event_type="SUPERSEDED",
        from_status="COMPLETED",
        to_status="SUPERSEDED",
        source_version=1,
        replacement_version=2,
        reason="newer validated version",
        correlation_id="supersede-correlation",
        occurred_at=NOW,
    )
    application = create_application(settings())
    application.dependency_overrides[get_market_analysis_service] = lambda: service

    with TestClient(application) as client:
        response = client.post(
            f"/api/v1/market-analyses/{ANALYSIS_ID}/runs/1/supersede",
            headers={"X-Correlation-ID": "supersede-correlation"},
            json={"replacement_version": 2, "reason": "newer validated version"},
        )

    assert response.status_code == 201
    assert response.json()["to_status"] == "SUPERSEDED"
    assert response.json()["replacement_version"] == 2
    service.supersede.assert_awaited_once_with(
        WORKSPACE_ID,
        ANALYSIS_ID,
        1,
        2,
        "supersede-correlation",
        "newer validated version",
    )


def test_lifecycle_conflict_maps_to_409() -> None:
    from app.features.analysis.domain.errors import AnalysisConflict

    service = AsyncMock()
    service.retry.side_effect = AnalysisConflict(
        "analysis run with status COMPLETED cannot be retried"
    )
    application = create_application(settings())
    application.dependency_overrides[get_market_analysis_service] = lambda: service

    with TestClient(application) as client:
        response = client.post(
            f"/api/v1/market-analyses/{ANALYSIS_ID}/runs/1/retry",
            json={},
        )

    assert response.status_code == 409
    assert response.json()["code"] == "ANALYSIS_CONFLICT"


def test_reproducibility_verification_exposes_explicit_checks() -> None:
    service = AsyncMock()
    service.verify_reproducibility.return_value = {
        "verified": True,
        "model_available": True,
        "input_hash_matches": True,
        "metrics_match": True,
        "criteria_match": True,
        "quality_status_match": True,
        "notes_match": True,
    }
    application = create_application(settings())
    application.dependency_overrides[get_market_analysis_service] = lambda: service

    with TestClient(application) as client:
        response = client.post(f"/api/v1/market-analyses/{ANALYSIS_ID}/runs/1/verify")

    assert response.status_code == 200
    assert response.json()["verified"] is True
    assert response.json()["input_hash_matches"] is True
    service.verify_reproducibility.assert_awaited_once_with(
        WORKSPACE_ID, ANALYSIS_ID, 1
    )
