"""Real history guards in the existing uniquely named disposable PostgreSQL fixture."""

import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.integration.backend.database import test_saved_quote_evidence_postgres as saved
from tests.integration.backend.database.test_product_price_scale_evidence_postgres import engine_for
from tests.integration.backend.test_usd_chf_currency_references import _migrate

readiness_database = saved.quote_database
forbid_outbound_http = saved.forbid_outbound_http


@pytest.mark.parametrize("table", ["product_review_documents", "review_calendar_sources"])
def test_original_history_cannot_be_truncated_even_when_empty(readiness_database, table):
    _migrate(readiness_database, "head")

    async def exercise():
        engine = engine_for(readiness_database)
        sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
        try:
            async with sessions() as session:
                # Table names are the fixed parameter list above, never user input.
                before = await session.scalar(text(f"SELECT count(*) FROM {table}"))
                with pytest.raises(IntegrityError, match="readiness originals are append-only"):
                    await session.execute(text(f"TRUNCATE {table} CASCADE"))
                await session.rollback()
                assert await session.scalar(text(f"SELECT count(*) FROM {table}")) == before
        finally:
            await engine.dispose()

    asyncio.run(exercise())
