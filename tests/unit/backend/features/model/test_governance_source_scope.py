"""Exercise the owner's actual source SELECT on an isolated in-memory query store.

This is a deterministic query regression, not PostgreSQL persistence evidence.
The native companion covers the same command against the migrated schema.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

from app.features.model.service.application import ModelGovernanceService


@pytest.mark.asyncio
async def test_generic_hypothesis_rejects_foreign_lesson_before_any_write() -> None:
    workspace_id, foreign_workspace, lesson_id, version_id = (uuid4() for _ in range(4))
    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.connect() as connection:
            # No configured/user database is consulted; the store has no file.
            assert connection.execute(text("PRAGMA database_list")).one()[2] == ""
            connection.execute(text("CREATE TABLE lessons (id CHAR(32), workspace_id CHAR(32))"))
            connection.execute(
                text("CREATE TABLE lesson_versions (id CHAR(32), lesson_id CHAR(32))")
            )
            connection.execute(
                text("INSERT INTO lessons VALUES (:id, :workspace)"),
                {"id": lesson_id.hex, "workspace": foreign_workspace.hex},
            )
            connection.execute(
                text("INSERT INTO lesson_versions VALUES (:id, :lesson)"),
                {"id": version_id.hex, "lesson": lesson_id.hex},
            )
            session = SimpleNamespace(
                scalar=AsyncMock(side_effect=connection.scalar),
                scalars=AsyncMock(),
                add=Mock(),
                flush=AsyncMock(),
                commit=AsyncMock(),
                rollback=AsyncMock(),
            )
            with pytest.raises(ValueError, match="source lesson version not found"):
                await ModelGovernanceService(session).create_hypothesis(
                    workspace_id=workspace_id,
                    title="Synthetic foreign-source rejection",
                    statement="A different workspace's lesson is not an authorized source.",
                    evidence_ids=(),
                    source_lesson_version_id=version_id,
                    actor=uuid4(),
                )
            session.add.assert_not_called()
            session.flush.assert_not_awaited()
            session.commit.assert_not_awaited()
    finally:
        engine.dispose()
