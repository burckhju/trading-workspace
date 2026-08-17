from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.features.trade_position.api.dependencies import get_trade_position_service
from app.features.trade_position.api.router import (
    LOCAL_ACTOR_ID,
    WORKSPACE_ID,
    router,
)
from app.features.trade_position.domain.enums import TradeOrigin
from app.features.trade_position.domain.models import ExecutionRecord, Position, Trade


NOW = datetime(2026, 8, 17, 8, 0, tzinfo=UTC)


class FakeService:
    def __init__(self) -> None:
        self.record_initial_purchase = AsyncMock()
        self.record_external_purchase = AsyncMock()
        self.record_additional_purchase = AsyncMock()


def _initial_result(
    *,
    origin: TradeOrigin,
    product_id: UUID | None = None,
    product_selection_id: UUID | None = None,
):
    product_id = product_id or uuid4()
    actor = uuid4()

    trade = Trade(
        id=uuid4(),
        workspace_id=WORKSPACE_ID,
        product_id=product_id,
        origin=origin,
        created_at=NOW,
        created_by=actor,
        trade_plan_id=uuid4() if origin is TradeOrigin.WORKSPACE_SELECTION else None,
        trade_plan_version_id=uuid4()
        if origin is TradeOrigin.WORKSPACE_SELECTION
        else None,
        product_selection_id=product_selection_id
        if origin is TradeOrigin.WORKSPACE_SELECTION
        else None,
        product_evaluation_id=uuid4()
        if origin is TradeOrigin.WORKSPACE_SELECTION
        else None,
    )

    execution = ExecutionRecord(
        id=uuid4(),
        trade_id=trade.id,
        product_id=trade.product_id,
        quantity=400,
        price_per_unit=Decimal("2.48"),
        executed_at=NOW,
        recorded_at=NOW,
        recorded_by=actor,
    )

    position = Position.from_execution(
        id=uuid4(),
        trade=trade,
        execution=execution,
    )

    return trade, execution, position


def _app(service: FakeService | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)

    if service is not None:
        app.dependency_overrides[get_trade_position_service] = lambda: service

    return app


def test_workspace_purchase_returns_created_trade_execution_and_position() -> None:
    service = FakeService()
    selection_id = uuid4()

    trade, execution, position = _initial_result(
        origin=TradeOrigin.WORKSPACE_SELECTION,
        product_selection_id=selection_id,
    )
    service.record_initial_purchase.return_value = (
        trade,
        execution,
        position,
    )

    client = TestClient(_app(service))

    response = client.post(
        "/api/v1/trade-position/purchases/from-selection",
        json={
            "product_selection_id": str(selection_id),
            "quantity": 400,
            "price_per_unit": "2.48",
            "executed_at": NOW.isoformat(),
        },
    )

    assert response.status_code == 201

    body = response.json()
    assert body["trade"]["id"] == str(trade.id)
    assert body["trade"]["origin"] == "WORKSPACE_SELECTION"
    assert body["execution"]["quantity"] == 400
    assert Decimal(body["execution"]["gross_amount"]) == Decimal("992.00")
    assert body["position"]["open_quantity"] == 400

    service.record_initial_purchase.assert_awaited_once_with(
        workspace_id=WORKSPACE_ID,
        product_selection_id=selection_id,
        quantity=400,
        price_per_unit=Decimal("2.48"),
        executed_at=NOW,
        actor=LOCAL_ACTOR_ID,
    )


