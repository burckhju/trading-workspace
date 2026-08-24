from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def _constraints(
    session: AsyncSession,
    table: str,
) -> dict[str, str]:
    rows = await session.execute(
        text(
            """
            select
                c.conname,
                pg_get_constraintdef(c.oid, true)
            from pg_constraint c
            join pg_class t on t.oid = c.conrelid
            where t.relname = :table
            """
        ),
        {"table": table},
    )
    return {row[0]: row[1] for row in rows}


async def _index_names(
    session: AsyncSession,
    table: str,
) -> set[str]:
    rows = await session.execute(
        text(
            """
            select indexname
            from pg_indexes
            where tablename = :table
            """
        ),
        {"table": table},
    )
    return {row[0] for row in rows}


async def test_external_observation_same_aggregate_current_fk_exists(
    learning_session: AsyncSession,
) -> None:
    constraints = await _constraints(
        learning_session,
        "external_observations",
    )
    assert "fk_external_observations_current_version_same_observation" in constraints


async def test_import_row_lifecycle_check_exists(
    learning_session: AsyncSession,
) -> None:
    constraints = await _constraints(
        learning_session,
        "external_observation_import_rows",
    )
    check_defs = [
        definition for definition in constraints.values() if definition.startswith("CHECK")
    ]

    assert any(
        "disposition" in definition
        and "PENDING" in definition
        and "ACCEPTED" in definition
        and "DISCARDED" in definition
        and "accepted_external_observation_version_id" in definition
        for definition in check_defs
    )


async def test_recording_provenance_check_exists(
    learning_session: AsyncSession,
) -> None:
    constraints = await _constraints(
        learning_session,
        "external_observation_versions",
    )
    check_defs = [
        definition for definition in constraints.values() if definition.startswith("CHECK")
    ]

    assert any(
        "recording_method" in definition
        and "FILE_IMPORT" in definition
        and "MANUAL" in definition
        and "imported_at" in definition
        and "import_row_id" in definition
        for definition in check_defs
    )


async def test_external_journal_open_draft_unique_index_exists(
    learning_session: AsyncSession,
) -> None:
    names = await _index_names(
        learning_session,
        "external_observation_journal_versions",
    )
    assert "uq_external_observation_journal_versions_open_draft" in names
