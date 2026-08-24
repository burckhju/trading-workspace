from __future__ import annotations

from fastapi.testclient import TestClient
from test_trade_link_api import _make_app, _projection

from app.features.learning.api.dependencies import get_trade_link_query_service
from app.features.learning.application.trade_link_projection_service import (
    TradeLinkCurrentSourceCompatibility,
    TradeLinkSourceState,
)
from app.features.learning.application.trade_link_query_service import (
    TradeLinkHistoryEntry,
)


class FakeQuery:
    def __init__(self, projection) -> None:
        self.projection = projection

    async def get(self, **kwargs):
        del kwargs
        return self.projection

    async def list_for_observation(self, **kwargs):
        del kwargs
        return (self.projection,)

    async def history(self, **kwargs):
        del kwargs
        return (
            TradeLinkHistoryEntry(
                version=self.projection.version,
                source_state=TradeLinkSourceState.CURRENT_SOURCE,
                current_source_compatibility=(TradeLinkCurrentSourceCompatibility.COMPATIBLE),
            ),
        )


def test_get_trade_link_detail() -> None:
    projection = _projection()
    app = _make_app()
    app.dependency_overrides[get_trade_link_query_service] = lambda: FakeQuery(projection)
    response = TestClient(app).get(f"/api/v1/learning/trade-links/{projection.link.id}")
    assert response.status_code == 200
    assert response.json()["trade_link_id"] == str(projection.link.id)


def test_list_trade_links_for_observation() -> None:
    projection = _projection()
    app = _make_app()
    app.dependency_overrides[get_trade_link_query_service] = lambda: FakeQuery(projection)
    response = TestClient(app).get(
        f"/api/v1/learning/external-observations/"
        f"{projection.link.external_observation_id}/trade-links"
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_trade_link_history() -> None:
    projection = _projection()
    app = _make_app()
    app.dependency_overrides[get_trade_link_query_service] = lambda: FakeQuery(projection)
    response = TestClient(app).get(f"/api/v1/learning/trade-links/{projection.link.id}/history")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["version"] == 1
    assert body[0]["source_state"] == "CURRENT_SOURCE"
