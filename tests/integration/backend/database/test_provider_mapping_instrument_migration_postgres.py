"""PostgreSQL qualification for the D01-B provider-mapping boundary."""

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

BASE_REVISION = "20260826_0025"
D01B_REVISION = "20260826_0026"
CURRENT_HEAD = "20260827_0028"
EXPECTED_DATABASE = "trading_workspace_test"


def _test_database_url() -> str:
    url = os.environ.get("TRADING_WORKSPACE_TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TRADING_WORKSPACE_TEST_DATABASE_URL is not configured")
    if url.split("?", 1)[0].rsplit("/", 1)[-1] != EXPECTED_DATABASE:
        pytest.fail(f"D01-B migration test may run only against {EXPECTED_DATABASE}")
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


async def _insert_listing_and_mapping(
    engine: AsyncEngine,
    *,
    workspace_id: UUID,
    venue_id: UUID,
    underlying_id: UUID,
    listing_id: UUID,
    mapping_id: UUID,
    currency_code: str,
    mic: str,
) -> None:
    now = datetime.now(UTC)
    async with engine.begin() as connection:
        await connection.execute(
            text("INSERT INTO workspaces (id, name, created_at) VALUES (:id, :name, :now)"),
            {"id": workspace_id, "name": f"D01-B {workspace_id}", "now": now},
        )
        await connection.execute(
            text(
                "INSERT INTO currencies "
                "(code, name, minor_unit, is_active, reference_version, created_at, updated_at) "
                "VALUES (:code, 'D01-B Currency', 2, true, 'd01b-test', :now, :now)"
            ),
            {"code": currency_code, "now": now},
        )
        await connection.execute(
            text(
                "INSERT INTO trading_venues "
                "(id, mic, name, country_code, timezone, is_active, reference_version, "
                "version, created_at, updated_at) "
                "VALUES (:id, :mic, 'D01-B Venue', 'DE', 'Europe/Berlin', true, "
                "'d01b-test', 1, :now, :now)"
            ),
            {"id": venue_id, "mic": mic, "now": now},
        )
        await connection.execute(
            text(
                "INSERT INTO underlyings "
                "(id, workspace_id, type, name, isin, wkn, lifecycle_status, quality_status, "
                "version, created_at, updated_at, data_origin) "
                "VALUES (:id, :workspace_id, 'STOCK', 'D01-B Underlying', NULL, NULL, "
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
                "ticker": f"B{str(listing_id.int)[-7:]}",
                "currency": currency_code,
                "now": now,
            },
        )
        identity_count = await connection.scalar(
            text("SELECT count(*) FROM market_data_instruments WHERE listing_id = :id"),
            {"id": listing_id},
        )
        assert identity_count == 0
        await connection.execute(
            text(
                "INSERT INTO provider_instrument_mappings "
                "(id, workspace_id, listing_id, provider, provider_symbol, "
                "provider_exchange_code, status, validated_at, validation_message, "
                "created_at, updated_at, version) "
                "VALUES (:id, :workspace_id, :listing_id, 'EODHD', :symbol, 'XETRA', "
                "'DISABLED', NULL, 'd01b-test', :now, :now, 1)"
            ),
            {
                "id": mapping_id,
                "workspace_id": workspace_id,
                "listing_id": listing_id,
                "symbol": f"D01B{str(mapping_id.int)[-8:]}",
                "now": now,
            },
        )


@pytest.mark.asyncio
async def test_d01b_upgrade_backfills_mapping_and_missing_listing_identity() -> None:
    database_url = _test_database_url()
    engine = create_async_engine(database_url, pool_pre_ping=True)
    workspace_id = uuid4()
    venue_id = uuid4()
    underlying_id = uuid4()
    listing_id = uuid4()
    mapping_id = uuid4()
    currency_code = f"{workspace_id.int % 676:02X}"[-2:] + "X"
    mic = f"B{venue_id.int % 1000:03d}"

    try:
        current = await _revision(engine)
        if current == CURRENT_HEAD:
            await asyncio.to_thread(_run_alembic, "downgrade", D01B_REVISION, database_url)
        elif current != D01B_REVISION:
            pytest.fail(f"unexpected Alembic revision for D01-B qualification: {current}")

        await asyncio.to_thread(_run_alembic, "downgrade", BASE_REVISION, database_url)
        await _insert_listing_and_mapping(
            engine,
            workspace_id=workspace_id,
            venue_id=venue_id,
            underlying_id=underlying_id,
            listing_id=listing_id,
            mapping_id=mapping_id,
            currency_code=currency_code,
            mic=mic,
        )

        await asyncio.to_thread(_run_alembic, "upgrade", D01B_REVISION, database_url)
        assert await _revision(engine) == D01B_REVISION

        async with engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT mapping.listing_id, mapping.market_data_instrument_id, "
                            "instrument.kind, instrument.listing_id AS instrument_listing_id "
                            "FROM provider_instrument_mappings AS mapping "
                            "JOIN market_data_instruments AS instrument "
                            "ON instrument.id = mapping.market_data_instrument_id "
                            "WHERE mapping.id = :mapping_id"
                        ),
                        {"mapping_id": mapping_id},
                    )
                )
                .mappings()
                .one()
            )

        assert row["listing_id"] == listing_id
        assert row["market_data_instrument_id"] is not None
        assert row["kind"] == "LISTING"
        assert row["instrument_listing_id"] == listing_id

        await asyncio.to_thread(_run_alembic, "downgrade", BASE_REVISION, database_url)
        assert await _revision(engine) == BASE_REVISION
        async with engine.connect() as connection:
            mapping_count = await connection.scalar(
                text("SELECT count(*) FROM provider_instrument_mappings WHERE id = :id"),
                {"id": mapping_id},
            )
            identity_count = await connection.scalar(
                text("SELECT count(*) FROM market_data_instruments WHERE listing_id = :id"),
                {"id": listing_id},
            )
        assert mapping_count == 1
        assert identity_count == 1

        await asyncio.to_thread(_run_alembic, "upgrade", D01B_REVISION, database_url)
        assert await _revision(engine) == D01B_REVISION
    finally:
        revision = await _revision(engine)
        if revision == BASE_REVISION:
            await asyncio.to_thread(_run_alembic, "upgrade", D01B_REVISION, database_url)
        async with engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM provider_instrument_mappings WHERE id = :id"),
                {"id": mapping_id},
            )
            await connection.execute(
                text("DELETE FROM market_data_instruments WHERE listing_id = :id"),
                {"id": listing_id},
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
