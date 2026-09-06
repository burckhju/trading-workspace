"""SQLAlchemy engine and session lifecycle management."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from typing import Any

from sqlalchemy import event, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings
from app.core.logging.context import record_database_query

_QUERY_STARTED_AT = "trading_workspace_query_started_at"


class DatabaseManager:
    """Own the asynchronous SQLAlchemy engine and session factory."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._url = make_url(settings.database_url)
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def url(self) -> URL:
        """Return the parsed database URL without opening a connection."""

        return self._url

    @property
    def engine(self) -> AsyncEngine:
        """Create and return the managed SQLAlchemy engine lazily."""

        if self._engine is None:
            self._engine = create_async_engine(
                self._url,
                echo=self._settings.database_echo,
                pool_pre_ping=True,
                pool_size=self._settings.database_pool_size,
                max_overflow=self._settings.database_max_overflow,
                pool_recycle=self._settings.database_pool_recycle_seconds,
            )
            self._attach_query_metrics(self._engine)
        return self._engine

    @staticmethod
    def _attach_query_metrics(engine: AsyncEngine) -> None:
        """Attach lightweight timing listeners without logging SQL or parameters."""

        def before_cursor_execute(
            _connection: Any,
            _cursor: Any,
            _statement: str,
            _parameters: Any,
            context: Any,
            _executemany: bool,
        ) -> None:
            setattr(context, _QUERY_STARTED_AT, perf_counter())

        def after_cursor_execute(
            _connection: Any,
            _cursor: Any,
            _statement: str,
            _parameters: Any,
            context: Any,
            _executemany: bool,
        ) -> None:
            started_at = getattr(context, _QUERY_STARTED_AT, None)
            if started_at is not None:
                record_database_query((perf_counter() - started_at) * 1000)

        event.listen(engine.sync_engine, "before_cursor_execute", before_cursor_execute)
        event.listen(engine.sync_engine, "after_cursor_execute", after_cursor_execute)

    def _get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                autoflush=False,
                expire_on_commit=False,
            )
        return self._session_factory

    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yield one transactional session and guarantee cleanup."""

        async with self._get_session_factory()() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    @asynccontextmanager
    async def session_context(self) -> AsyncIterator[AsyncSession]:
        """Expose a reusable async context manager around one managed session."""

        async for session in self.session():
            yield session
            return

    async def ping(self) -> None:
        """Verify that the database accepts a simple statement."""

        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def dispose(self) -> None:
        """Close all pooled database connections."""

        if self._engine is not None:
            await self._engine.dispose()