def test_external_purchase_returns_created_trade_execution_and_position() -> None:
    service = FakeService()
    product_id = uuid4()
    actor_id = uuid4()

    trade, execution, position = _initial_result(
        origin=TradeOrigin.EXTERNAL,
        product_id=product_id,
    )
    service.record_external_purchase.return_value = (
        trade,
        execution,
        position,
    )

    client = TestClient(_app(service))

    response = client.post(
        "/api/v1/trade-position/purchases/external",
        headers={"X-Actor-ID": str(actor_id)},
        json={
            "product_id": str(product_id),
            "quantity": 100,
            "price_per_unit": "1.25",
            "executed_at": NOW.isoformat(),
        },
    )

    assert response.status_code == 201
    assert response.json()["trade"]["origin"] == "EXTERNAL"

    service.record_external_purchase.assert_awaited_once_with(
        workspace_id=WORKSPACE_ID,
        product_id=product_id,
        quantity=100,
        price_per_unit=Decimal("1.25"),
        executed_at=NOW,
        actor=actor_id,
    )


def test_additional_purchase_uses_trade_identity_from_path() -> None:
    service = FakeService()

    trade, first, position = _initial_result(
        origin=TradeOrigin.EXTERNAL,
    )
    second = ExecutionRecord(
        id=uuid4(),
        trade_id=trade.id,
        product_id=trade.product_id,
        quantity=200,
        price_per_unit=Decimal("2.70"),
        executed_at=NOW,
        recorded_at=NOW,
        recorded_by=uuid4(),
    )
    updated = position.apply_purchase(second)

    service.record_additional_purchase.return_value = second, updated

    client = TestClient(_app(service))

    response = client.post(
        f"/api/v1/trade-position/trades/{trade.id}/purchases",
        json={
            "quantity": 200,
            "price_per_unit": "2.70",
            "executed_at": NOW.isoformat(),
        },
    )

    assert response.status_code == 201
    assert response.json()["position"]["open_quantity"] == 600

    service.record_additional_purchase.assert_awaited_once_with(
        workspace_id=WORKSPACE_ID,
        trade_id=trade.id,
        quantity=200,
        price_per_unit=Decimal("2.70"),
        executed_at=NOW,
        actor=LOCAL_ACTOR_ID,
    )


@pytest.mark.parametrize("quantity", [0, -1])
def test_purchase_quantity_must_be_positive(quantity: int) -> None:
    service = FakeService()
    client = TestClient(_app(service))

    response = client.post(
        "/api/v1/trade-position/purchases/from-selection",
        json={
            "product_selection_id": str(uuid4()),
            "quantity": quantity,
            "price_per_unit": "2.48",
        },
    )

    assert response.status_code == 422
    service.record_initial_purchase.assert_not_awaited()


@pytest.mark.parametrize("price", ["0", "-1"])
def test_purchase_price_must_be_positive(price: str) -> None:
    service = FakeService()
    client = TestClient(_app(service))

    response = client.post(
        "/api/v1/trade-position/purchases/from-selection",
        json={
            "product_selection_id": str(uuid4()),
            "quantity": 1,
            "price_per_unit": price,
        },
    )

    assert response.status_code == 422
    service.record_initial_purchase.assert_not_awaited()


def test_executed_at_is_optional_and_defaults_to_current_time() -> None:
    service = FakeService()
    selection_id = uuid4()

    service.record_initial_purchase.return_value = _initial_result(
        origin=TradeOrigin.WORKSPACE_SELECTION,
        product_selection_id=selection_id,
    )

    before = datetime.now(UTC)
    client = TestClient(_app(service))

    response = client.post(
        "/api/v1/trade-position/purchases/from-selection",
        json={
            "product_selection_id": str(selection_id),
            "quantity": 1,
            "price_per_unit": "2.48",
        },
    )
    after = datetime.now(UTC)

    assert response.status_code == 201

    executed_at = service.record_initial_purchase.await_args.kwargs["executed_at"]
    assert before <= executed_at <= after


def test_unknown_product_selection_is_translated_to_404() -> None:
    service = FakeService()
    service.record_initial_purchase.side_effect = ValueError(
        "product selection not found"
    )

    client = TestClient(_app(service))

    response = client.post(
        "/api/v1/trade-position/purchases/from-selection",
        json={
            "product_selection_id": str(uuid4()),
            "quantity": 1,
            "price_per_unit": "2.48",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "product selection not found"
