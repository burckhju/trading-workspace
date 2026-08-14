from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Environment, Settings
from app.features.market.api.dependencies import (
    get_reference_data_service,
    get_trading_venue_administration_service,
)
from app.features.market.persistence.models import TradingVenueModel
from app.features.market.service.errors import (
    DuplicateTradingVenueMic,
    TradingVenueConcurrentModification,
    TradingVenueNotFound,
)
from app.main import create_application

NOW = datetime(2026, 8, 13, 12, 0, tzinfo=UTC)
VENUE_ID = UUID("30000000-0000-4000-8000-000000000001")


def _override(value: object):
    return lambda: value


def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment=Environment.TEST,
        documentation_enabled=True,
        log_level="CRITICAL",
    )


def venue(*, active: bool = True, version: int = 1) -> TradingVenueModel:
    return TradingVenueModel(
        id=VENUE_ID,
        mic="XETR",
        name="Xetra",
        country_code="DE",
        timezone="Europe/Berlin",
        is_active=active,
        reference_version="FT002_MANUAL_V1",
        version=version,
        created_at=NOW,
        updated_at=NOW,
    )


def test_create_trading_venue_delegates_minimal_admin_input() -> None:
    service = AsyncMock()
    service.create.return_value = venue()
    application = create_application(settings())
    application.dependency_overrides[get_trading_venue_administration_service] = _override(service)

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/market-reference-data/trading-venues",
            headers={"X-Actor-ID": "admin-1", "X-Actor-Name": "Reference Admin"},
            json={
                "mic": "xetr",
                "name": "Xetra",
                "country_code": "de",
                "timezone": "Europe/Berlin",
            },
        )

    assert response.status_code == 201
    assert response.json()["mic"] == "XETR"
    command = service.create.await_args.args[0]
    assert command.actor.display_name == "Reference Admin"
    assert command.mic == "xetr"
    assert not hasattr(command, "reference_version")


def test_update_does_not_allow_mic_or_reference_version() -> None:
    service = AsyncMock()
    application = create_application(settings())
    application.dependency_overrides[get_trading_venue_administration_service] = _override(service)

    with TestClient(application) as client:
        response = client.patch(
            f"/api/v1/market-reference-data/trading-venues/{VENUE_ID}",
            json={"expected_version": 1, "mic": "XFRA"},
        )

    assert response.status_code == 422
    service.update.assert_not_awaited()


def test_update_uses_expected_version_and_returns_admin_state() -> None:
    service = AsyncMock()
    service.update.return_value = venue(version=2)
    application = create_application(settings())
    application.dependency_overrides[get_trading_venue_administration_service] = _override(service)

    with TestClient(application) as client:
        response = client.patch(
            f"/api/v1/market-reference-data/trading-venues/{VENUE_ID}",
            json={"expected_version": 1, "name": "Xetra Market"},
        )

    assert response.status_code == 200
    assert response.json()["version"] == 2
    command = service.update.await_args.args[0]
    assert command.expected_version == 1
    assert command.name == "Xetra Market"


def test_deactivate_and_reactivate_are_explicit_status_mutations() -> None:
    service = AsyncMock()
    service.deactivate.return_value = venue(active=False, version=2)
    service.reactivate.return_value = venue(active=True, version=3)
    application = create_application(settings())
    application.dependency_overrides[get_trading_venue_administration_service] = _override(service)

    with TestClient(application) as client:
        deactivated = client.post(
            f"/api/v1/market-reference-data/trading-venues/{VENUE_ID}/deactivate",
            json={"expected_version": 1},
        )
        reactivated = client.post(
            f"/api/v1/market-reference-data/trading-venues/{VENUE_ID}/reactivate",
            json={"expected_version": 2},
        )

    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True


def test_trading_venue_errors_map_to_stable_http_contract() -> None:
    cases = [
        (TradingVenueNotFound("missing"), 404, "TRADING_VENUE_NOT_FOUND"),
        (DuplicateTradingVenueMic("duplicate", field="mic"), 409, "TRADING_VENUE_DUPLICATE_MIC"),
        (
            TradingVenueConcurrentModification("stale", field="expected_version"),
            409,
            "TRADING_VENUE_CONCURRENT_MODIFICATION",
        ),
    ]

    for error, expected_status, expected_code in cases:
        service = AsyncMock()
        service.create.side_effect = error
        application = create_application(settings())
        application.dependency_overrides[get_trading_venue_administration_service] = _override(
            service
        )
        with TestClient(application) as client:
            response = client.post(
                "/api/v1/market-reference-data/trading-venues",
                json={
                    "mic": "XETR",
                    "name": "Xetra",
                    "country_code": "DE",
                    "timezone": "Europe/Berlin",
                },
            )
        assert response.status_code == expected_status
        assert response.json()["code"] == expected_code


def test_consumer_read_contract_still_delegates_to_active_only_service() -> None:
    service = AsyncMock()
    service.list_active_trading_venues.return_value = [venue()]
    application = create_application(settings())
    application.dependency_overrides[get_reference_data_service] = _override(service)

    with TestClient(application) as client:
        response = client.get("/api/v1/market-reference-data/trading-venues")

    assert response.status_code == 200
    assert response.json()["items"][0]["mic"] == "XETR"
    service.list_active_trading_venues.assert_awaited_once_with()


def test_admin_read_contract_includes_inactive_and_concurrency_metadata() -> None:
    service = AsyncMock()
    service.list_trading_venues.return_value = [venue(active=False, version=3)]
    application = create_application(settings())
    application.dependency_overrides[get_reference_data_service] = _override(service)

    with TestClient(application) as client:
        response = client.get("/api/v1/market-reference-data/trading-venues/admin")

    assert response.status_code == 200
    assert response.json()["items"][0]["is_active"] is False
    assert response.json()["items"][0]["version"] == 3
    service.list_trading_venues.assert_awaited_once_with()
