"""REST tests for FT-012 handoff exposure."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.features.post_trade.api.dependencies import (
    get_ft012_handoff_service,
)
from app.features.post_trade.api.router import router
from app.features.post_trade.application.handoff_service import (
    Ft012Handoff,
)


def test_handoff_endpoint_exposes_ready_state() -> None:
    trade_id = uuid4()

    service = MagicMock()
    service.get = AsyncMock(
        return_value=Ft012Handoff(
            ready=True,
            reason="READY",
            post_trade_observation_id=uuid4(),
            exit_review_id=uuid4(),
            exit_review_version_id=uuid4(),
        )
    )

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_ft012_handoff_service] = lambda: service

    client = TestClient(app)

    response = client.get(f"/api/v1/post-trade/trades/{trade_id}/handoff")

    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert response.json()["reason"] == "READY"
