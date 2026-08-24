from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncEngine

import app.features.learning.persistence.models  # noqa: F401
from app.database.base import Base

TABLES = {
    "external_observation_trade_link_versions",
    "external_observation_trade_links",
    "lesson_tag_assignments",
    "lesson_tags",
    "lesson_suggestions",
    "lesson_review_signal_evidence",
    "lesson_review_signals",
    "lesson_state_transitions",
    "lesson_evidence_links",
    "lesson_versions",
    "lessons",
    "external_observation_journal_version_evidence",
    "external_observation_evidence",
    "trade_journal_version_evidence",
    "ft011_evidence",
    "learning_evidence",
    "external_observation_import_batches",
    "external_observation_import_rows",
    "external_observation_import_row_issues",
    "external_observations",
    "external_observation_versions",
    "external_observation_journals",
    "external_observation_journal_versions",
}


async def _database_columns(
    engine: AsyncEngine,
) -> dict[str, set[str]]:
    async with engine.connect() as connection:

        def inspect_columns(sync_connection):
            inspector = inspect(sync_connection)
            return {
                table: {column["name"] for column in inspector.get_columns(table)}
                for table in TABLES
            }

        return await connection.run_sync(inspect_columns)


async def test_learning_orm_tables_3_to_9_match_database_columns(
    learning_test_engine: AsyncEngine,
) -> None:
    database = await _database_columns(learning_test_engine)

    for table_name in sorted(TABLES):
        orm_table = Base.metadata.tables[table_name]
        orm_columns = {column.name for column in orm_table.columns}

        assert database[table_name] == orm_columns, (
            table_name,
            sorted(database[table_name] - orm_columns),
            sorted(orm_columns - database[table_name]),
        )


def test_learning_tables_3_to_9_are_registered_in_metadata() -> None:
    assert set(Base.metadata.tables) >= TABLES
