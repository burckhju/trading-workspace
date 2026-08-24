"""Shared-session FT-009 external Trade creator for FT-012."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.product.service.application import WarrantService
from app.features.trade_position.domain.enums import TradeOrigin
from app.features.trade_position.domain.models import (
    ExecutionRecord,
    Position,
    Trade,
)
from app.features.trade_position.persistence.repositories import (
    SqlAlchemyExecutionRecordRepository,
    SqlAlchemyPositionRepository,
    SqlAlchemyTradeRepository,
)
from app.features.trade_position.service.resolvers import WarrantProductResolver


class ExternalTradeCreator(Protocol):
    async def create(
        self,
        *,
        workspace_id: UUID,
        product_id: UUID,
        quantity: int,
        price_per_unit: Decimal,
        executed_at: datetime,
        actor_id: UUID,
    ) -> tuple[Trade, ExecutionRecord, Position]: ...


class SqlAlchemyExternalTradeCreator:
    """Create FT-009 Trade state in the caller-owned transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._products = WarrantProductResolver(WarrantService(session))
        self._trades = SqlAlchemyTradeRepository(session)
        self._executions = SqlAlchemyExecutionRecordRepository(session)
        self._positions = SqlAlchemyPositionRepository(session)

    async def create(
        self,
        *,
        workspace_id: UUID,
        product_id: UUID,
        quantity: int,
        price_per_unit: Decimal,
        executed_at: datetime,
        actor_id: UUID,
    ) -> tuple[Trade, ExecutionRecord, Position]:
        product = await self._products.resolve(workspace_id, product_id)
        if product is None:
            raise ValueError("product not found")

        now = datetime.now(UTC)
        trade = Trade(
            id=uuid4(),
            workspace_id=workspace_id,
            product_id=product.product_id,
            origin=TradeOrigin.EXTERNAL,
            created_at=now,
            created_by=actor_id,
        )
        execution = ExecutionRecord(
            id=uuid4(),
            trade_id=trade.id,
            product_id=trade.product_id,
            quantity=quantity,
            price_per_unit=price_per_unit,
            executed_at=executed_at,
            recorded_at=max(now, executed_at),
            recorded_by=actor_id,
        )
        position = Position.from_execution(
            id=uuid4(),
            trade=trade,
            execution=execution,
        )

        # The FT-009 ORM mappings do not expose relationships that let
        # SQLAlchemy infer the FK insert order. Flush each dependency
        # boundary explicitly while keeping the caller-owned transaction.
        await self._trades.add(trade)
        await self._session.flush()

        await self._executions.add(execution)
        await self._session.flush()

        await self._positions.add(position)
        await self._session.flush()

        return trade, execution, position
