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
async def test_persist_run_writes_complete_snapshot_before_commit():
    uow = FakeUow()
    service = ProductSelectionPersistenceService(uow)
    run = Mock(id=uuid4())
    e1, e2 = Mock(), Mock()
    o1 = Mock()
    result = Mock(run=run, evaluations=(e1, e2), universe_omissions=(o1,))
    await service.persist_run(result)
    uow.runs.add.assert_awaited_once_with(run)
    assert uow.evaluations.add.await_count == 2
    uow.omissions.add_all.assert_awaited_once_with(run.id, (o1,))
    uow.flush.assert_awaited_once()
    uow.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_persist_selection_is_separate_explicit_user_decision_transaction():
    uow = FakeUow()
    service = ProductSelectionPersistenceService(uow)
    selection = Mock(spec=ProductSelection)
    await service.persist_selection(selection)
    uow.selections.add.assert_awaited_once_with(selection)
    uow.commit.assert_awaited_once()
