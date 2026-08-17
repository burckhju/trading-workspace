"""Deterministic FT-010 Position projection from effective executions."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from app.features.trade_position.domain.enums import ExecutionSide
from app.features.trade_position.domain.models import ExecutionRecord, Position, Trade


class PositionProjector:
    @staticmethod
    def project(
        *,
        id: UUID,
        trade: Trade,
        executions: list[ExecutionRecord],
    ) -> Position:
        if not executions:
            raise ValueError("position projection requires execution history")

        ordered = sorted(
            executions,
            key=lambda execution: (
                execution.executed_at,
                execution.recorded_at,
                execution.id,
            ),
        )

        open_quantity = 0
        cost_basis = Decimal("0")
        average_entry_price: Decimal | None = None
        realized_gross_pnl = Decimal("0")
        opened_at = None
        closed_at = None

        for execution in ordered:
            if execution.trade_id != trade.id:
                raise ValueError("execution does not belong to trade")
            if execution.product_id != trade.product_id:
                raise ValueError("execution product does not match trade")

            if execution.side is ExecutionSide.BUY:
                if closed_at is not None:
                    raise ValueError("closed trade must not be reopened by BUY execution")

                if opened_at is None:
                    opened_at = execution.executed_at

                new_quantity = open_quantity + execution.quantity
                cost_basis += execution.gross_amount
                open_quantity = new_quantity
                average_entry_price = cost_basis / Decimal(open_quantity)
                continue

            if opened_at is None or average_entry_price is None:
                raise ValueError("SELL execution requires prior open quantity")
            if execution.quantity > open_quantity:
                raise ValueError("SELL quantity exceeds current open quantity")

            applicable_cost = average_entry_price
            realized_gross_pnl += Decimal(execution.quantity) * (
                execution.price_per_unit - applicable_cost
            )
            cost_basis -= Decimal(execution.quantity) * applicable_cost
            open_quantity -= execution.quantity

            if open_quantity == 0:
                cost_basis = Decimal("0")
                closed_at = execution.executed_at

        if opened_at is None or average_entry_price is None:
            raise ValueError("position projection requires BUY execution")

        return Position(
            id=id,
            trade_id=trade.id,
            product_id=trade.product_id,
            open_quantity=open_quantity,
            cost_basis=cost_basis,
            average_entry_price=average_entry_price,
            realized_gross_pnl=realized_gross_pnl,
            opened_at=opened_at,
            last_execution_at=ordered[-1].executed_at,
            closed_at=closed_at,
        )
