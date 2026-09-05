from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from app.features.product_selection.persistence.repositories import (
    SqlAlchemyProductEvaluationRepository,
    SqlAlchemyProductSelectionRepository,
    SqlAlchemyProductSelectionRunRepository,
)


def _session():
    s = Mock()
    s.scalar = AsyncMock()
    s.scalars = AsyncMock()
    s.flush = AsyncMock()
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
async def test_evaluation_repository_flushes_root_before_fk_dependent_evidence():
    s = _session()
    repo = SqlAlchemyProductEvaluationRepository(s)
    evaluation = Mock()
    root = Mock()
    inputs = (Mock(),)
    criteria = (Mock(),)
    metrics = (Mock(),)
    reasons = (Mock(),)
    events: list[str] = []

    s.add.side_effect = lambda value: events.append("root")

    async def record_flush() -> None:
        events.append("flush")

    s.flush.side_effect = record_flush
    s.add_all.side_effect = lambda values: events.append("evidence")

    with patch(
        "app.features.product_selection.persistence.repositories.evaluation_to_models",
        return_value=(root, inputs, criteria, metrics, reasons),
    ):
        await repo.add(evaluation)

    assert events == ["root", "flush", "evidence"]
    s.add.assert_called_once_with(root)
    s.flush.assert_awaited_once()
    s.add_all.assert_called_once_with([*inputs, *criteria, *metrics, *reasons])


@pytest.mark.asyncio
async def test_selection_repository_returns_none_when_user_has_not_selected():
    s = _session()
    repo = SqlAlchemyProductSelectionRepository(s)
    s.scalar.return_value = None
    assert await repo.get_for_run(uuid4()) is None
