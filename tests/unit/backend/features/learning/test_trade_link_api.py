from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.features.learning.api.dependencies import (
    get_trade_link_projection_service,
    get_trade_link_service,
)
from app.features.learning.application.trade_link_projection_service import (
    TradeLinkCurrentSourceCompatibility,
    TradeLinkProjection,
    TradeLinkSourceState,
)
from app.features.learning.application.trade_link_service import (
    TradeLinkErrorCode,
    TradeLinkServiceError,
)
from app.features.learning.domain import (
    ExternalObservationTradeLink,
    ExternalObservationTradeLinkVersion,
    TradeLinkChangeReason,
    TradeLinkStatus,
)

NOW = datetime(2026, 8, 23, tzinfo=UTC)


def _make_app():
    if hasattr(main_module, "create_app"):
        return main_module.create_app()
    if hasattr(main_module, "create_application"):
        return main_module.create_application()
    if hasattr(main_module, "app"):
        return main_module.app
    if hasattr(main_module, "application"):
        return main_module.application
    raise RuntimeError("FastAPI application entry point not found in app.main")


class FakeService:
    def __init__(self, *, result=None, error=None) -> None:
        self.result = result
        self.error = error

    async def create(self, **kwargs):
        del kwargs
        if self.error:
            raise self.error
        return self.result

    async def correct_target(self, **kwargs):
        del kwargs
        if self.error:
            raise self.error
        return self.result

    async def retract(self, **kwargs):
        del kwargs
        if self.error:
            raise self.error
        return self.result

    async def reactivate(self, **kwargs):
        del kwargs
        if self.error:
            raise self.error
        return self.result

    async def revalidate_source(self, **kwargs):
        del kwargs
        if self.error:
            raise self.error
        return self.result


class FakeProjection:
    def __init__(self, projection) -> None:
        self.projection = projection

    async def get(self, **kwargs):
        del kwargs
        return self.projection


def _projection():
    link_id = uuid4()
    observation_id = uuid4()
    version_id = uuid4()
    link = ExternalObservationTradeLink(
        id=link_id,
        workspace_id=uuid4(),
        external_observation_id=observation_id,
        current_version_id=version_id,
        created_at=NOW,
        created_by=uuid4(),
    )
    version = ExternalObservationTradeLinkVersion(
        id=version_id,
        external_observation_trade_link_id=link_id,
        version=1,
        external_observation_version_id=uuid4(),
        trade_id=uuid4(),
        status=TradeLinkStatus.ACTIVE,
        change_reason=TradeLinkChangeReason.INITIAL_LINK,
        created_at=NOW,
        created_by=uuid4(),
    )
    return TradeLinkProjection(
        link=link,
        version=version,
        source_state=TradeLinkSourceState.CURRENT_SOURCE,
        current_source_compatibility=(TradeLinkCurrentSourceCompatibility.COMPATIBLE),
    )


def test_create_trade_link_returns_contract_response() -> None:
    projection = _projection()
    app = _make_app()
    app.dependency_overrides[get_trade_link_service] = lambda: FakeService(
        result=projection.version
    )
    app.dependency_overrides[get_trade_link_projection_service] = lambda: FakeProjection(projection)

    client = TestClient(app)
    response = client.post(
        f"/api/v1/learning/external-observations/{projection.link.external_observation_id}/trade-links",
        json={"trade_id": str(projection.version.trade_id)},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["trade_link_id"] == str(projection.link.id)
    assert body["source_state"] == "CURRENT_SOURCE"
    assert body["current_source_compatibility"] == "COMPATIBLE"


@pytest.mark.parametrize(
    ("code", "expected_status"),
    [
        (TradeLinkErrorCode.TRADE_LINK_NOT_FOUND, 404),
        (TradeLinkErrorCode.TRADE_LINK_TARGET_NOT_FOUND, 404),
        (TradeLinkErrorCode.TRADE_LINK_ACTIVE_PAIR_ALREADY_EXISTS, 409),
        (TradeLinkErrorCode.TRADE_LINK_INVALID_TRANSITION, 409),
        (TradeLinkErrorCode.TRADE_LINK_SOURCE_NOT_CURRENT, 409),
        (TradeLinkErrorCode.TRADE_LINK_TARGET_NOT_EXTERNAL, 422),
        (TradeLinkErrorCode.TRADE_LINK_WORKSPACE_MISMATCH, 422),
        (TradeLinkErrorCode.TRADE_LINK_PRODUCT_MISMATCH, 422),
        (TradeLinkErrorCode.TRADE_LINK_UNDERLYING_MISMATCH, 422),
        (TradeLinkErrorCode.TRADE_LINK_SOURCE_INCOMPATIBLE, 422),
    ],
)
def test_trade_link_error_mapping(code, expected_status) -> None:
    projection = _projection()
    app = _make_app()
    app.dependency_overrides[get_trade_link_service] = lambda: FakeService(
        error=TradeLinkServiceError(code, "boom")
    )
    app.dependency_overrides[get_trade_link_projection_service] = lambda: FakeProjection(projection)

    client = TestClient(app)
    response = client.post(
        f"/api/v1/learning/external-observations/{projection.link.external_observation_id}/trade-links",
        json={"trade_id": str(projection.version.trade_id)},
    )

    assert response.status_code == expected_status
    assert response.json()["code"] == code.value
