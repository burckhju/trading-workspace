"""Deterministic FT-010 Position projection from effective executions."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from uuid import UUID

from app.features.trade_position.domain.enums import ExecutionSide
from app.features.trade_position.domain.models import ExecutionRecord, Position, Trade


@dataclass(frozen=True, slots=True)
class SellProjectionTrace:
    """One SELL's existing arithmetic, without currency or reporting qualification.

    ``execution_index`` identifies the SELL in ``ordered_executions``. All records
    before that index are its complete cost-basis history, including prior SELLs.
    ``cost_basis_before_close_reset`` is present only at a full exit: the existing
    projector resets that remainder to zero without adjusting realized P&L.
    """

    execution_index: int
    open_quantity_before: int
    cost_basis_before: Decimal
    average_cost_per_unit: Decimal
    realized_gross_pnl_delta: Decimal
    open_quantity_after: int
    cost_basis_after: Decimal
    cost_basis_before_close_reset: Decimal | None


@dataclass(frozen=True, slots=True)
class BuyProjectionContribution:
    """One effective BUY's remaining weight in the owner's average-cost pool.

    This is an analytical quantity contribution, not a separately held lot or a
    FIFO allocation. SELLs reduce every prior BUY proportionally. Consumers use
    the owner's ``position.open_quantity`` as the denominator, including when a
    price/evidence value is missing. Rational weights are converted to Decimal
    only for this immutable read result; no monetary arithmetic is changed.
    """

    execution_id: UUID
    original_quantity: int
    remaining_quantity: Decimal


@dataclass(frozen=True, slots=True)
class PositionProjectionTrace:
    """Pure projection and immutable source snapshots from one effective stream.

    Callers supply the complete, already effective execution history. This result
    neither selects effective records nor qualifies cancellation, currency, date
    attribution or a reporting period. Date-only anchors retain their original
    precision in the execution snapshots; they are not actual clock times.
    """

    position: Position
    ordered_executions: tuple[ExecutionRecord, ...]
    sells: tuple[SellProjectionTrace, ...]
    buy_contributions: tuple[BuyProjectionContribution, ...] = ()


class PositionProjector:
    @staticmethod
    def project(
        *,
        id: UUID,
        trade: Trade,
        executions: list[ExecutionRecord],
    ) -> Position:
        position, _ = PositionProjector._project(
            id=id, trade=trade, executions=executions, sells=None, buys=None
        )
        return position

    @staticmethod
    def project_with_trace(
        *,
        id: UUID,
        trade: Trade,
        executions: list[ExecutionRecord],
    ) -> PositionProjectionTrace:
        sells: list[SellProjectionTrace] = []
        buys: list[BuyProjectionContribution] = []
        position, ordered = PositionProjector._project(
            id=id, trade=trade, executions=executions, sells=sells, buys=buys
        )
        return PositionProjectionTrace(
            position=position,
            ordered_executions=tuple(ordered),
            sells=tuple(sells),
            buy_contributions=tuple(buys),
        )

    @staticmethod
    def _project(
        *,
        id: UUID,
        trade: Trade,
        executions: list[ExecutionRecord],
        sells: list[SellProjectionTrace] | None,
        buys: list[BuyProjectionContribution] | None,
    ) -> tuple[Position, list[ExecutionRecord]]:
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
        opened_on = None
        closed_at = None
        closed_on = None
        # Track only read provenance alongside this same economic projection.
        # Fractions avoid accumulating a different rounding history per BUY.
        buy_weights: dict[UUID, tuple[int, Fraction]] = {}
        remaining_factor = Fraction(1)

        for execution_index, execution in enumerate(ordered):
            if execution.trade_id != trade.id:
                raise ValueError("execution does not belong to trade")
            if execution.product_id != trade.product_id:
                raise ValueError("execution product does not match trade")

            if execution.side is ExecutionSide.BUY:
                if closed_at is not None:
                    raise ValueError("closed trade must not be reopened by BUY execution")

                if opened_at is None:
                    opened_at = execution.executed_at
                    opened_on = execution.executed_on

                new_quantity = open_quantity + execution.quantity
                cost_basis += execution.gross_amount
                open_quantity = new_quantity
                average_entry_price = cost_basis / Decimal(open_quantity)
                if buys is not None:
                    buy_weights[execution.id] = (
                        execution.quantity,
                        Fraction(execution.quantity) / remaining_factor,
                    )
                continue

            if opened_at is None or average_entry_price is None:
                raise ValueError("SELL execution requires prior open quantity")
            if execution.quantity > open_quantity:
                raise ValueError("SELL quantity exceeds current open quantity")

            open_quantity_before = open_quantity
            cost_basis_before = cost_basis
            applicable_cost = average_entry_price
            realized_gross_pnl_delta = Decimal(execution.quantity) * (
                execution.price_per_unit - applicable_cost
            )
            realized_gross_pnl += realized_gross_pnl_delta
            cost_basis -= Decimal(execution.quantity) * applicable_cost
            open_quantity -= execution.quantity
            if buys is not None:
                remaining_factor *= Fraction(open_quantity, open_quantity_before)

            cost_basis_before_close_reset = None
            if open_quantity == 0:
                cost_basis_before_close_reset = cost_basis
                cost_basis = Decimal("0")
                closed_at = execution.executed_at
                closed_on = execution.executed_on

            if sells is not None:
                sells.append(
                    SellProjectionTrace(
                        execution_index=execution_index,
                        open_quantity_before=open_quantity_before,
                        cost_basis_before=cost_basis_before,
                        average_cost_per_unit=applicable_cost,
                        realized_gross_pnl_delta=realized_gross_pnl_delta,
                        open_quantity_after=open_quantity,
                        cost_basis_after=cost_basis,
                        cost_basis_before_close_reset=cost_basis_before_close_reset,
                    )
                )

        if opened_at is None or average_entry_price is None:
            raise ValueError("position projection requires BUY execution")

        if buys is not None:
            buys.extend(
                BuyProjectionContribution(
                    execution_id=execution_id,
                    original_quantity=quantity,
                    remaining_quantity=Decimal((weight * remaining_factor).numerator)
                    / Decimal((weight * remaining_factor).denominator),
                )
                for execution_id, (quantity, weight) in buy_weights.items()
            )

        position = Position(
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
            opened_on=opened_on,
            last_execution_on=ordered[-1].executed_on,
            closed_on=closed_on,
        )
        return position, ordered
