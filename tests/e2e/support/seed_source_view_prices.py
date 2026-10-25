"""Synthetic EOD-only fixture for the independently marked report browser stack.

Trading facts are created through HTTP owners, never by this fixture. This seed
uses the established twenty-observation fixture values, not provider data. The
report guard, database marker and exact observation relation are checked before
any INSERT. It must never adopt a configured user database or re-seed a listing.
"""

import asyncio
import os
import sys
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

from realized_gross_database_guard import verify
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool


async def seed(trade_id: UUID, listing_id: UUID) -> None:
    state = await verify()
    engine = create_async_engine(
        os.environ["TRADING_WORKSPACE_TEST_DATABASE_URL"], poolclass=NullPool
    )
    workspace = UUID("00000000-0000-4000-8000-000000000001")
    try:
        async with engine.begin() as connection:
            database = await connection.scalar(text("SELECT current_database()"))
            marker = await connection.scalar(
                text(
                    "SELECT shobj_description(oid, 'pg_database') FROM pg_database "
                    "WHERE datname=current_database()"
                )
            )
            assert database == state["database"]
            assert marker == f"synthetic realized-gross browser {state['run_id']}"
            relation = await connection.scalar(
                text(
                    "SELECT count(*) FROM post_trade_observations "
                    "WHERE trade_id=:trade AND underlying_listing_id=:listing "
                    "AND workspace_id=:workspace AND status='ACTIVE'"
                ),
                {"trade": trade_id, "listing": listing_id, "workspace": workspace},
            )
            assert relation == 1, "A real owner-created observation is required"
            count = await connection.scalar(
                text("SELECT count(*) FROM daily_prices WHERE listing_id=:listing"),
                {"listing": listing_id},
            )
            assert count == 0, "Never replace or append to an existing price history"
            now = datetime.now(UTC)
            day = date(2026, 8, 19)
            observations = []
            while len(observations) < 20:
                if day.weekday() < 5:
                    assert day < now.date(), "No future synthetic price observations"
                    observations.append(
                        dict(
                            id=uuid4(),
                            workspace=workspace,
                            listing=listing_id,
                            day=day,
                            now=now,
                        )
                    )
                day += timedelta(days=1)
            await connection.execute(
                text(
                    "INSERT INTO daily_prices "
                    "(id,workspace_id,listing_id,trading_date,open,high,low,close,currency,"
                    "provider,provider_symbol,retrieved_at,source_updated_at,quality_status,"
                    "warnings,price_type,created_at,updated_at) "
                    "VALUES(:id,:workspace,:listing,:day,100,105,95,102,'EUR','EODHD',"
                    "'SYNTHETIC-NO-PROVIDER',:now,NULL,'VALID',"
                    "'synthetic source-view qualification observations','EOD',:now,:now)"
                ),
                observations,
            )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed(UUID(sys.argv[1]), UUID(sys.argv[2])))
