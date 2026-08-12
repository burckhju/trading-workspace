from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Environment, Settings
from app.features.market.api.dependencies import (
    get_listing_service,
    get_reference_data_service,
    get_underlying_service,
)
from app.features.market.domain.enums import (
    DataOrigin,
    LifecycleStatus,
    QualityStatus,
    UnderlyingType,
)
from app.features.market.persistence.models import (
    CurrencyModel,
    ListingModel,
    TradingVenueModel,
    UnderlyingModel,
)
from app.features.market.service.errors import (
    DuplicateIsin,
    UnderlyingDeleteReferenced,
    UnderlyingNotFound,
)
from app.features.market.service.types import UsageReference, UsageSummary
from app.main import create_application

NOW = datetime(2026, 8, 4, 16, 0, tzinfo=UTC)
UNDERLYING_ID = UUID("10000000-0000-4000-8000-000000000001")
VENUE_ID = UUID("00000000-0000-4000-8001-000000000001")


def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment=Environment.TEST,
        documentation_enabled=True,
        log_level="CRITICAL",
    )


def model() -> UnderlyingModel:
    return UnderlyingModel(
        id=UNDERLYING_ID,
        workspace_id=UUID("00000000-0000-4000-8000-000000000001"),
        type=UnderlyingType.STOCK,
        name="Siemens AG",
        isin="DE0007236101",
        wkn="723610",
        lifecycle_status=LifecycleStatus.ACTIVE,
        quality_status=QualityStatus.COMPLETE,
        version=1,
        created_at=NOW,
        updated_at=NOW,
        data_origin=DataOrigin.MANUAL,
    )


def test_openapi_contains_versioned_ft001_routes() -> None:
    with TestClient(create_application(settings())) as client:
        paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/underlyings" in paths
    assert "/api/v1/underlyings/{underlying_id}" in paths
    assert "/api/v1/underlyings/{underlying_id}/listings" in paths
    assert "/api/v1/underlyings/{underlying_id}/primary-listing/{listing_id}" in paths
    assert "/api/v1/market-reference-data/trading-venues" in paths
    assert "/api/v1/market-reference-data/currencies" in paths


def test_create_underlying_delegates_to_service_and_returns_201() -> None:
    service = AsyncMock()
    service.create.return_value = model()
    application = create_application(settings())
    application.dependency_overrides[get_underlying_service] = lambda: service

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/underlyings",
            headers={"X-Actor-ID": "user-1", "X-Actor-Name": "Test User"},
            json={
                "name": "Siemens AG",
                "isin": "DE0007236101",
                "wkn": "723610",
                "primary_listing": {
                    "trading_venue_id": str(VENUE_ID),
                    "ticker": "SIE",
                    "currency_code": "EUR",
                },
            },
        )

    assert response.status_code == 201
    assert response.json()["id"] == str(UNDERLYING_ID)
    command = service.create.await_args.args[0]
    assert command.workspace_id == UUID("00000000-0000-4000-8000-000000000001")
    assert command.actor.display_name == "Test User"


def test_service_conflict_uses_stable_error_contract() -> None:
    service = AsyncMock()
    service.create.side_effect = DuplicateIsin("ISIN already exists", field="isin")
    application = create_application(settings())
    application.dependency_overrides[get_underlying_service] = lambda: service

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/underlyings",
            json={
                "name": "Siemens AG",
                "primary_listing": {
                    "trading_venue_id": str(VENUE_ID),
                    "ticker": "SIE",
                    "currency_code": "EUR",
                },
            },
        )

    payload = response.json()
    assert response.status_code == 409
    assert payload["code"] == "UNDERLYING_DUPLICATE_ISIN"
    assert payload["details"][0]["field"] == "isin"


def test_missing_underlying_maps_to_404() -> None:
    service = AsyncMock()
    service.get.side_effect = UnderlyingNotFound("Underlying does not exist")
    application = create_application(settings())
    application.dependency_overrides[get_underlying_service] = lambda: service

    with TestClient(application) as client:
        response = client.get(f"/api/v1/underlyings/{UNDERLYING_ID}")

    assert response.status_code == 404
    assert response.json()["code"] == "UNDERLYING_NOT_FOUND"


