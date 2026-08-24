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


async def test_lesson_state_vocabulary_is_authoritative(learning_session: AsyncSession) -> None:
    constraints = await _constraints(learning_session, "lessons")
    checks = [value for value in constraints.values() if value.startswith("CHECK")]
    assert any(
        "CURRENT" in value
        and "REVIEW_RECOMMENDED" in value
        and "RETIRED" in value
        and "STALE" not in value
        for value in checks
    )


async def test_lesson_current_version_fk_is_deferred_same_aggregate(
    learning_session: AsyncSession,
) -> None:
    row = (
        await learning_session.execute(
            text(
                """
                select c.condeferrable, c.condeferred, pg_get_constraintdef(c.oid, true)
                from pg_constraint c
                join pg_class t on t.oid = c.conrelid
                where t.relname = 'lessons'
                  and c.conname = 'fk_lessons_current_version_same_lesson'
                """
            )
        )
    ).one()
    assert row[0] is True
    assert row[1] is True
    assert "FOREIGN KEY (id, current_version_id)" in row[2]
    assert "REFERENCES lesson_versions(lesson_id, id)" in row[2]


async def test_lesson_evidence_relationship_check_exists(learning_session: AsyncSession) -> None:
    constraints = await _constraints(learning_session, "lesson_evidence_links")
    checks = [value for value in constraints.values() if value.startswith("CHECK")]
    assert any(
        "SUPPORTS" in value and "CONTRADICTS" in value and "CONTEXTUAL" in value for value in checks
    )


async def test_lesson_state_transition_forbids_same_state(
    learning_session: AsyncSession,
) -> None:
    constraints = await _constraints(
        learning_session,
        "lesson_state_transitions",
    )
    matching = [definition for name, definition in constraints.items() if "state_changes" in name]
    assert len(matching) == 1
    assert "from_state" in matching[0]
    assert "to_state" in matching[0]
