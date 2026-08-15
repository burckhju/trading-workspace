from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Environment, Settings
from app.features.market.api.dependencies import (
    get_issuer_administration_service,
    get_reference_data_service,
)
from app.features.market.persistence.models import IssuerModel
from app.features.market.service.errors import (
    DuplicateIssuerLei,
    IssuerConcurrentModification,
    IssuerNotFound,
)
from app.main import create_application

NOW = datetime(2026, 8, 15, 6, 0, tzinfo=UTC)
ISSUER_ID = UUID("50000000-0000-4000-8000-000000000001")


def _override(value: object):
    return lambda: value


def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment=Environment.TEST,
        documentation_enabled=True,
        log_level="CRITICAL",
    )


def issuer(*, active: bool = True, version: int = 1) -> IssuerModel:
    return IssuerModel(
        id=ISSUER_ID,
        legal_name="Société Générale S.A.",
        display_name="Société Générale",
        country_code="FR",
        lei="O2RNE8IBXP4R0TD8PU41",
        is_active=active,
        version=version,
        created_at=NOW,
        updated_at=NOW,
    )


def test_consumer_list_exposes_active_business_reference_data_only() -> None:
    service = AsyncMock()
    service.list_active_issuers.return_value = [issuer()]
    application = create_application(settings())
    application.dependency_overrides[get_reference_data_service] = _override(service)

    with TestClient(application) as client:
        response = client.get("/api/v1/market-reference-data/issuers")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["display_name"] == "Société Générale"
    assert "version" not in item
    assert "is_active" not in item
    service.list_active_issuers.assert_awaited_once_with()


def test_admin_list_includes_lifecycle_and_concurrency_metadata() -> None:
    service = AsyncMock()
    service.list_issuers.return_value = [issuer(active=False, version=3)]
    application = create_application(settings())
    application.dependency_overrides[get_reference_data_service] = _override(service)

    with TestClient(application) as client:
        response = client.get("/api/v1/market-reference-data/issuers/admin")

    assert response.status_code == 200
    assert response.json()["items"][0]["is_active"] is False
    assert response.json()["items"][0]["version"] == 3


def test_create_issuer_delegates_minimal_admin_input() -> None:
    service = AsyncMock()
    service.create.return_value = issuer()
    application = create_application(settings())
    application.dependency_overrides[get_issuer_administration_service] = _override(service)

    with TestClient(application) as client:
        response = client.post(
            "/api/v1/market-reference-data/issuers",
            headers={"X-Actor-ID": "admin-1", "X-Actor-Name": "Reference Admin"},
            json={
                "legal_name": "Société Générale S.A.",
                "display_name": "Société Générale",
                "country_code": "fr",
                "lei": "o2rne8ibxp4r0td8pu41",
            },
        )

    assert response.status_code == 201
    command = service.create.await_args.args[0]
    assert command.actor.display_name == "Reference Admin"
    assert command.country_code == "fr"
    assert command.lei == "o2rne8ibxp4r0td8pu41"


def test_update_preserves_omitted_optional_fields_and_allows_explicit_clear() -> None:
    service = AsyncMock()
    service.update.return_value = issuer(version=2)
    application = create_application(settings())
    application.dependency_overrides[get_issuer_administration_service] = _override(service)

    with TestClient(application) as client:
        response = client.patch(
            f"/api/v1/market-reference-data/issuers/{ISSUER_ID}",
            json={"expected_version": 1, "display_name": "SG", "lei": None},
        )

    assert response.status_code == 200
    command = service.update.await_args.args[0]
    assert command.display_name == "SG"
    assert command.lei is None
    assert command.country_code is ...


def test_deactivate_and_reactivate_are_explicit_admin_operations() -> None:
    service = AsyncMock()
    service.deactivate.return_value = issuer(active=False, version=2)
    service.reactivate.return_value = issuer(active=True, version=3)
    application = create_application(settings())
    application.dependency_overrides[get_issuer_administration_service] = _override(service)

    with TestClient(application) as client:
        deactivated = client.post(
            f"/api/v1/market-reference-data/issuers/{ISSUER_ID}/deactivate",
            json={"expected_version": 1},
        )
        reactivated = client.post(
            f"/api/v1/market-reference-data/issuers/{ISSUER_ID}/reactivate",
            json={"expected_version": 2},
        )

    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert reactivated.status_code == 200
    assert reactivated.json()["is_active"] is True


def test_issuer_errors_map_to_stable_http_contract() -> None:
    cases = [
        (IssuerNotFound("missing"), 404, "ISSUER_NOT_FOUND"),
        (DuplicateIssuerLei("duplicate", field="lei"), 409, "ISSUER_DUPLICATE_LEI"),
        (
            IssuerConcurrentModification("stale", field="expected_version"),
            409,
            "ISSUER_CONCURRENT_MODIFICATION",
        ),
    ]
    for error, expected_status, expected_code in cases:
        service = AsyncMock()
        service.create.side_effect = error
        application = create_application(settings())
        application.dependency_overrides[get_issuer_administration_service] = _override(service)
        with TestClient(application) as client:
            response = client.post(
                "/api/v1/market-reference-data/issuers",
                json={"legal_name": "Issuer AG", "display_name": "Issuer"},
            )
        assert response.status_code == expected_status
        assert response.json()["code"] == expected_code
