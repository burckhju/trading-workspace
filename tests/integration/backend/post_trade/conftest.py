"""PostgreSQL integration fixtures for FT-011."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)

EXPECTED_DATABASE = "trading_workspace_test"
EXPECTED_ALEMBIC_HEAD = "20260826_0026"


def _test_database_url() -> str:
    explicit = os.getenv("TRADING_WORKSPACE_TEST_DATABASE_URL")
    if explicit:
        return explicit

    repository_root = Path(__file__).resolve().parents[4]
    env_path = repository_root / "docker" / ".env"
    if not env_path.exists():
        raise RuntimeError(
            "TRADING_WORKSPACE_TEST_DATABASE_URL fehlt " "und docker/.env ist nicht vorhanden"
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
async def post_trade_test_engine() -> AsyncEngine:
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

            if revision != EXPECTED_ALEMBIC_HEAD:
                raise RuntimeError(
                    "Test-DB ist nicht auf erwartetem "
                    "Alembic Head: "
                    f"{revision!r} != "
                    f"{EXPECTED_ALEMBIC_HEAD!r}"
                )

        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def post_trade_connection(
    post_trade_test_engine: AsyncEngine,
) -> AsyncConnection:
    async with post_trade_test_engine.connect() as connection:
        transaction = await connection.begin()

        try:
            yield connection
        finally:
            if transaction.is_active:
                await transaction.rollback()


@pytest_asyncio.fixture
async def post_trade_session(
    post_trade_connection: AsyncConnection,
) -> AsyncSession:
    session = AsyncSession(
        bind=post_trade_connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        await session.close()
