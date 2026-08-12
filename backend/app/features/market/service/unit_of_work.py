"""Unit-of-work contracts and SQLAlchemy implementation for FT-001."""

from __future__ import annotations

from collections.abc import Sequence
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market.persistence.repositories import (
    AuditEventRepository,
    ListingRepository,
    ReferenceDataRepository,
    SqlAlchemyAuditEventRepository,
    SqlAlchemyListingRepository,
    SqlAlchemyReferenceDataRepository,
    SqlAlchemyUnderlyingRepository,
    SqlAlchemyWorkspaceRepository,
    UnderlyingRepository,
    WorkspaceRepository,
)
from app.features.market.service.types import UsageReference


class UsageRepository(Protocol):
    async def list_for_underlying(
        self, workspace_id: UUID, underlying_id: UUID
    ) -> Sequence[UsageReference]: ...


class NoUsageRepository:
    """FT-001 default until referencing features provide usage adapters."""

    async def list_for_underlying(
        self, workspace_id: UUID, underlying_id: UUID
    ) -> Sequence[UsageReference]:
        return ()


class MarketUnitOfWork(Protocol):
    workspaces: WorkspaceRepository
    reference_data: ReferenceDataRepository
    underlyings: UnderlyingRepository
    listings: ListingRepository
    audit_events: AuditEventRepository
    usages: UsageRepository

    async def __aenter__(self) -> Self: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


class SqlAlchemyMarketUnitOfWork:
    workspaces: WorkspaceRepository
    reference_data: ReferenceDataRepository
    underlyings: UnderlyingRepository
    listings: ListingRepository
    audit_events: AuditEventRepository
    usages: UsageRepository

    def __init__(
        self, session: AsyncSession, usages: UsageRepository | None = None
    ) -> None:
        self._session = session
        self.workspaces = SqlAlchemyWorkspaceRepository(session)
        self.reference_data = SqlAlchemyReferenceDataRepository(session)
        self.underlyings = SqlAlchemyUnderlyingRepository(session)
        self.listings = SqlAlchemyListingRepository(session)
        self.audit_events = SqlAlchemyAuditEventRepository(session)
        self.usages = usages or NoUsageRepository()

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
