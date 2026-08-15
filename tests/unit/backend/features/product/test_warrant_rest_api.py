from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import Environment, Settings
from app.features.product.api.router import service
from app.features.product.domain.models import (
    OptionDirection,
    ProductFamily,
    WarrantLifecycle,
)
from app.features.product.persistence.models import (
    WarrantModel,
    WarrantTermsVersionModel,
)
from app.features.product.service.errors import (
    DuplicateWarrantIsin,
    DuplicateWarrantListing,
    WarrantConcurrentModification,
    WarrantNotFound,
)
from app.main import create_application

NOW = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)
WARRANT_ID = UUID("60000000-0000-4000-8000-000000000001")
ISSUER_ID = UUID("50000000-0000-4000-8000-000000000001")
UNDERLYING_ID = UUID("10000000-0000-4000-8000-000000000001")


def settings() -> Settings:
    return Settings(
        _env_file=None,
        environment=Environment.TEST,
        documentation_enabled=True,
        log_level="CRITICAL",
    )


def warrant(*, version: int = 1) -> WarrantModel:
    return WarrantModel(
        id=WARRANT_ID,
        workspace_id=UUID("00000000-0000-4000-8000-000000000001"),
        issuer_id=ISSUER_ID,
        underlying_id=UNDERLYING_ID,
        product_family=ProductFamily.WARRANT,
        display_name="Siemens Call 180",
        isin="DE000TEST001",
        wkn="TEST01",
        lifecycle_status=WarrantLifecycle.ACTIVE,
        version=version,
        created_at=NOW,
        updated_at=NOW,
    )


def terms() -> WarrantTermsVersionModel:
    return WarrantTermsVersionModel(
        id=UUID("61000000-0000-4000-8000-000000000001"),
        warrant_id=WARRANT_ID,
        version_no=2,
        effective_from=NOW,
        effective_to=None,
        option_direction=OptionDirection.CALL,
        strike=Decimal("180"),
        maturity_date=date(2026, 12, 18),
        ratio=Decimal("0.1"),
        created_at=NOW,
    )


def service_override(value: AsyncMock):
    def override():
        return value

    return override


def test_terms_update_requires_and_delegates_expected_version() -> None:
    svc = AsyncMock()
    svc.add_terms_version.return_value = terms()
    app = create_application(settings())
    app.dependency_overrides[service] = service_override(svc)
    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/warrants/{WARRANT_ID}/terms",
            json={
                "expected_version": 3,
                "option_direction": "CALL",
                "strike": "180",
                "maturity_date": "2026-12-18",
                "ratio": "0.1",
            },
        )
    assert response.status_code == 201
    assert svc.add_terms_version.await_args.kwargs["expected_version"] == 3


def test_product_errors_use_stable_http_conflict_contract() -> None:
    cases = [
        (WarrantNotFound("missing"), 404, "WARRANT_NOT_FOUND"),
        (
            DuplicateWarrantIsin("duplicate", field="isin"),
            409,
            "WARRANT_DUPLICATE_ISIN",
        ),
        (
            DuplicateWarrantListing("duplicate", field="symbol"),
            409,
            "WARRANT_LISTING_DUPLICATE",
        ),
        (
            WarrantConcurrentModification("stale", field="expected_version"),
            409,
            "WARRANT_CONCURRENT_MODIFICATION",
        ),
    ]
    for error, status_code, code in cases:
        svc = AsyncMock()
        svc.create.side_effect = error
        app = create_application(settings())
        app.dependency_overrides[service] = service_override(svc)
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/warrants",
                json={
                    "issuer_id": str(ISSUER_ID),
                    "underlying_id": str(UNDERLYING_ID),
                    "display_name": "Test",
                    "isin": "DE000TEST001",
                    "wkn": None,
                    "option_direction": "CALL",
                    "strike": "100",
                    "maturity_date": "2027-01-01",
                    "ratio": "0.1",
                },
            )
        assert response.status_code == status_code
        assert response.json()["code"] == code
