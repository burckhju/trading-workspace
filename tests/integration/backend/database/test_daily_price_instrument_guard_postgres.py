"""PostgreSQL invariants for the D01-C DailyPrice identity boundary."""

from __future__ import annotations

import os
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine


def _test_database_url() -> str:
    url = os.environ.get("TRADING_WORKSPACE_TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TRADING_WORKSPACE_TEST_DATABASE_URL is not configured")
    if url.split("?", 1)[0].rsplit("/", 1)[-1] != "trading_workspace_test":
        pytest.fail("D01-C integration test may run only against trading_workspace_test")
    return url


@pytest.mark.asyncio
async def test_daily_price_rejects_cross_workspace_instrument() -> None:
    engine = create_async_engine(_test_database_url())
    workspace_a = uuid4()
    workspace_b = uuid4()
    reference_id = uuid4()
    instrument_id = uuid4()
    currency_code = "G" + workspace_a.hex[-2:].upper()
    now = datetime.now(UTC)

    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            await connection.execute(
                text(
                    "INSERT INTO workspaces (id, name, created_at) VALUES "
                    "(:id_a, 'D01-C Guard A', :now), (:id_b, 'D01-C Guard B', :now)"
                ),
                {"id_a": workspace_a, "id_b": workspace_b, "now": now},
            )
            await connection.execute(
                text(
                    "INSERT INTO currencies "
                    "(code, name, minor_unit, is_active, reference_version, "
                    "created_at, updated_at) "
                    "VALUES (:code, 'D01-C Guard Currency', 2, true, "
                    "'d01c-guard', :now, :now)"
                ),
                {"code": currency_code, "now": now},
            )
            await connection.execute(
                text(
                    "INSERT INTO market_references "
                    "(id, workspace_id, code, name, reference_type, region, role, "
                    "reference_version, active, created_at) "
                    "VALUES (:id, :workspace_id, :code, 'D01-C Guard Reference', 'INDEX', "
                    "'GLOBAL', 'BENCHMARK', 'd01c-guard', true, :now)"
                ),
                {
                    "id": reference_id,
                    "workspace_id": workspace_a,
                    "code": f"D01C-{str(reference_id)[:8]}",
                    "now": now,
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO market_data_instruments "
                    "(id, workspace_id, kind, listing_id, market_reference_id, created_at) "
                    "VALUES (:id, :workspace_id, 'MARKET_REFERENCE', NULL, :reference_id, :now)"
                ),
                {
                    "id": instrument_id,
                    "workspace_id": workspace_a,
                    "reference_id": reference_id,
                    "now": now,
                },
            )

            with pytest.raises(IntegrityError):
                async with connection.begin_nested():
                    await connection.execute(
                        text(
                            "INSERT INTO daily_prices "
                            "(id, workspace_id, listing_id, market_data_instrument_id, "
                            "trading_date, open, high, low, close, adjusted_close, volume, "
                            "currency, provider, provider_symbol, retrieved_at, source_updated_at, "
                            "quality_status, warnings, price_type, created_at, updated_at) "
                            "VALUES (:id, :workspace_id, NULL, :instrument_id, :trading_date, "
                            "100, 102, 99, 101, NULL, 1000, :currency, 'EODHD', 'D01C.GUARD', "
                            ":now, NULL, 'VALID', '', 'EOD', :now, :now)"
                        ),
                        {
                            "id": uuid4(),
                            "workspace_id": workspace_b,
                            "instrument_id": instrument_id,
                            "trading_date": date(2026, 8, 25),
                            "currency": currency_code,
                            "now": now,
                        },
                    )
        finally:
            await transaction.rollback()
    await engine.dispose()
