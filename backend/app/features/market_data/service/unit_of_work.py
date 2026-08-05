"""Transaction boundary for market-data persistence."""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market.persistence.repositories import (
    AuditEventRepository,
    SqlAlchemyAuditEventRepository,
)
from app.features.market_data.persistence.repositories import (
    DailyPriceRepository,
    ProviderInstrumentMappingRepository,
    SqlAlchemyDailyPriceRepository,
    SqlAlchemyProviderInstrumentMappingRepository,
)


class MarketDataUnitOfWork(Protocol):
    """Expose market-data repositories under one explicit transaction."""

    mappings: ProviderInstrumentMappingRepository
    daily_prices: DailyPriceRepository
    audit_events: AuditEventRepository

    async def __aenter__(self) -> Self: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


class SqlAlchemyMarketDataUnitOfWork:
    """SQLAlchemy market-data unit of work; repositories never commit."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.mappings = SqlAlchemyProviderInstrumentMappingRepository(session)
        self.daily_prices = SqlAlchemyDailyPriceRepository(session)
        self.audit_events = SqlAlchemyAuditEventRepository(session)

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

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
