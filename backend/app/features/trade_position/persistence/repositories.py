"""SQLAlchemy repositories for FT-009 Trade & Position."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.trade_position.domain.enums import TradeOrigin
from app.features.trade_position.domain.models import ExecutionRecord, Position, Trade
from app.features.trade_position.persistence.models import (
    ExecutionRecordModel,
    PositionModel,
    TradeModel,
)


class TradeRepository(Protocol):
    async def add(self, trade: Trade) -> None: ...

    async def get(
        self,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> Trade | None: ...


class ExecutionRecordRepository(Protocol):
    async def add(self, execution: ExecutionRecord) -> None: ...


class PositionRepository(Protocol):
    async def add(self, position: Position) -> None: ...

    async def get_for_trade(
        self,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> Position | None: ...

    async def replace(self, position: Position) -> None: ...


class SqlAlchemyTradeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, trade: Trade) -> None:
        self._session.add(
            TradeModel(
                id=trade.id,
                workspace_id=trade.workspace_id,
                product_id=trade.product_id,
                origin=trade.origin.value,
                created_at=trade.created_at,
                created_by=trade.created_by,
                trade_plan_id=trade.trade_plan_id,
                trade_plan_version_id=trade.trade_plan_version_id,
                product_selection_id=trade.product_selection_id,
                product_evaluation_id=trade.product_evaluation_id,
            )
        )

    async def get(
        self,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> Trade | None:
        model = await self._session.scalar(
            select(TradeModel).where(
                TradeModel.workspace_id == workspace_id,
                TradeModel.id == trade_id,
            )
        )
        if model is None:
            return None

        return Trade(
            id=model.id,
            workspace_id=model.workspace_id,
            product_id=model.product_id,
            origin=TradeOrigin(model.origin),
            created_at=model.created_at,
            created_by=model.created_by,
            trade_plan_id=model.trade_plan_id,
            trade_plan_version_id=model.trade_plan_version_id,
            product_selection_id=model.product_selection_id,
            product_evaluation_id=model.product_evaluation_id,
        )


class SqlAlchemyExecutionRecordRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, execution: ExecutionRecord) -> None:
        self._session.add(
            ExecutionRecordModel(
                id=execution.id,
                trade_id=execution.trade_id,
                product_id=execution.product_id,
                quantity=execution.quantity,
                price_per_unit=execution.price_per_unit,
                executed_at=execution.executed_at,
                recorded_at=execution.recorded_at,
                recorded_by=execution.recorded_by,
            )
        )


class SqlAlchemyPositionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, position: Position) -> None:
        self._session.add(
            PositionModel(
                id=position.id,
                trade_id=position.trade_id,
                product_id=position.product_id,
                open_quantity=position.open_quantity,
                cost_basis=position.cost_basis,
                average_entry_price=position.average_entry_price,
                opened_at=position.opened_at,
                last_execution_at=position.last_execution_at,
            )
        )

    async def get_for_trade(
        self,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> Position | None:
        model = await self._session.scalar(
            select(PositionModel)
            .join(
                TradeModel,
                TradeModel.id == PositionModel.trade_id,
            )
            .where(
                TradeModel.workspace_id == workspace_id,
                PositionModel.trade_id == trade_id,
            )
        )
        if model is None:
            return None

        return Position(
            id=model.id,
            trade_id=model.trade_id,
            product_id=model.product_id,
            open_quantity=model.open_quantity,
            cost_basis=model.cost_basis,
            average_entry_price=model.average_entry_price,
            opened_at=model.opened_at,
            last_execution_at=model.last_execution_at,
        )

    async def replace(self, position: Position) -> None:
        model = await self._session.scalar(
            select(PositionModel).where(
                PositionModel.id == position.id,
            )
        )
        if model is None:
            raise LookupError("position not found")

        model.product_id = position.product_id
        model.open_quantity = position.open_quantity
        model.cost_basis = position.cost_basis
        model.average_entry_price = position.average_entry_price
        model.opened_at = position.opened_at
        model.last_execution_at = position.last_execution_at
