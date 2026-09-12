"""Cancellable catalog scheduler with a PostgreSQL deployment leader lock."""

import asyncio
from contextlib import suppress

from sqlalchemy import text

from app.features.market_data.service.refresh import MarketDataRefreshRuntime


async def run_refresh_forever(runtime: MarketDataRefreshRuntime) -> None:
    # Session lock on a dedicated connection: worker replicas cannot run overlapping
    # discovery batches. Technical quote caches/budgets remain single-process.
    lock_id = runtime.workspace_id.int % (2**63 - 1)
    while True:
        try:
            async with runtime.container.database.engine.connect() as connection:
                acquired = await connection.scalar(
                    text("SELECT pg_try_advisory_lock(:key)"),
                    {"key": lock_id},
                )
                await connection.commit()
                if acquired:
                    runtime.leader = True
                    try:
                        while True:
                            # Probe the dedicated connection before each batch; if
                            # PostgreSQL lost the session, its lock is gone as well.
                            await connection.execute(text("SELECT 1"))
                            await connection.commit()
                            runtime.wake.clear()
                            await runtime.run_once()
                            with suppress(TimeoutError):
                                await asyncio.wait_for(runtime.wake.wait(), timeout=30)
                    finally:
                        runtime.leader = False
                        await connection.execute(
                            text("SELECT pg_advisory_unlock(:key)"), {"key": lock_id}
                        )
                        await connection.commit()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            runtime.last_error = type(exc).__name__
        await asyncio.sleep(30)
