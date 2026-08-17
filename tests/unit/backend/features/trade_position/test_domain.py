from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.features.trade_position.domain.enums import TradeOrigin
from app.features.trade_position.domain.models import ExecutionRecord, Position, Trade

EXECUTED_AT = datetime(2026, 8, 17, 8, 0, tzinfo=UTC)
RECORDED_AT = datetime(2026, 8, 17, 8, 1, tzinfo=UTC)


def workspace_trade() -> Trade:
    return Trade(
        id=uuid4(),
        workspace_id=uuid4(),
        product_id=uuid4(),
        origin=TradeOrigin.WORKSPACE_SELECTION,
        created_at=RECORDED_AT,
        created_by=uuid4(),
        trade_plan_id=uuid4(),
        trade_plan_version_id=uuid4(),
        product_selection_id=uuid4(),
        product_evaluation_id=uuid4(),
    )


def external_trade() -> Trade:
    return Trade(
        id=uuid4(),
        workspace_id=uuid4(),
        product_id=uuid4(),
        origin=TradeOrigin.EXTERNAL,
        created_at=RECORDED_AT,
        created_by=uuid4(),
    )


def execution(
    trade: Trade,
    *,
    quantity: int = 10,
    price: str = "5.00",
    executed_at: datetime = EXECUTED_AT,
    recorded_at: datetime | None = None,
) -> ExecutionRecord:
    effective_recorded_at = recorded_at or executed_at + timedelta(minutes=1)

    return ExecutionRecord(
        id=uuid4(),
        trade_id=trade.id,
        product_id=trade.product_id,
        quantity=quantity,
        price_per_unit=Decimal(price),
        executed_at=executed_at,
        recorded_at=effective_recorded_at,
        recorded_by=uuid4(),
    )


def test_workspace_trade_requires_selection_provenance() -> None:
    with pytest.raises(
        ValueError,
        match="workspace trade requires product selection provenance",
    ):
        Trade(
            id=uuid4(),
            workspace_id=uuid4(),
            product_id=uuid4(),
            origin=TradeOrigin.WORKSPACE_SELECTION,
            created_at=RECORDED_AT,
            created_by=uuid4(),
        )


def test_external_trade_must_not_invent_selection_provenance() -> None:
    with pytest.raises(
        ValueError,
        match="external trade must not carry product selection provenance",
    ):
        Trade(
            id=uuid4(),
            workspace_id=uuid4(),
            product_id=uuid4(),
            origin=TradeOrigin.EXTERNAL,
            created_at=RECORDED_AT,
            created_by=uuid4(),
            product_selection_id=uuid4(),
        )


@pytest.mark.parametrize("quantity", [0, -1])
def test_execution_requires_positive_quantity(quantity: int) -> None:
    trade = workspace_trade()

    with pytest.raises(ValueError, match="quantity must be positive"):
        execution(trade, quantity=quantity)


def test_execution_requires_positive_price() -> None:
    trade = workspace_trade()

    with pytest.raises(ValueError, match="price_per_unit must be positive"):
        execution(trade, price="0")


def test_execution_keeps_execution_and_recording_time_separate() -> None:
    trade = workspace_trade()
    executed_at = datetime(2026, 8, 16, 10, 30, tzinfo=UTC)
    recorded_at = datetime(2026, 8, 17, 8, 0, tzinfo=UTC)

    record = execution(
        trade,
        executed_at=executed_at,
        recorded_at=recorded_at,
    )

    assert record.executed_at == executed_at
    assert record.recorded_at == recorded_at


def test_execution_gross_amount_is_derived() -> None:
    trade = workspace_trade()

    record = execution(trade, quantity=400, price="2.48")

    assert record.gross_amount == Decimal("992.00")


def test_initial_execution_creates_position() -> None:
    trade = workspace_trade()
    first = execution(trade, quantity=400, price="2.48")

    position = Position.from_execution(
        id=uuid4(),
        trade=trade,
        execution=first,
    )

    assert position.trade_id == trade.id
    assert position.product_id == trade.product_id
    assert position.open_quantity == 400
    assert position.cost_basis == Decimal("992.00")
    assert position.average_entry_price == Decimal("2.48")
    assert position.opened_at == first.executed_at
    assert position.last_execution_at == first.executed_at


