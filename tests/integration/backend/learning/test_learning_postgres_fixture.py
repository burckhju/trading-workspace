from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession


async def test_learning_fixture_is_on_ft012_head(
    learning_test_engine: AsyncEngine,
) -> None:
    async with learning_test_engine.connect() as connection:
        revision = await connection.scalar(text("select version_num from alembic_version"))
    assert revision == "20260824_0021"


async def test_learning_session_is_live(
    learning_session: AsyncSession,
) -> None:
    value = await learning_session.scalar(text("select 1"))
    assert value == 1