def test_listing_routes_resolve_listing_service_dependency() -> None:
    service = AsyncMock()
    service.add.return_value = ListingModel(
        id=UUID("20000000-0000-4000-8000-000000000001"),
        workspace_id=UUID("00000000-0000-4000-8000-000000000001"),
        underlying_id=UNDERLYING_ID,
        trading_venue_id=VENUE_ID,
        ticker="SIE",
        currency_code="EUR",
        lifecycle_status=LifecycleStatus.ACTIVE,
        is_primary=False,
        version=1,
        created_at=NOW,
        updated_at=NOW,
        data_origin=DataOrigin.MANUAL,
    )
    application = create_application(settings())
    application.dependency_overrides[get_listing_service] = lambda: service

    with TestClient(application) as client:
        response = client.post(
            f"/api/v1/underlyings/{UNDERLYING_ID}/listings",
            json={
                "trading_venue_id": str(VENUE_ID),
                "ticker": "SIE",
                "currency_code": "EUR",
            },
        )

    assert response.status_code == 201
    assert response.json()["ticker"] == "SIE"
    service.add.assert_awaited_once()


def test_openapi_exposes_named_ft001_dto_schemas() -> None:
    with TestClient(create_application(settings())) as client:
        schemas = client.get("/openapi.json").json()["components"]["schemas"]

    assert "CreateUnderlyingRequest" in schemas
    assert "UpdateUnderlyingRequest" in schemas
    assert "UnderlyingSummaryResponse" in schemas
    assert "UnderlyingDetailResponse" in schemas
    assert "ListingResponse" in schemas
    assert "TradingVenueListResponse" in schemas
    assert "CurrencyListResponse" in schemas


def test_create_request_rejects_unknown_transport_fields() -> None:
    service = AsyncMock()
    application = create_application(settings())
    application.dependency_overrides[get_underlying_service] = lambda: service

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/underlyings",
            json={
                "name": "Siemens AG",
                "unexpected": "not part of the contract",
                "primary_listing": {
                    "trading_venue_id": str(VENUE_ID),
                    "ticker": "SIE",
                    "currency_code": "EUR",
                },
            },
        )

    assert response.status_code == 422
    service.create.assert_not_awaited()


def test_create_request_rejects_invalid_uuid_before_service_call() -> None:
    service = AsyncMock()
    application = create_application(settings())
    application.dependency_overrides[get_underlying_service] = lambda: service

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/underlyings",
            json={
                "name": "Siemens AG",
                "primary_listing": {
                    "trading_venue_id": "not-a-uuid",
                    "ticker": "SIE",
                    "currency_code": "EUR",
                },
            },
        )

    assert response.status_code == 422
    service.create.assert_not_awaited()


def test_update_dto_preserves_omitted_identifier_semantics() -> None:
    service = AsyncMock()
    service.update.return_value = model()
    application = create_application(settings())
    application.dependency_overrides[get_underlying_service] = lambda: service

    with TestClient(application) as client:
        response = client.patch(
            f"/api/v1/underlyings/{UNDERLYING_ID}",
            json={"version": 1, "name": "Siemens Energy AG"},
        )

    assert response.status_code == 200
    command = service.update.await_args.args[0]
    assert command.name == "Siemens Energy AG"
    assert command.isin is ...
    assert command.wkn is ...


def test_update_dto_preserves_explicit_identifier_removal() -> None:
    service = AsyncMock()
    service.update.return_value = model()
    application = create_application(settings())
    application.dependency_overrides[get_underlying_service] = lambda: service

    with TestClient(application) as client:
        response = client.patch(
            f"/api/v1/underlyings/{UNDERLYING_ID}",
            json={"version": 1, "isin": None},
        )

    assert response.status_code == 200
    command = service.update.await_args.args[0]
    assert command.isin is None
    assert command.wkn is ...


def test_create_rejects_blank_and_oversized_transport_values() -> None:
    service = AsyncMock()
    application = create_application(settings())
    application.dependency_overrides[get_underlying_service] = lambda: service
    with TestClient(application) as client:
        blank = client.post(
            "/api/v1/underlyings",
            json={
                "name": "   ",
                "primary_listing": {
                    "trading_venue_id": str(VENUE_ID),
                    "ticker": "SIE",
                    "currency_code": "EUR",
                },
            },
        )
        long_ticker = client.post(
            "/api/v1/underlyings",
            json={
                "name": "Siemens AG",
                "primary_listing": {
                    "trading_venue_id": str(VENUE_ID),
                    "ticker": "X" * 33,
                    "currency_code": "EUR",
                },
            },
        )
    assert blank.status_code == 422
    assert long_ticker.status_code == 422
    service.create.assert_not_awaited()


def test_update_requires_at_least_one_mutable_field() -> None:
    service = AsyncMock()
    application = create_application(settings())
    application.dependency_overrides[get_underlying_service] = lambda: service
    with TestClient(application) as client:
        response = client.patch(f"/api/v1/underlyings/{UNDERLYING_ID}", json={"version": 1})
    assert response.status_code == 422
    service.update.assert_not_awaited()


