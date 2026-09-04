from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.features.market.api.underlying_usage import ReleasedUnderlyingUsageRepository


@pytest.mark.asyncio
async def test_released_direct_fk_consumers_are_reported_as_underlying_usages() -> None:
    workspace_id = uuid4()
    underlying_id = uuid4()
    analysis_id = uuid4()
    warrant_id = uuid4()
    candidate_id = uuid4()
    results = []
    for object_id in (analysis_id, warrant_id, candidate_id):
        scalar_result = MagicMock()
        scalar_result.all.return_value = [object_id]
        results.append(scalar_result)
    session = MagicMock()
    session.scalars = AsyncMock(side_effect=results)

    repository = ReleasedUnderlyingUsageRepository(session)

    usages = await repository.list_for_underlying(workspace_id, underlying_id)

    assert [(usage.reference_type, usage.object_id) for usage in usages] == [
        ("MARKET_ANALYSIS", analysis_id),
        ("WARRANT", warrant_id),
        ("CANDIDATE", candidate_id),
    ]
    assert session.scalars.await_count == 3
