from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.features.product_selection.domain.models import ProductSelection
from app.features.product_selection.service.persistence import ProductSelectionPersistenceService


class FakeUow:
    def __init__(self):
        self.runs = Mock(add=AsyncMock())
        self.evaluations = Mock(add=AsyncMock())
        self.omissions = Mock(add_all=AsyncMock())
        self.selections = Mock(add=AsyncMock())
        self.flush = AsyncMock()
        self.commit = AsyncMock()
        self.rollback = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        if exc_type is not None:
            await self.rollback()


@pytest.mark.asyncio
async def test_persist_run_establishes_run_parent_before_evaluations_and_commit():
    uow = FakeUow()
    service = ProductSelectionPersistenceService(uow)
    run = Mock(id=uuid4())
    e1, e2 = Mock(), Mock()
    o1 = Mock()
    result = Mock(run=run, evaluations=(e1, e2), universe_omissions=(o1,))
    events: list[str] = []

    uow.runs.add.side_effect = lambda value: events.append("run")
    uow.evaluations.add.side_effect = lambda value: events.append("evaluation")
    uow.omissions.add_all.side_effect = lambda run_id, values: events.append("omissions")

    async def record_flush() -> None:
        events.append("flush")

    async def record_commit() -> None:
        events.append("commit")

    uow.flush.side_effect = record_flush
    uow.commit.side_effect = record_commit

    await service.persist_run(result)

    assert events == ["run", "flush", "evaluation", "evaluation", "omissions", "flush", "commit"]
    uow.runs.add.assert_awaited_once_with(run)
    assert uow.evaluations.add.await_count == 2
    uow.omissions.add_all.assert_awaited_once_with(run.id, (o1,))
    assert uow.flush.await_count == 2
    uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_persist_selection_is_separate_explicit_user_decision_transaction():
    uow = FakeUow()
    service = ProductSelectionPersistenceService(uow)
    selection = Mock(spec=ProductSelection)
    await service.persist_selection(selection)
    uow.selections.add.assert_awaited_once_with(selection)
    uow.commit.assert_awaited_once()
