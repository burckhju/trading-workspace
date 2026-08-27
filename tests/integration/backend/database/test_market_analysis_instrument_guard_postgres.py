"""PostgreSQL invariants for the D01-D MarketAnalysis identity boundary."""

from __future__ import annotations

import os
from datetime import UTC, datetime
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
        pytest.fail("D01-D integration test may run only against trading_workspace_test")
    return url


@pytest.mark.asyncio
async def test_market_analysis_rejects_cross_workspace_instrument() -> None:
    engine = create_async_engine(_test_database_url())
    workspace_a = uuid4()
    workspace_b = uuid4()
    reference_id = uuid4()
    instrument_id = uuid4()
    now = datetime.now(UTC)

    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            await connection.execute(
                text(
                    "INSERT INTO workspaces (id, name, created_at) VALUES "
                    "(:id_a, 'D01-D Guard A', :now), (:id_b, 'D01-D Guard B', :now)"
                ),
                {"id_a": workspace_a, "id_b": workspace_b, "now": now},
            )
            await connection.execute(
                text(
                    "INSERT INTO market_references "
                    "(id, workspace_id, code, name, reference_type, region, role, "
                    "reference_version, active, created_at) "
                    "VALUES (:id, :workspace_id, :code, 'D01-D Guard Reference', 'INDEX', "
                    "'GLOBAL', 'BENCHMARK', 'd01d-guard', true, :now)"
                ),
                {
                    "id": reference_id,
                    "workspace_id": workspace_a,
                    "code": f"D01D-{str(reference_id)[:8]}",
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
                            "INSERT INTO market_analyses "
                            "(id, workspace_id, market_data_instrument_id, underlying_id, "
                            "listing_id, created_at, created_by) "
                            "VALUES (:id, :workspace_id, :instrument_id, NULL, NULL, "
                            ":now, 'd01d-test')"
                        ),
                        {
                            "id": uuid4(),
                            "workspace_id": workspace_b,
                            "instrument_id": instrument_id,
                            "now": now,
                        },
                    )
        finally:
            await transaction.rollback()
    await engine.dispose()