def test_additional_purchase_updates_same_position() -> None:
    trade = workspace_trade()
    first = execution(
        trade,
        quantity=400,
        price="2.48",
        executed_at=datetime(2026, 8, 17, 8, 0, tzinfo=UTC),
    )
    position = Position.from_execution(
        id=uuid4(),
        trade=trade,
        execution=first,
    )

    second = execution(
        trade,
        quantity=200,
        price="2.70",
        executed_at=datetime(2026, 8, 17, 9, 0, tzinfo=UTC),
        recorded_at=datetime(2026, 8, 17, 9, 1, tzinfo=UTC),
    )

    updated = position.apply_purchase(second)

    assert updated.id == position.id
    assert updated.trade_id == position.trade_id
    assert updated.open_quantity == 600
    assert updated.cost_basis == Decimal("1532.00")
    assert updated.average_entry_price == Decimal("2.553333333333333333333333333")
    assert updated.opened_at == first.executed_at
    assert updated.last_execution_at == second.executed_at

    # Immutable snapshot: the previous state remains unchanged.
    assert position.open_quantity == 400
    assert position.cost_basis == Decimal("992.00")


def test_additional_purchase_must_belong_to_same_trade() -> None:
    trade = workspace_trade()
    first = execution(trade)
    position = Position.from_execution(
        id=uuid4(),
        trade=trade,
        execution=first,
    )

    other_trade = external_trade()
    other_execution = execution(other_trade)

    with pytest.raises(ValueError, match="execution does not belong to position trade"):
        position.apply_purchase(other_execution)


def test_additional_purchase_must_reference_same_product() -> None:
    trade = workspace_trade()
    first = execution(trade)
    position = Position.from_execution(
        id=uuid4(),
        trade=trade,
        execution=first,
    )

    inconsistent = ExecutionRecord(
        id=uuid4(),
        trade_id=trade.id,
        product_id=uuid4(),
        quantity=1,
        price_per_unit=Decimal("6.00"),
        executed_at=datetime(2026, 8, 17, 9, 0, tzinfo=UTC),
        recorded_at=datetime(2026, 8, 17, 9, 1, tzinfo=UTC),
        recorded_by=uuid4(),
    )

    with pytest.raises(ValueError, match="execution product does not match position"):
        position.apply_purchase(inconsistent)


def test_additional_purchase_cannot_precede_position_history() -> None:
    trade = workspace_trade()
    first = execution(
        trade,
        executed_at=datetime(2026, 8, 17, 9, 0, tzinfo=UTC),
    )
    position = Position.from_execution(
        id=uuid4(),
        trade=trade,
        execution=first,
    )

    earlier = execution(
        trade,
        quantity=1,
        price="6.00",
        executed_at=datetime(2026, 8, 17, 8, 0, tzinfo=UTC),
        recorded_at=datetime(2026, 8, 17, 10, 0, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="execution time must not precede"):
        position.apply_purchase(earlier)


def test_execution_cannot_be_recorded_before_execution() -> None:
    trade = workspace_trade()

    with pytest.raises(ValueError, match="recorded_at must not precede executed_at"):
        execution(
            trade,
            executed_at=datetime(2026, 8, 17, 10, 0, tzinfo=UTC),
            recorded_at=datetime(2026, 8, 17, 9, 59, tzinfo=UTC),
        )


@pytest.mark.parametrize(
    ("open_quantity", "cost_basis", "average_entry_price"),
    [
        (0, Decimal("1.00"), Decimal("1.00")),
        (-1, Decimal("1.00"), Decimal("1.00")),
        (1, Decimal("0"), Decimal("1.00")),
        (1, Decimal("-1.00"), Decimal("1.00")),
        (1, Decimal("1.00"), Decimal("0")),
        (1, Decimal("1.00"), Decimal("-1.00")),
    ],
)
def test_position_requires_positive_aggregates(
    open_quantity: int,
    cost_basis: Decimal,
    average_entry_price: Decimal,
) -> None:
    with pytest.raises(ValueError):
        Position(
            id=uuid4(),
            trade_id=uuid4(),
            product_id=uuid4(),
            open_quantity=open_quantity,
            cost_basis=cost_basis,
            average_entry_price=average_entry_price,
            opened_at=EXECUTED_AT,
            last_execution_at=EXECUTED_AT,
        )


def test_position_last_execution_must_not_precede_opening() -> None:
    with pytest.raises(
        ValueError,
        match="last_execution_at must not precede opened_at",
    ):
        Position(
            id=uuid4(),
            trade_id=uuid4(),
            product_id=uuid4(),
            open_quantity=1,
            cost_basis=Decimal("1.00"),
            average_entry_price=Decimal("1.00"),
            opened_at=datetime(2026, 8, 17, 10, 0, tzinfo=UTC),
            last_execution_at=datetime(2026, 8, 17, 9, 0, tzinfo=UTC),
        )
