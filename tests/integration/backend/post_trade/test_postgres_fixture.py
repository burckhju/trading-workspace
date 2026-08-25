"""Qualification tests for the FT-011 PostgreSQL fixture."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

pytestmark = pytest.mark.asyncio


async def test_fixture_uses_isolated_database(
    post_trade_test_engine: AsyncEngine,
) -> None:
    async with post_trade_test_engine.connect() as connection:
        database = await connection.scalar(text("select current_database()"))
        revision = await connection.scalar(text("select version_num from alembic_version"))

    assert database == "trading_workspace_test"
    assert revision == "20260825_0024"


async def test_session_commit_is_contained_by_outer_transaction(
    post_trade_session: AsyncSession,
) -> None:
    await post_trade_session.execute(text("""
            create table
            s11_fixture_rollback_probe (
                id integer primary key
            )
            """))

    await post_trade_session.execute(text("""
            insert into s11_fixture_rollback_probe (id)
            values (1)
            """))

    await post_trade_session.commit()

    value = await post_trade_session.scalar(text("""
            select id
            from s11_fixture_rollback_probe
            where id = 1
            """))

    assert value == 1


async def test_previous_test_was_fully_rolled_back(
    post_trade_test_engine: AsyncEngine,
) -> None:
    async with post_trade_test_engine.connect() as connection:
        exists = await connection.scalar(text("""
                select to_regclass(
                    'public.s11_fixture_rollback_probe'
                )
                """))

    assert exists is None
