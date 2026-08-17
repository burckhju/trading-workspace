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
from app.features.trade_position.domain.enums import (
    ExecutionSide,
    TradeManagementEventType,
    TradeOrigin,
)
from app.features.trade_position.domain.management import TradeManagementState
from app.features.trade_position.domain.timeline import (
    Ft011Eligibility,
    TradeTimelineEntry,
    TradeTimelineEntryKind,
)
from app.features.trade_position.domain.models import (
    ExecutionRecord,
    Position,
    Trade,
    TradeManagementEvent,
)

NOW = datetime(2026, 8, 17, 8, 0, tzinfo=UTC)


class FakeService:
    def __init__(self) -> None:
        self.record_initial_purchase = AsyncMock()
        self.record_external_purchase = AsyncMock()
        self.record_additional_purchase = AsyncMock()
        self.record_sale = AsyncMock()
        self.change_stop = AsyncMock()
        self.change_target = AsyncMock()
        self.update_thesis = AsyncMock()
        self.add_management_note = AsyncMock()
        self.get_management_state = AsyncMock()
        self.get_position = AsyncMock()
        self.correct_execution = AsyncMock()
        self.correct_management_event = AsyncMock()
        self.get_trade_timeline = AsyncMock()
        self.get_ft011_eligibility = AsyncMock()


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
        trade_plan_version_id=(uuid4() if origin is TradeOrigin.WORKSPACE_SELECTION else None),
        product_selection_id=(
            product_selection_id if origin is TradeOrigin.WORKSPACE_SELECTION else None
        ),
        product_evaluation_id=(uuid4() if origin is TradeOrigin.WORKSPACE_SELECTION else None),
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

    trade, _first, position = _initial_result(
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
    service.record_initial_purchase.side_effect = ValueError("product selection not found")

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


def test_sale_returns_sell_execution_and_partial_position() -> None:
    service = FakeService()
    trade, _buy, position = _initial_result(origin=TradeOrigin.EXTERNAL)
    sale = ExecutionRecord(
        id=uuid4(),
        trade_id=trade.id,
        product_id=trade.product_id,
        side=ExecutionSide.SELL,
        quantity=100,
        price_per_unit=Decimal("2.80"),
        executed_at=NOW,
        recorded_at=NOW,
        recorded_by=uuid4(),
    )
    updated = Position(
        id=position.id,
        trade_id=position.trade_id,
        product_id=position.product_id,
        open_quantity=300,
        cost_basis=Decimal("744.00"),
        average_entry_price=Decimal("2.48"),
        realized_gross_pnl=Decimal("32.00"),
        opened_at=position.opened_at,
        last_execution_at=NOW,
    )
    service.record_sale.return_value = sale, updated
    client = TestClient(_app(service))

    response = client.post(
        f"/api/v1/trade-position/trades/{trade.id}/sales",
        json={
            "quantity": 100,
            "price_per_unit": "2.80",
            "executed_at": NOW.isoformat(),
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["execution"]["side"] == "SELL"
    assert body["position"]["open_quantity"] == 300
    assert Decimal(body["position"]["realized_gross_pnl"]) == Decimal("32.00")
    assert body["position"]["is_closed"] is False


def test_sale_full_exit_exposes_closed_position() -> None:
    service = FakeService()
    trade, _buy, position = _initial_result(origin=TradeOrigin.EXTERNAL)
    sale = ExecutionRecord(
        id=uuid4(),
        trade_id=trade.id,
        product_id=trade.product_id,
        side=ExecutionSide.SELL,
        quantity=400,
        price_per_unit=Decimal("2.60"),
        executed_at=NOW,
        recorded_at=NOW,
        recorded_by=uuid4(),
    )
    updated = Position(
        id=position.id,
        trade_id=position.trade_id,
        product_id=position.product_id,
        open_quantity=0,
        cost_basis=Decimal("0"),
        average_entry_price=Decimal("2.48"),
        realized_gross_pnl=Decimal("48.00"),
        opened_at=position.opened_at,
        last_execution_at=NOW,
        closed_at=NOW,
    )
    service.record_sale.return_value = sale, updated
    client = TestClient(_app(service))

    response = client.post(
        f"/api/v1/trade-position/trades/{trade.id}/sales",
        json={"quantity": 400, "price_per_unit": "2.60"},
    )

    assert response.status_code == 201
    assert response.json()["position"]["is_closed"] is True
    assert response.json()["position"]["closed_at"] == NOW.isoformat().replace("+00:00", "Z")


def test_sale_domain_validation_translates_to_422() -> None:
    service = FakeService()
    trade_id = uuid4()
    service.record_sale.side_effect = ValueError("SELL quantity exceeds current open quantity")
    client = TestClient(_app(service))

    response = client.post(
        f"/api/v1/trade-position/trades/{trade_id}/sales",
        json={"quantity": 999, "price_per_unit": "2.60"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "SELL quantity exceeds current open quantity"


@pytest.mark.parametrize(
    ("path", "method_name", "payload", "event_type", "value"),
    [
        ("stop", "change_stop", {"price": "1.10"}, TradeManagementEventType.STOP_CHANGED, Decimal("1.10")),
        ("target", "change_target", {"price": "2.50"}, TradeManagementEventType.TARGET_CHANGED, Decimal("2.50")),
    ],
)
def test_price_management_commands_are_exposed(
    path: str,
    method_name: str,
    payload: dict[str, str],
    event_type: TradeManagementEventType,
    value: Decimal,
) -> None:
    service = FakeService()
    trade_id = uuid4()
    event = TradeManagementEvent(
        id=uuid4(),
        trade_id=trade_id,
        event_type=event_type,
        effective_at=NOW,
        recorded_at=NOW,
        recorded_by=LOCAL_ACTOR_ID,
        numeric_value=value,
    )
    getattr(service, method_name).return_value = event
    client = TestClient(_app(service))

    response = client.post(
        f"/api/v1/trade-position/trades/{trade_id}/management/{path}",
        json={"price": str(value), "effective_at": NOW.isoformat()},
    )

    assert response.status_code == 201
    assert response.json()["event_type"] == event_type.value
    assert Decimal(response.json()["numeric_value"]) == value


@pytest.mark.parametrize(
    ("path", "method_name", "event_type"),
    [
        ("thesis", "update_thesis", TradeManagementEventType.THESIS_UPDATED),
        ("notes", "add_management_note", TradeManagementEventType.MANAGEMENT_NOTE),
    ],
)
def test_text_management_commands_are_exposed(
    path: str,
    method_name: str,
    event_type: TradeManagementEventType,
) -> None:
    service = FakeService()
    trade_id = uuid4()
    event = TradeManagementEvent(
        id=uuid4(),
        trade_id=trade_id,
        event_type=event_type,
        effective_at=NOW,
        recorded_at=NOW,
        recorded_by=LOCAL_ACTOR_ID,
        text_value="updated context",
    )
    getattr(service, method_name).return_value = event
    client = TestClient(_app(service))

    response = client.post(
        f"/api/v1/trade-position/trades/{trade_id}/management/{path}",
        json={"text": "updated context", "effective_at": NOW.isoformat()},
    )

    assert response.status_code == 201
    assert response.json()["text_value"] == "updated context"


def test_management_state_is_readable() -> None:
    service = FakeService()
    trade_id = uuid4()
    service.get_management_state.return_value = TradeManagementState(
        trade_id=trade_id,
        stop_price=Decimal("1.10"),
        target_price=Decimal("2.50"),
        thesis="trend intact",
        notes=("note 1",),
        last_event_at=NOW,
    )
    client = TestClient(_app(service))

    response = client.get(
        f"/api/v1/trade-position/trades/{trade_id}/management",
    )

    assert response.status_code == 200
    body = response.json()
    assert Decimal(body["stop_price"]) == Decimal("1.10")
    assert body["notes"] == ["note 1"]


def test_position_state_is_readable() -> None:
    service = FakeService()
    trade, _buy, position = _initial_result(origin=TradeOrigin.EXTERNAL)
    service.get_position.return_value = position
    client = TestClient(_app(service))

    response = client.get(
        f"/api/v1/trade-position/trades/{trade.id}/position",
    )

    assert response.status_code == 200
    assert response.json()["open_quantity"] == 400
    assert response.json()["is_closed"] is False
    service.get_position.assert_awaited_once_with(
        workspace_id=WORKSPACE_ID,
        trade_id=trade.id,
    )


def test_execution_correction_endpoint_returns_reprojected_position() -> None:
    service = FakeService()
    trade, original, position = _initial_result(origin=TradeOrigin.EXTERNAL)
    replacement = ExecutionRecord(
        id=uuid4(),
        trade_id=trade.id,
        product_id=trade.product_id,
        side=ExecutionSide.BUY,
        quantity=300,
        price_per_unit=Decimal("2.40"),
        executed_at=NOW,
        recorded_at=NOW,
        recorded_by=LOCAL_ACTOR_ID,
        supersedes_execution_id=original.id,
    )
    corrected = Position(
        id=position.id,
        trade_id=position.trade_id,
        product_id=position.product_id,
        open_quantity=300,
        cost_basis=Decimal("720.00"),
        average_entry_price=Decimal("2.40"),
        opened_at=NOW,
        last_execution_at=NOW,
    )
    service.correct_execution.return_value = replacement, corrected
    client = TestClient(_app(service))

    response = client.post(
        f"/api/v1/trade-position/trades/{trade.id}/executions/{original.id}/corrections",
        json={
            "side": "BUY",
            "quantity": 300,
            "price_per_unit": "2.40",
            "executed_at": NOW.isoformat(),
        },
    )

    assert response.status_code == 201
    assert response.json()["execution"]["side"] == "BUY"
    assert response.json()["position"]["open_quantity"] == 300
    service.correct_execution.assert_awaited_once()


def test_management_correction_endpoint_preserves_event_type_server_side() -> None:
    service = FakeService()
    trade_id = uuid4()
    event_id = uuid4()
    replacement = TradeManagementEvent(
        id=uuid4(),
        trade_id=trade_id,
        event_type=TradeManagementEventType.STOP_CHANGED,
        effective_at=NOW,
        recorded_at=NOW,
        recorded_by=LOCAL_ACTOR_ID,
        numeric_value=Decimal("1.70"),
        supersedes_event_id=event_id,
    )
    service.correct_management_event.return_value = replacement
    client = TestClient(_app(service))

    response = client.post(
        f"/api/v1/trade-position/trades/{trade_id}/management/{event_id}/corrections",
        json={"effective_at": NOW.isoformat(), "numeric_value": "1.70"},
    )

    assert response.status_code == 201
    assert response.json()["event_type"] == "STOP_CHANGED"
    assert response.json()["supersedes_event_id"] == str(event_id)


def test_trade_timeline_keeps_sale_as_execution_only() -> None:
    service = FakeService()
    trade_id = uuid4()
    sale_id = uuid4()
    service.get_trade_timeline.return_value = [
        TradeTimelineEntry(
            id=sale_id,
            trade_id=trade_id,
            occurred_at=NOW,
            recorded_at=NOW,
            kind=TradeTimelineEntryKind.EXECUTION,
            execution_side=ExecutionSide.SELL,
            quantity=5,
            price_per_unit=Decimal("2.50"),
        )
    ]
    client = TestClient(_app(service))

    response = client.get(f"/api/v1/trade-position/trades/{trade_id}/timeline")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": str(sale_id),
            "trade_id": str(trade_id),
            "occurred_at": NOW.isoformat().replace("+00:00", "Z"),
            "recorded_at": NOW.isoformat().replace("+00:00", "Z"),
            "kind": "EXECUTION",
            "execution_side": "SELL",
            "management_event_type": None,
            "quantity": 5,
            "price_per_unit": "2.50",
            "numeric_value": None,
            "text_value": None,
            "supersedes_id": None,
        }
    ]


@pytest.mark.parametrize(
    ("eligible", "reason"),
    [
        (False, "trade position still has open quantity"),
        (True, "trade position is fully closed"),
    ],
)
def test_ft011_eligibility_endpoint(eligible: bool, reason: str) -> None:
    service = FakeService()
    trade_id = uuid4()
    service.get_ft011_eligibility.return_value = Ft011Eligibility(
        trade_id=trade_id,
        eligible=eligible,
        reason=reason,
    )
    client = TestClient(_app(service))

    response = client.get(
        f"/api/v1/trade-position/trades/{trade_id}/ft011-eligibility",
    )

    assert response.status_code == 200
    assert response.json() == {
        "trade_id": str(trade_id),
        "eligible": eligible,
        "reason": reason,
    }