def test_versions_and_pagination_have_safe_ranges() -> None:
    service = AsyncMock()
    application = create_application(settings())
    application.dependency_overrides[get_underlying_service] = lambda: service
    with TestClient(application) as client:
        invalid_version = client.patch(
            f"/api/v1/underlyings/{UNDERLYING_ID}",
            json={"version": 0, "name": "New Name"},
        )
        invalid_offset = client.get("/api/v1/underlyings?offset=-1")
        invalid_limit = client.get("/api/v1/underlyings?limit=101")
    assert invalid_version.status_code == 422
    assert invalid_offset.status_code == 422
    assert invalid_limit.status_code == 422


def test_currency_code_requires_three_letters() -> None:
    service = AsyncMock()
    application = create_application(settings())
    application.dependency_overrides[get_underlying_service] = lambda: service
    with TestClient(application) as client:
        response = client.post(
            "/api/v1/underlyings",
            json={
                "name": "Siemens AG",
                "primary_listing": {
                    "trading_venue_id": str(VENUE_ID),
                    "ticker": "SIE",
                    "currency_code": "EU1",
                },
            },
        )
    assert response.status_code == 422
    service.create.assert_not_awaited()


def listing_model(*, listing_id: UUID | None = None, primary: bool = False) -> ListingModel:
    return ListingModel(
        id=listing_id or UUID("20000000-0000-4000-8000-000000000001"),
        workspace_id=UUID("00000000-0000-4000-8000-000000000001"),
        underlying_id=UNDERLYING_ID,
        trading_venue_id=VENUE_ID,
        ticker="SIE",
        currency_code="EUR",
        lifecycle_status=LifecycleStatus.ACTIVE,
        is_primary=primary,
        version=1,
        created_at=NOW,
        updated_at=NOW,
        data_origin=DataOrigin.MANUAL,
    )


def test_search_delegates_filters_and_returns_pagination_contract() -> None:
    service = AsyncMock()
    service.search.return_value = ([model()], 1)
    application = create_application(settings())
    application.dependency_overrides[get_underlying_service] = lambda: service

    with TestClient(application) as client:
        response = client.get(
            "/api/v1/underlyings?q=Siemens&lifecycle_status=ACTIVE&offset=5&limit=10"
        )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["offset"] == 5
    command = service.search.await_args.args[0]
    assert command.query == "Siemens"
    assert command.lifecycle_status is LifecycleStatus.ACTIVE
    assert command.offset == 5
    assert command.limit == 10


def test_status_routes_delegate_version_and_actor() -> None:
    service = AsyncMock()
    service.verify.return_value = model()
    service.deactivate.return_value = model()
    service.reactivate.return_value = model()
    application = create_application(settings())
    application.dependency_overrides[get_underlying_service] = lambda: service

    with TestClient(application) as client:
        for operation in ("verify", "deactivate", "reactivate"):
            response = client.post(
                f"/api/v1/underlyings/{UNDERLYING_ID}/{operation}",
                headers={"X-Actor-ID": "user-2", "X-Actor-Name": "Operator"},
                json={"version": 4},
            )
            assert response.status_code == 200

    for operation in ("verify", "deactivate", "reactivate"):
        command = getattr(service, operation).await_args.args[0]
        assert command.expected_version == 4
        assert command.actor.id == "user-2"
        assert command.actor.display_name == "Operator"


def test_delete_delegates_and_returns_204() -> None:
    service = AsyncMock()
    application = create_application(settings())
    application.dependency_overrides[get_underlying_service] = lambda: service

    with TestClient(application) as client:
        response = client.delete(f"/api/v1/underlyings/{UNDERLYING_ID}?version=3")

    assert response.status_code == 204
    command = service.delete.await_args.args[0]
    assert command.underlying_id == UNDERLYING_ID
    assert command.expected_version == 3


def test_update_listing_and_set_primary_delegate_typed_commands() -> None:
    service = AsyncMock()
    service.update.return_value = listing_model()
    service.set_primary.return_value = listing_model(primary=True)
    application = create_application(settings())
    application.dependency_overrides[get_listing_service] = lambda: service
    listing_id = UUID("20000000-0000-4000-8000-000000000001")

    with TestClient(application) as client:
        updated = client.patch(
            f"/api/v1/underlyings/{UNDERLYING_ID}/listings/{listing_id}",
            json={"version": 1, "ticker": "SIE2"},
        )
        primary = client.put(
            f"/api/v1/underlyings/{UNDERLYING_ID}/primary-listing/{listing_id}",
            json={"version": 2},
        )

    assert updated.status_code == 200
    assert primary.status_code == 200
    update_command = service.update.await_args.args[0]
    assert update_command.ticker == "SIE2"
    assert update_command.currency_code is None
    primary_command = service.set_primary.await_args.args[0]
    assert primary_command.expected_listing_version == 2


