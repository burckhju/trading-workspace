"""PostgreSQL invariants for the D01-B provider-mapping instrument boundary."""

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
    database_name = url.split("?", 1)[0].rsplit("/", 1)[-1]
    if database_name != "trading_workspace_test":
        pytest.fail("D01-B integration test may run only against trading_workspace_test")
    return url


@pytest.mark.asyncio
async def test_provider_mapping_rejects_instrument_from_other_workspace() -> None:
    engine = create_async_engine(_test_database_url())
    workspace_a = uuid4()
    workspace_b = uuid4()
    reference_id = uuid4()
    instrument_id = uuid4()

    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            now = datetime.now(UTC)
            await connection.execute(
                text(
                    "INSERT INTO workspaces (id, name, created_at) "
                    "VALUES (:id_a, 'D01-B A', :now), (:id_b, 'D01-B B', :now)"
                ),
                {"id_a": workspace_a, "id_b": workspace_b, "now": now},
            )
            await connection.execute(
                text(
                    "INSERT INTO market_references "
                    "(id, workspace_id, code, name, reference_type, region, role, "
                    "reference_version, active, created_at) "
                    "VALUES (:id, :workspace_id, :code, 'D01-B Reference', "
                    "'INDEX', 'GLOBAL', 'BENCHMARK', 'd01b-test', true, :now)"
                ),
                {
                    "id": reference_id,
                    "workspace_id": workspace_a,
                    "code": f"D01B-{str(reference_id)[:8]}",
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
                            "INSERT INTO provider_instrument_mappings "
                            "(id, workspace_id, listing_id, market_data_instrument_id, provider, "
                            "provider_symbol, provider_exchange_code, status, validated_at, "
                            "validation_message, created_at, updated_at, version) "
                            "VALUES (:id, :workspace_id, NULL, :instrument_id, 'EODHD', "
                            ":symbol, 'INDX', 'DISABLED', NULL, 'd01b-test', :now, :now, 1)"
                        ),
                        {
                            "id": uuid4(),
                            "workspace_id": workspace_b,
                            "instrument_id": instrument_id,
                            "symbol": f"D01B{str(instrument_id.int)[-8:]}",
                            "now": now,
                        },
                    )
        finally:
            await transaction.rollback()
    await engine.dispose()
