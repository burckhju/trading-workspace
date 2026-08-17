"""Application service for FT-009 Trade & Position purchase execution capture."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID, uuid4

from app.features.trade_position.domain.enums import TradeOrigin
from app.features.trade_position.domain.models import ExecutionRecord, Position, Trade


class WorkspaceSelectionResolver(Protocol):
    async def resolve(
        self,
        workspace_id: UUID,
        product_selection_id: UUID,
    ): ...


class ProductResolver(Protocol):
    async def resolve(
        self,
        workspace_id: UUID,
        product_id: UUID,
    ): ...


class TradePositionService:
    def __init__(
        self,
        *,
        uow,
        workspace_selections: WorkspaceSelectionResolver,
        products: ProductResolver | None = None,
    ) -> None:
        self._uow = uow
        self._workspace_selections = workspace_selections
        self._products = products

    async def record_initial_purchase(
        self,
        *,
        workspace_id: UUID,
        product_selection_id: UUID,
        quantity: int,
        price_per_unit: Decimal,
        executed_at: datetime,
        actor: UUID,
    ) -> tuple[Trade, ExecutionRecord, Position]:
        selection = await self._workspace_selections.resolve(
            workspace_id,
            product_selection_id,
        )
        if selection is None:
            raise ValueError("product selection not found")

        now = datetime.now(UTC)

        trade = Trade(
            id=uuid4(),
            workspace_id=workspace_id,
            product_id=selection.product_id,
            origin=TradeOrigin.WORKSPACE_SELECTION,
            created_at=now,
            created_by=actor,
            trade_plan_id=selection.trade_plan_id,
            trade_plan_version_id=selection.trade_plan_version_id,
            product_selection_id=selection.product_selection_id,
            product_evaluation_id=selection.product_evaluation_id,
        )

        execution = ExecutionRecord(
            id=uuid4(),
            trade_id=trade.id,
            product_id=trade.product_id,
            quantity=quantity,
            price_per_unit=price_per_unit,
            executed_at=executed_at,
            recorded_at=max(now, executed_at),
            recorded_by=actor,
        )

        position = Position.from_execution(
            id=uuid4(),
            trade=trade,
            execution=execution,
        )

        async with self._uow as uow:
            await uow.trades.add(trade)
            await uow.executions.add(execution)
            await uow.positions.add(position)
            await uow.commit()

        return trade, execution, position

    async def record_external_purchase(
        self,
        *,
        workspace_id: UUID,
        product_id: UUID,
        quantity: int,
        price_per_unit: Decimal,
        executed_at: datetime,
        actor: UUID,
    ) -> tuple[Trade, ExecutionRecord, Position]:
        if self._products is None:
            raise ValueError("product resolver is required")

        product = await self._products.resolve(
            workspace_id,
            product_id,
        )
        if product is None:
            raise ValueError("product not found")

        now = datetime.now(UTC)

        trade = Trade(
            id=uuid4(),
            workspace_id=workspace_id,
            product_id=product.product_id,
            origin=TradeOrigin.EXTERNAL,
            created_at=now,
            created_by=actor,
        )

        execution = ExecutionRecord(
            id=uuid4(),
            trade_id=trade.id,
            product_id=trade.product_id,
            quantity=quantity,
            price_per_unit=price_per_unit,
            executed_at=executed_at,
            recorded_at=max(now, executed_at),
            recorded_by=actor,
        )

        position = Position.from_execution(
            id=uuid4(),
            trade=trade,
            execution=execution,
        )

        async with self._uow as uow:
            await uow.trades.add(trade)
            await uow.executions.add(execution)
            await uow.positions.add(position)
            await uow.commit()

        return trade, execution, position

    async def record_additional_purchase(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
        quantity: int,
        price_per_unit: Decimal,
        executed_at: datetime,
        actor: UUID,
    ) -> tuple[ExecutionRecord, Position]:
        async with self._uow as uow:
            trade = await uow.trades.get(
                workspace_id,
                trade_id,
            )
            if trade is None:
                raise ValueError("trade not found")

            position = await uow.positions.get_for_trade(
                workspace_id,
                trade_id,
            )
            if position is None:
                raise ValueError("position not found")

            now = datetime.now(UTC)

            execution = ExecutionRecord(
                id=uuid4(),
                trade_id=trade.id,
                product_id=trade.product_id,
                quantity=quantity,
                price_per_unit=price_per_unit,
                executed_at=executed_at,
                recorded_at=max(now, executed_at),
                recorded_by=actor,
            )

            updated = position.apply_purchase(execution)

            await uow.executions.add(execution)
            await uow.positions.replace(updated)
            await uow.commit()

        return execution, updated
