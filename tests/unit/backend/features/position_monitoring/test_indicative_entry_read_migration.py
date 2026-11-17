"""Passive readers and additive schema in explicitly synthetic disposable storage."""

import importlib
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, insert, inspect
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from starlette.requests import Request

from app.core.exceptions import ApplicationError
from app.features.position_monitoring.api.indicative_entry import read_indicative_status
from app.features.position_monitoring.persistence.indicative_entry import (
    IndicativeEntryAssessmentModel,
)
from app.features.position_monitoring.service import indicative_entry_read as module


@pytest.mark.parametrize("has_history", [False, True])
def test_review_migration_is_additive_and_refuses_history_destruction(tmp_path, has_history):
    migration = importlib.import_module("migrations.versions.20261117_0057_indicative_entry_review")
    assert migration.down_revision == "20261117_0056"
    engine = create_engine(f"sqlite:///{tmp_path}/synthetic_review_migration.db")
    try:
        with (
            engine.begin() as connection,
            Operations.context(MigrationContext.configure(connection)),
        ):
            migration.upgrade()
            assert set(inspect(connection).get_table_names()) == {
                "indicative_entry_assessments",
                "indicative_entry_episodes",
            }
            if has_history:
                connection.execute(
                    insert(IndicativeEntryAssessmentModel).values(
                        id=uuid4(),
                        workspace_id=uuid4(),
                        trade_id=uuid4(),
                        position_id=uuid4(),
                        rule_version="indicative-entry-review-v1",
                        previous_assessment_id=None,
                        input_fingerprint="1" * 64,
                        owner_basis_id="2" * 64,
                        outcome="UNAVAILABLE",
                        evaluated_at=datetime.now(UTC),
                        recorded_at=datetime.now(UTC),
                        ordering_at=None,
                        inputs={},
                        result={},
                    )
                )
                with pytest.raises(RuntimeError, match="destructive downgrade refused"):
                    migration.downgrade()
            else:
                migration.downgrade()
                assert inspect(connection).get_table_names() == []
    finally:
        engine.dispose()


@pytest.mark.asyncio
async def test_passive_reader_opens_read_only_snapshot_and_never_refreshes_or_writes(
    monkeypatch,
):
    session = Mock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.scalar = AsyncMock(side_effect=[0, 0])
    session.scalars = AsyncMock(side_effect=[(), ()])
    session.rollback = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    monkeypatch.setattr(module, "AsyncSession", Mock(return_value=session))
    monkeypatch.setattr(module, "latest_indicative_assessment", AsyncMock(return_value=None))
    workspace, trade, position = uuid4(), uuid4(), uuid4()
    monkeypatch.setattr(
        module,
        "SqlAlchemyReadOnlyTradeRepository",
        Mock(return_value=SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(id=trade)))),
    )
    monkeypatch.setattr(
        module,
        "SqlAlchemyPositionRepository",
        Mock(
            return_value=SimpleNamespace(
                get_for_trade=AsyncMock(return_value=SimpleNamespace(id=position))
            )
        ),
    )
    report = await module.IndicativeEntryReader(Mock(spec=AsyncEngine)).read(
        workspace, trade, position
    )
    assert report.read_status == "READ_ONLY"
    assert report.activation_status == "NOT_ACTIVATED"
    assert report.qualified_b04 is report.full_baseline_activated is False
    assert report.latest_assessment is None and report.assessment_count == 0
    assert "REPEATABLE READ READ ONLY" in str(session.execute.await_args_list[0].args[0])
    session.commit.assert_not_awaited()
    session.flush.assert_not_awaited()
    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query", [b"", b"position_id=a&position_id=b", b"position_id=a&refresh=true"]
)
async def test_status_api_rejects_hidden_commands_or_ambiguous_scope(query):
    reader = SimpleNamespace(read=AsyncMock())
    request = Request({"type": "http", "query_string": query})
    with pytest.raises(ApplicationError) as raised:
        await read_indicative_status(uuid4(), uuid4(), reader, request)
    assert raised.value.code == "REVIEW_POSITION_QUERY_INVALID"
    reader.read.assert_not_awaited()
