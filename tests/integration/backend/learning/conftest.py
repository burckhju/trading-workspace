"""PostgreSQL integration fixtures for FT-012 and follow-on learning slices."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from urllib.parse import quote

import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)

EXPECTED_DATABASE = "trading_workspace_test"
EXPECTED_ALEMBIC_HEAD = "20260825_0023"
REBUILD_BASE_ALEMBIC_HEAD = "20260824_0022"


def _test_database_url() -> str:
    explicit = os.getenv("TRADING_WORKSPACE_TEST_DATABASE_URL")
    if explicit:
        return explicit

    repository_root = Path(__file__).resolve().parents[4]
    env_path = repository_root / "docker" / ".env"
    if not env_path.exists():
        raise RuntimeError(
            "TRADING_WORKSPACE_TEST_DATABASE_URL fehlt und docker/.env ist nicht vorhanden"
        )

    values: dict[str, str] = {}

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()

        if not raw or raw.startswith("#") or "=" not in raw:
            continue

        key, value = raw.split("=", 1)

        values[key.strip()] = value.strip().strip('"').strip("'")

    user = values.get("POSTGRES_USER")
    password = values.get("POSTGRES_PASSWORD")

    if not user or password is None:
        raise RuntimeError("POSTGRES_USER / POSTGRES_PASSWORD fehlen in docker/.env")

    return (
        "postgresql+asyncpg://"
        f"{quote(user, safe='')}:"
        f"{quote(password, safe='')}"
        "@localhost:5432/"
        f"{EXPECTED_DATABASE}"
    )


@pytest_asyncio.fixture
async def learning_test_engine() -> AsyncEngine:
    engine = create_async_engine(
        _test_database_url(),
        pool_pre_ping=True,
    )

    try:
        async with engine.connect() as connection:
            database = await connection.scalar(text("select current_database()"))

            if database != EXPECTED_DATABASE:
                raise RuntimeError(
                    "Integrationstests dürfen nur gegen "
                    f"{EXPECTED_DATABASE!r} laufen; "
                    f"aktuell: {database!r}"
                )

            revision = await connection.scalar(text("select version_num from alembic_version"))

        repository_root = Path(__file__).resolve().parents[4]
        config = Config(str(repository_root / "backend" / "alembic.ini"))
        test_database_url = _test_database_url()

        def run_alembic(action: str, revision_target: str) -> None:
            previous = os.environ.get("TRADING_WORKSPACE_DATABASE_URL")
            os.environ["TRADING_WORKSPACE_DATABASE_URL"] = test_database_url
            try:
                if action == "upgrade":
                    command.upgrade(config, revision_target)
                elif action == "downgrade":
                    command.downgrade(config, revision_target)
                else:
                    raise ValueError(action)
            finally:
                if previous is None:
                    os.environ.pop("TRADING_WORKSPACE_DATABASE_URL", None)
                else:
                    os.environ["TRADING_WORKSPACE_DATABASE_URL"] = previous

        if revision == EXPECTED_ALEMBIC_HEAD:
            await asyncio.to_thread(
                run_alembic,
                "downgrade",
                REBUILD_BASE_ALEMBIC_HEAD,
            )
            revision = REBUILD_BASE_ALEMBIC_HEAD

        if revision != EXPECTED_ALEMBIC_HEAD:
            await asyncio.to_thread(
                run_alembic,
                "upgrade",
                EXPECTED_ALEMBIC_HEAD,
            )

            async with engine.connect() as connection:
                revision = await connection.scalar(text("select version_num from alembic_version"))
            if revision != EXPECTED_ALEMBIC_HEAD:
                raise RuntimeError(
                    "Test-DB konnte nicht auf erwarteten Alembic Head migriert werden: "
                    f"{revision!r} != {EXPECTED_ALEMBIC_HEAD!r}"
                )

        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def learning_connection(
    learning_test_engine: AsyncEngine,
) -> AsyncConnection:
    async with learning_test_engine.connect() as connection:
        transaction = await connection.begin()

        try:
            yield connection
        finally:
            if transaction.is_active:
                await transaction.rollback()


@pytest_asyncio.fixture
async def learning_session(
    learning_connection: AsyncConnection,
) -> AsyncSession:
    session = AsyncSession(
        bind=learning_connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        await session.close()
