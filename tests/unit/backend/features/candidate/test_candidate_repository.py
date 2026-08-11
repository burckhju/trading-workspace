from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.features.candidate.persistence.repositories import (
    SqlAlchemyCandidateRepository,
)


def _session():
    s = Mock()
    s.scalar = AsyncMock()
    s.scalars = AsyncMock()
    s.add = Mock()
    s.add_all = Mock()
    s.commit = AsyncMock()
    return s


@pytest.mark.asyncio
async def test_candidate_repository_crud_query_helpers():
    session = _session()
    repo = SqlAlchemyCandidateRepository(session)
    workspace, candidate, underlying, evaluation = (uuid4() for _ in range(4))

    session.scalar.return_value = underlying
    assert await repo.underlying_exists(workspace, underlying)
    marker = object()
    session.scalar.return_value = marker
    assert await repo.get_by_underlying(workspace, underlying) is marker
    assert await repo.get(workspace, candidate) is marker

    rows = Mock()
    rows.all.return_value = [marker]
    session.scalars.return_value = rows
    assert await repo.list(workspace) == (marker,)
    assert await repo.list_evaluations(candidate) == (marker,)
    assert await repo.list_criteria(evaluation) == (marker,)

    session.scalar.return_value = None
    assert await repo.next_evaluation_version(candidate) == 1
    session.scalar.return_value = 4
    assert await repo.next_evaluation_version(candidate) == 5

    repo.add(marker)
    repo.add_all([marker])
    await repo.commit()
    session.add.assert_called_once_with(marker)
    session.add_all.assert_called_once_with([marker])
    session.commit.assert_awaited_once()
