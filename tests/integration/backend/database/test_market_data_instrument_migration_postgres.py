"""PostgreSQL migration qualification for the D01-A identity foundation."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import get_settings

BASE_REVISION = "20260825_0024"
D01A_REVISION = "20260826_0025"
CURRENT_HEAD = "20260826_0026"
EXPECTED_DATABASE = "trading_workspace_test"


def _test_database_url() -> str:
    url = os.environ.get("TRADING_WORKSPACE_TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TRADING_WORKSPACE_TEST_DATABASE_URL is not configured")
    database_name = url.split("?", 1)[0].rsplit("/", 1)[-1]
    if database_name != EXPECTED_DATABASE:
        pytest.fail(f"D01-A migration test may run only against {EXPECTED_DATABASE}")
    return url


def _alembic_config() -> Config:
    repository_root = Path(__file__).resolve().parents[4]
    return Config(str(repository_root / "backend" / "alembic.ini"))


def _run_alembic(action: str, revision: str, database_url: str) -> None:
    previous = os.environ.get("TRADING_WORKSPACE_DATABASE_URL")
    os.environ["TRADING_WORKSPACE_DATABASE_URL"] = database_url
    get_settings.cache_clear()
    try:
        config = _alembic_config()
        if action == "upgrade":
            command.upgrade(config, revision)
        elif action == "downgrade":
            command.downgrade(config, revision)
        else:
            raise ValueError(action)
    finally:
        if previous is None:
            os.environ.pop("TRADING_WORKSPACE_DATABASE_URL", None)
        else:
            os.environ["TRADING_WORKSPACE_DATABASE_URL"] = previous
        get_settings.cache_clear()


async def _revision(engine: AsyncEngine) -> str:
    async with engine.connect() as connection:
        value = await connection.scalar(text("SELECT version_num FROM alembic_version"))
    assert isinstance(value, str)
    return value


async def _insert_owners(
    engine: AsyncEngine,
    *,
    workspace_id: UUID,
    currency_code: str,
    venue_id: UUID,
    underlying_id: UUID,
    listing_id: UUID,
    reference_id: UUID,
) -> None:
    now = datetime.now(UTC)
    async with engine.begin() as connection:
        await connection.execute(
            text("INSERT INTO workspaces (id, name, created_at) VALUES (:id, :name, :now)"),
            {"id": workspace_id, "name": f"D01-A {workspace_id}", "now": now},
        )
        await connection.execute(
            text(
                "INSERT INTO currencies "
                "(code, name, minor_unit, is_active, reference_version, created_at, updated_at) "
                "VALUES (:code, 'D01-A Currency', 2, true, 'd01a-test', :now, :now)"
            ),
            {"code": currency_code, "now": now},
        )
        await connection.execute(
            text(
                "INSERT INTO trading_venues "
                "(id, mic, name, country_code, timezone, is_active, reference_version, "
                "version, created_at, updated_at) "
                "VALUES (:id, :mic, 'D01-A Venue', 'DE', 'Europe/Berlin', true, "
                "'d01a-test', 1, :now, :now)"
            ),
            {"id": venue_id, "mic": f"D{str(venue_id.int)[-3:]}"[-4:].upper(), "now": now},
        )
        await connection.execute(
            text(
                "INSERT INTO underlyings "
                "(id, workspace_id, type, name, isin, wkn, lifecycle_status, quality_status, "
                "version, created_at, updated_at, data_origin) "
                "VALUES (:id, :workspace_id, 'STOCK', 'D01-A Underlying', NULL, NULL, "
                "'ACTIVE', 'COMPLETE', 1, :now, :now, 'MANUAL')"
            ),
            {"id": underlying_id, "workspace_id": workspace_id, "now": now},
        )
        await connection.execute(
            text(
                "INSERT INTO listings "
                "(id, workspace_id, underlying_id, trading_venue_id, ticker, currency_code, "
                "lifecycle_status, is_primary, version, created_at, updated_at, data_origin) "
                "VALUES (:id, :workspace_id, :underlying_id, :venue_id, :ticker, :currency, "
                "'ACTIVE', false, 1, :now, :now, 'MANUAL')"
            ),
            {
                "id": listing_id,
                "workspace_id": workspace_id,
                "underlying_id": underlying_id,
                "venue_id": venue_id,
                "ticker": f"D01A{str(listing_id.int)[-6:]}",
                "currency": currency_code,
                "now": now,
            },
        )
        await connection.execute(
            text(
                "INSERT INTO market_references "
                "(id, workspace_id, code, name, reference_type, region, role, "
                "reference_version, active, created_at) "
                "VALUES (:id, :workspace_id, :code, 'D01-A Reference', 'INDEX', 'GLOBAL', "
                "'BENCHMARK', 'd01a-test', true, :now)"
            ),
            {
                "id": reference_id,
                "workspace_id": workspace_id,
                "code": f"D01A-{str(reference_id)[:8]}",
                "now": now,
            },
        )


async def _assert_backfill(
    engine: AsyncEngine, *, listing_id: UUID, reference_id: UUID, workspace_id: UUID
) -> None:
    async with engine.connect() as connection:
        result = await connection.execute(
            text(
                "SELECT workspace_id, kind, listing_id, market_reference_id "
                "FROM market_data_instruments "
                "WHERE listing_id = :listing_id OR market_reference_id = :reference_id"
            ),
            {"listing_id": listing_id, "reference_id": reference_id},
        )
        rows = result.mappings().all()
    assert len(rows) == 2
    assert {
        (row["workspace_id"], row["kind"], row["listing_id"], row["market_reference_id"])
        for row in rows
    } == {
        (workspace_id, "LISTING", listing_id, None),
        (workspace_id, "MARKET_REFERENCE", None, reference_id),
    }


@pytest.mark.asyncio
async def test_d01a_upgrade_downgrade_upgrade_preserves_owners_and_backfills() -> None:
    database_url = _test_database_url()
    engine = create_async_engine(database_url, pool_pre_ping=True)
    workspace_id = uuid4()
    venue_id = uuid4()
    underlying_id = uuid4()
    listing_id = uuid4()
    reference_id = uuid4()
    currency_code = "X" + str(workspace_id.int)[-2:]

    try:
        current = await _revision(engine)
        if current == CURRENT_HEAD:
            await asyncio.to_thread(_run_alembic, "downgrade", D01A_REVISION, database_url)
            current = D01A_REVISION
        if current == D01A_REVISION:
            await asyncio.to_thread(_run_alembic, "downgrade", BASE_REVISION, database_url)
        elif current != BASE_REVISION:
            pytest.fail(f"unexpected Alembic revision for D01-A qualification: {current}")

        await _insert_owners(
            engine,
            workspace_id=workspace_id,
            currency_code=currency_code,
            venue_id=venue_id,
            underlying_id=underlying_id,
            listing_id=listing_id,
            reference_id=reference_id,
        )

        await asyncio.to_thread(_run_alembic, "upgrade", D01A_REVISION, database_url)
        assert await _revision(engine) == D01A_REVISION
        await _assert_backfill(
            engine,
            listing_id=listing_id,
            reference_id=reference_id,
            workspace_id=workspace_id,
        )

        await asyncio.to_thread(_run_alembic, "downgrade", BASE_REVISION, database_url)
        assert await _revision(engine) == BASE_REVISION
        async with engine.connect() as connection:
            listing_count = await connection.scalar(
                text("SELECT count(*) FROM listings WHERE id = :id"), {"id": listing_id}
            )
            reference_count = await connection.scalar(
                text("SELECT count(*) FROM market_references WHERE id = :id"),
                {"id": reference_id},
            )
        assert listing_count == 1
        assert reference_count == 1

        await asyncio.to_thread(_run_alembic, "upgrade", D01A_REVISION, database_url)
        assert await _revision(engine) == D01A_REVISION
        await _assert_backfill(
            engine,
            listing_id=listing_id,
            reference_id=reference_id,
            workspace_id=workspace_id,
        )
    finally:
        revision = await _revision(engine)
        if revision == BASE_REVISION:
            await asyncio.to_thread(_run_alembic, "upgrade", D01A_REVISION, database_url)
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "DELETE FROM market_data_instruments "
                    "WHERE listing_id = :listing_id OR market_reference_id = :reference_id"
                ),
                {"listing_id": listing_id, "reference_id": reference_id},
            )
            await connection.execute(
                text("DELETE FROM market_references WHERE id = :id"), {"id": reference_id}
            )
            await connection.execute(
                text("DELETE FROM listings WHERE id = :id"),
                {"id": listing_id},
            )
            await connection.execute(
                text("DELETE FROM underlyings WHERE id = :id"), {"id": underlying_id}
            )
            await connection.execute(
                text("DELETE FROM trading_venues WHERE id = :id"), {"id": venue_id}
            )
            await connection.execute(
                text("DELETE FROM currencies WHERE code = :code"), {"code": currency_code}
            )
            await connection.execute(
                text("DELETE FROM workspaces WHERE id = :id"), {"id": workspace_id}
            )
        if await _revision(engine) != CURRENT_HEAD:
            await asyncio.to_thread(_run_alembic, "upgrade", CURRENT_HEAD, database_url)
        await engine.dispose()
