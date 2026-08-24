from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def _constraints(session: AsyncSession, table: str) -> dict[str, str]:
    rows = await session.execute(
        text(
            """
            select c.conname, pg_get_constraintdef(c.oid, true)
            from pg_constraint c
            join pg_class t on t.oid = c.conrelid
            where t.relname = :table
            """
        ),
        {"table": table},
    )
    return {row[0]: row[1] for row in rows}


async def test_review_signal_open_partial_unique_exists(learning_session: AsyncSession) -> None:
    row = (
        await learning_session.execute(
            text(
                """
                select indexdef
                from pg_indexes
                where tablename = 'lesson_review_signals'
                  and indexname = 'uq_lesson_review_signals_open'
                """
            )
        )
    ).one()
    assert "UNIQUE INDEX" in row[0]
    assert "WHERE" in row[0]
    assert "OPEN" in row[0]


async def test_review_signal_lifecycle_check_exists(learning_session: AsyncSession) -> None:
    checks = [
        v
        for v in (await _constraints(learning_session, "lesson_review_signals")).values()
        if v.startswith("CHECK")
    ]
    assert any("OPEN" in v and "RESOLVED" in v and "NEW_VERSION_CREATED" in v for v in checks)


async def test_suggestion_lifecycle_check_exists(learning_session: AsyncSession) -> None:
    checks = [
        v
        for v in (await _constraints(learning_session, "lesson_suggestions")).values()
        if v.startswith("CHECK")
    ]
    assert any("SUGGESTED" in v and "REJECTED" in v and "CONFIRMED" in v for v in checks)


async def test_tag_workspace_normalized_unique_exists(learning_session: AsyncSession) -> None:
    constraints = await _constraints(learning_session, "lesson_tags")
    assert any("UNIQUE (workspace_id, normalized_name)" in v for v in constraints.values())
