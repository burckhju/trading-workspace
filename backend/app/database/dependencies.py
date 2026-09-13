"""FastAPI dependencies for database access."""

from collections.abc import AsyncIterator
from contextlib import aclosing
from typing import cast

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.manager import DatabaseManager


def get_database_manager(request: Request) -> DatabaseManager:
    """Resolve the application-scoped database manager."""

    return cast(DatabaseManager, request.app.state.container.database)


async def get_database_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Provide one request-scoped asynchronous database session."""

    manager = get_database_manager(request)
    async with aclosing(manager.session()) as sessions:
        async for session in sessions:
            yield session