def test_reference_data_routes_return_controlled_lists() -> None:
    reference_service = AsyncMock()
    reference_service.list_active_trading_venues.return_value = [
        TradingVenueModel(
            id=VENUE_ID,
            mic="XETR",
            name="Xetra",
            country_code="DE",
            timezone="Europe/Berlin",
            is_active=True,
            reference_version="FT-001-V1",
            created_at=NOW,
            updated_at=NOW,
        )
    ]
    reference_service.list_active_currencies.return_value = [
        CurrencyModel(
            code="EUR",
            name="Euro",
            minor_unit=2,
            is_active=True,
            reference_version="FT-001-V1",
            created_at=NOW,
            updated_at=NOW,
        )
    ]
    application = create_application(settings())
    application.dependency_overrides[get_reference_data_service] = lambda: reference_service

    with TestClient(application) as client:
        venues = client.get("/api/v1/market-reference-data/trading-venues")
        currencies = client.get("/api/v1/market-reference-data/currencies")

    assert venues.status_code == 200
    assert venues.json()["items"][0]["mic"] == "XETR"
    assert currencies.status_code == 200
    assert currencies.json()["items"][0]["code"] == "EUR"


def test_delete_conflict_exposes_usage_references() -> None:
    service = AsyncMock()
    service.delete.side_effect = UnderlyingDeleteReferenced(
        "Referenced underlying cannot be deleted",
        references=(UsageReference("WARRANT", UUID("40000000-0000-4000-8000-000000000001")),),
    )
    application = create_application(settings())
    application.dependency_overrides[get_underlying_service] = lambda: service

    with TestClient(application) as client:
        response = client.delete(f"/api/v1/underlyings/{UNDERLYING_ID}?version=1")

    assert response.status_code == 409
    detail = response.json()["details"][0]
    assert detail["context"]["reference_type"] == "WARRANT"


def test_domain_rule_violation_and_value_error_map_to_422() -> None:
    service = AsyncMock()
    application = create_application(settings())
    application.dependency_overrides[get_listing_service] = lambda: service
    service.add.side_effect = ValueError("Inactive listing cannot become primary")

    with TestClient(application) as client:
        response = client.post(
            f"/api/v1/underlyings/{UNDERLYING_ID}/listings",
            json={
                "trading_venue_id": str(VENUE_ID),
                "ticker": "SIE",
                "currency_code": "EUR",
                "is_primary": True,
            },
        )

    assert response.status_code == 422
    assert response.json()["code"] == "REQUEST_VALIDATION_ERROR"


def test_search_forwards_market_and_currency_filters() -> None:
    service = AsyncMock()
    service.search.return_value = ([], 0)
    application = create_application(settings())
    application.dependency_overrides[get_underlying_service] = lambda: service

    with TestClient(application) as client:
        response = client.get(f"/api/v1/underlyings?trading_venue_id={VENUE_ID}&currency_code=eur")

    assert response.status_code == 200
    query = service.search.await_args.args[0]
    assert query.trading_venue_id == VENUE_ID
    assert query.currency_code == "EUR"


def test_audit_history_endpoint_is_paginated() -> None:
    service = AsyncMock()
    service.audit_history.return_value = ((), 0)
    application = create_application(settings())
    application.dependency_overrides[get_underlying_service] = lambda: service

    with TestClient(application) as client:
        response = client.get(f"/api/v1/underlyings/{UNDERLYING_ID}/audit-events?offset=5&limit=10")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "offset": 5, "limit": 10}
    service.audit_history.assert_awaited_once_with(
        UUID("00000000-0000-4000-8000-000000000001"),
        UNDERLYING_ID,
        offset=5,
        limit=10,
    )


def test_usage_endpoint_uses_service_read_model() -> None:
    object_id = UUID("30000000-0000-4000-8000-000000000001")
    service = AsyncMock()
    service.usages.return_value = (UsageSummary("trade", 1, (object_id,)),)
    application = create_application(settings())
    application.dependency_overrides[get_underlying_service] = lambda: service

    with TestClient(application) as client:
        response = client.get(f"/api/v1/underlyings/{UNDERLYING_ID}/usages")

    assert response.status_code == 200
    assert response.json()["items"][0] == {
        "usage_type": "trade",
        "count": 1,
        "object_ids": [str(object_id)],
    }
