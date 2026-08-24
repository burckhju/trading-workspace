"""SQLAlchemy cross-feature read adapters for FT-012 Learning."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.learning.application.ports import ProductContext, TradeContext
from app.features.product.persistence.models import WarrantModel
from app.features.trade_position.persistence.repositories import (
    SqlAlchemyTradeRepository,
)


class SqlAlchemyTradeReader:
    def __init__(self, session: AsyncSession) -> None:
        self._trades = SqlAlchemyTradeRepository(session)

    async def get(
        self,
        *,
        workspace_id: UUID,
        trade_id: UUID,
    ) -> TradeContext | None:
        trade = await self._trades.get(workspace_id, trade_id)
        if trade is None:
            return None
        return TradeContext(
            workspace_id=trade.workspace_id,
            trade_id=trade.id,
            origin=trade.origin,
            product_id=trade.product_id,
        )


class SqlAlchemyProductReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self,
        *,
        workspace_id: UUID,
        product_id: UUID,
    ) -> ProductContext | None:
        warrant = await self._session.scalar(
            select(WarrantModel).where(
                WarrantModel.id == product_id,
                WarrantModel.workspace_id == workspace_id,
            )
        )
        if warrant is None:
            return None
        return ProductContext(
            product_id=warrant.id,
            underlying_id=warrant.underlying_id,
        )
