from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from test_trade_link_api import _make_app

from app.features.learning.api.dependencies import get_execute_as_trade_service
from app.features.learning.application.execute_as_trade_service import ExecuteAsTradeResult


class FakeExecuteAsTradeService:
    def __init__(self) -> None:
        self.calls = 0
        self.trade_id = uuid4()
        self.trade_link_id = uuid4()

    async def execute(self, **kwargs):
        del kwargs
        self.calls += 1
        return ExecuteAsTradeResult(
            trade_id=self.trade_id,
            trade_link_id=self.trade_link_id,
            replayed=self.calls > 1,
        )


def test_execute_as_trade_first_call_and_replay() -> None:
    service = FakeExecuteAsTradeService()
    app = _make_app()
    app.dependency_overrides[get_execute_as_trade_service] = lambda: service
    client = TestClient(app)
    observation_id = uuid4()
    payload = {
        "quantity": 2,
        "price_per_unit": "11.25",
        "executed_at": datetime(2026, 8, 23, tzinfo=UTC).isoformat(),
    }
    headers = {"Idempotency-Key": "exec-api-1"}
    first = client.post(
        f"/api/v1/learning/external-observations/{observation_id}/execute-as-trade",
        json=payload,
        headers=headers,
    )
    assert first.status_code == 201
    assert first.json()["replayed"] is False
    replay = client.post(
        f"/api/v1/learning/external-observations/{observation_id}/execute-as-trade",
        json=payload,
        headers=headers,
    )
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert replay.json()["trade_id"] == first.json()["trade_id"]
    assert replay.json()["trade_link_id"] == first.json()["trade_link_id"]
