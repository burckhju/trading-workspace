"""Immutable FT-009 Trade, ExecutionRecord and Position domain snapshots."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from app.features.trade_position.domain.enums import TradeOrigin


@dataclass(frozen=True, slots=True)
class Trade:
    id: UUID
    workspace_id: UUID
    product_id: UUID
    origin: TradeOrigin
    created_at: datetime
    created_by: UUID
    trade_plan_id: UUID | None = None
    trade_plan_version_id: UUID | None = None
    product_selection_id: UUID | None = None
    product_evaluation_id: UUID | None = None

    def __post_init__(self) -> None:
        provenance = (
            self.trade_plan_id,
            self.trade_plan_version_id,
            self.product_selection_id,
            self.product_evaluation_id,
        )

        if self.origin is TradeOrigin.WORKSPACE_SELECTION and any(
            value is None for value in provenance
        ):
            raise ValueError("workspace trade requires product selection provenance")

        if self.origin is TradeOrigin.EXTERNAL and any(value is not None for value in provenance):
            raise ValueError("external trade must not carry product selection provenance")


@dataclass(frozen=True, slots=True)
class ExecutionRecord:
    id: UUID
    trade_id: UUID
    product_id: UUID
    quantity: int
    price_per_unit: Decimal
    executed_at: datetime
    recorded_at: datetime
    recorded_by: UUID

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.price_per_unit <= 0:
            raise ValueError("price_per_unit must be positive")
        if self.recorded_at < self.executed_at:
            raise ValueError("recorded_at must not precede executed_at")

    @property
    def gross_amount(self) -> Decimal:
        return Decimal(self.quantity) * self.price_per_unit


@dataclass(frozen=True, slots=True)
class Position:
    id: UUID
    trade_id: UUID
    product_id: UUID
    open_quantity: int
    cost_basis: Decimal
    average_entry_price: Decimal
    opened_at: datetime
    last_execution_at: datetime

    def __post_init__(self) -> None:
        if self.open_quantity <= 0:
            raise ValueError("open_quantity must be positive")
        if self.cost_basis <= 0:
            raise ValueError("cost_basis must be positive")
        if self.average_entry_price <= 0:
            raise ValueError("average_entry_price must be positive")
        if self.last_execution_at < self.opened_at:
            raise ValueError("last_execution_at must not precede opened_at")

    @classmethod
    def from_execution(
        cls,
        *,
        id: UUID,
        trade: Trade,
        execution: ExecutionRecord,
    ) -> Position:
        if execution.trade_id != trade.id:
            raise ValueError("execution does not belong to trade")
        if execution.product_id != trade.product_id:
            raise ValueError("execution product does not match trade")

        return cls(
            id=id,
            trade_id=trade.id,
            product_id=trade.product_id,
            open_quantity=execution.quantity,
            cost_basis=execution.gross_amount,
            average_entry_price=execution.price_per_unit,
            opened_at=execution.executed_at,
            last_execution_at=execution.executed_at,
        )

    def apply_purchase(self, execution: ExecutionRecord) -> Position:
        if execution.trade_id != self.trade_id:
            raise ValueError("execution does not belong to position trade")
        if execution.product_id != self.product_id:
            raise ValueError("execution product does not match position")
        if execution.executed_at < self.last_execution_at:
            raise ValueError("execution time must not precede position execution history")

        new_quantity = self.open_quantity + execution.quantity
        new_cost_basis = self.cost_basis + execution.gross_amount
        new_average_entry_price = new_cost_basis / Decimal(new_quantity)

        return replace(
            self,
            open_quantity=new_quantity,
            cost_basis=new_cost_basis,
            average_entry_price=new_average_entry_price,
            last_execution_at=execution.executed_at,
        )
