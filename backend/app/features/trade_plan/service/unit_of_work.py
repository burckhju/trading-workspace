"""Unit-of-work contract and SQLAlchemy implementation for FT-007."""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.trade_plan.persistence.repositories import (
    SqlAlchemyTradePlanApprovalRepository,
    SqlAlchemyTradePlanEventRepository,
    SqlAlchemyTradePlanRepository,
    SqlAlchemyTradePlanVersionRepository,
    TradePlanApprovalRepository,
    TradePlanEventRepository,
    TradePlanRepository,
    TradePlanVersionRepository,
)


class TradePlanUnitOfWork(Protocol):
    plans: TradePlanRepository
    versions: TradePlanVersionRepository
    events: TradePlanEventRepository
    approvals: TradePlanApprovalRepository

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


class SqlAlchemyTradePlanUnitOfWork:
    plans: TradePlanRepository
    versions: TradePlanVersionRepository
    events: TradePlanEventRepository
    approvals: TradePlanApprovalRepository

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.plans = SqlAlchemyTradePlanRepository(session)
        self.versions = SqlAlchemyTradePlanVersionRepository(session, self.plans)
        self.events = SqlAlchemyTradePlanEventRepository(session)
        self.approvals = SqlAlchemyTradePlanApprovalRepository(session)

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
