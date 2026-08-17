"""Unit-of-work contract and SQLAlchemy implementation for FT-009."""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.trade_position.persistence.repositories import (
    ExecutionRecordRepository,
    PositionRepository,
    SqlAlchemyExecutionRecordRepository,
    SqlAlchemyPositionRepository,
    SqlAlchemyTradeManagementEventRepository,
    SqlAlchemyTradeRepository,
    TradeManagementEventRepository,
    TradeRepository,
)


class TradePositionUnitOfWork(Protocol):
    trades: TradeRepository
    executions: ExecutionRecordRepository
    positions: PositionRepository
    management_events: TradeManagementEventRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def flush(self) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class SqlAlchemyTradePositionUnitOfWork:
    trades: TradeRepository
    executions: ExecutionRecordRepository
    positions: PositionRepository

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.trades = SqlAlchemyTradeRepository(session)
        self.executions = SqlAlchemyExecutionRecordRepository(session)
        self.positions = SqlAlchemyPositionRepository(session)
        self.management_events = SqlAlchemyTradeManagementEventRepository(session)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def flush(self) -> None:
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
