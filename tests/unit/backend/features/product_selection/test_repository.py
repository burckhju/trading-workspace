from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.features.product_selection.persistence.repositories import (
    SqlAlchemyProductSelectionRepository,
    SqlAlchemyProductSelectionRunRepository,
)


def _session():
    s = Mock()
    s.scalar = AsyncMock()
    s.scalars = AsyncMock()
    s.add = Mock()
    s.add_all = Mock()
    return s


@pytest.mark.asyncio
async def test_run_repository_returns_none_for_unknown_workspace_run():
    s = _session()
    repo = SqlAlchemyProductSelectionRunRepository(s)
    s.scalar.return_value = None
    assert await repo.get(uuid4(), uuid4()) is None


@pytest.mark.asyncio
async def test_selection_repository_returns_none_when_user_has_not_selected():
    s = _session()
    repo = SqlAlchemyProductSelectionRepository(s)
    s.scalar.return_value = None
    assert await repo.get_for_run(uuid4()) is None
