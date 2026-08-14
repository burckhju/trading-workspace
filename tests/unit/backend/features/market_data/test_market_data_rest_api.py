from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Environment, Settings
from app.features.market_data.api.dependencies import (
    get_daily_price_import_service,
    get_provider_venue_reconciliation_service,
)
from app.features.market_data.domain.enums import (
    CacheStatus,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.service.application import DailyPriceImportResult
from app.features.market_data.service.errors import (
    MarketDataNotFoundError,
    MarketDataRateLimitError,
)
from app.features.market_data.service.venue_reconciliation import (
    VenueReconciliationResult,
    VenueReconciliationStatus,
)
from app.main import create_application

LISTING_ID = UUID("10000000-0000-4000-8000-000000000001")
MAPPING_ID = UUID("20000000-0000-4000-8000-000000000001")
WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
REQUEST_ID = UUID("30000000-0000-4000-8000-000000000001")


def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment=Environment.TEST,
        documentation_enabled=True,
        log_level="CRITICAL",
    )


def result() -> DailyPriceImportResult:
    return DailyPriceImportResult(
        workspace_id=WORKSPACE_ID,
        listing_id=LISTING_ID,
        mapping_id=MAPPING_ID,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        inserted=20,
        updated=1,
        unchanged=2,
        provider=MarketDataProvider.EODHD,
        cache_status=CacheStatus.MISS,
        quality_status=QualityStatus.VALID,
        warnings=(),
        retry_count=1,
        provider_call_cost=2,
        retrieved_at=datetime(2026, 8, 5, 10, 0, tzinfo=UTC),
    )


def test_openapi_exposes_market_data_import_contract() -> None:
    with TestClient(create_application(settings())) as client:
        document = client.get("/openapi.json").json()
    assert "/api/v1/market-data/daily-prices/import" in document["paths"]
    assert "ImportDailyPricesRequest" in document["components"]["schemas"]
    assert "ImportDailyPricesResponse" in document["components"]["schemas"]


def test_import_delegates_with_request_id_as_correlation_id() -> None:
    service = AsyncMock()
    service.import_daily_prices.return_value = result()
    application = create_application(settings())
    application.dependency_overrides[get_daily_price_import_service] = lambda: service

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/market-data/daily-prices/import",
            headers={"X-Request-ID": str(REQUEST_ID)},
            json={
                "listing_id": str(LISTING_ID),
                "mapping_id": str(MAPPING_ID),
                "start_date": "2026-07-01",
                "end_date": "2026-07-31",
            },
        )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == str(REQUEST_ID)
    assert response.json()["processed"] == 23
    command = service.import_daily_prices.await_args.args[0]
    assert command.correlation_id == REQUEST_ID
    assert command.workspace_id == WORKSPACE_ID


def test_import_rejects_range_longer_than_ten_years() -> None:
    service = AsyncMock()
    application = create_application(settings())
    application.dependency_overrides[get_daily_price_import_service] = lambda: service
    with TestClient(application) as client:
        response = client.post(
            "/api/v1/market-data/daily-prices/import",
            json={
                "listing_id": str(LISTING_ID),
                "mapping_id": str(MAPPING_ID),
                "start_date": "2010-01-01",
                "end_date": "2026-01-01",
            },
        )
    assert response.status_code == 422
    service.import_daily_prices.assert_not_awaited()


def test_rate_limit_uses_stable_error_contract_and_retry_metadata() -> None:
    service = AsyncMock()
    service.import_daily_prices.side_effect = MarketDataRateLimitError(
        "Provider request limit reached",
        provider=MarketDataProvider.EODHD,
        retryable=True,
        retry_after=timedelta(seconds=12),
    )
    application = create_application(settings())
    application.dependency_overrides[get_daily_price_import_service] = lambda: service
    with TestClient(application) as client:
        response = client.post(
            "/api/v1/market-data/daily-prices/import",
            json={
                "listing_id": str(LISTING_ID),
                "mapping_id": str(MAPPING_ID),
                "start_date": "2026-07-01",
                "end_date": "2026-07-31",
            },
        )
    assert response.status_code == 429
    assert response.json()["code"] == "MARKET_DATA_RATE_LIMIT_ERROR"
    assert response.json()["details"][0]["context"]["retry_after_seconds"] == 12.0


def test_venue_reconciliation_endpoint_exposes_read_only_evidence() -> None:
    service = AsyncMock()
    venue_id = UUID("40000000-0000-4000-8000-000000000001")
    service.reconcile_mapping.return_value = VenueReconciliationResult(
        status=VenueReconciliationStatus.MATCHED,
        listing_venue_id=venue_id,
        evidence_venue_ids=(venue_id,),
    )
    application = create_application(settings())
    application.dependency_overrides[get_provider_venue_reconciliation_service] = (
        lambda: service
    )

    with TestClient(application) as client:
        response = client.get(
            f"/api/v1/market-data/provider-mappings/{MAPPING_ID}/venue-reconciliation"
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "MATCHED",
        "listing_venue_id": str(venue_id),
        "evidence_venue_ids": [str(venue_id)],
        "explanation": "Provider evidence confirms the listing trading venue.",
    }
    service.reconcile_mapping.assert_awaited_once_with(WORKSPACE_ID, MAPPING_ID)


def test_venue_reconciliation_endpoint_maps_missing_mapping_to_404() -> None:
    service = AsyncMock()
    service.reconcile_mapping.side_effect = MarketDataNotFoundError(
        "Provider mapping not found"
    )
    application = create_application(settings())
    application.dependency_overrides[get_provider_venue_reconciliation_service] = (
        lambda: service
    )

    with TestClient(application) as client:
        response = client.get(
            f"/api/v1/market-data/provider-mappings/{MAPPING_ID}/venue-reconciliation"
        )

    assert response.status_code == 404
    assert response.json()["code"] == "MARKET_DATA_NOT_FOUND"
