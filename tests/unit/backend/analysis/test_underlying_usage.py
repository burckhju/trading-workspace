from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.features.analysis.service.underlying_usage import (
    MarketAnalysisUnderlyingUsageRepository,
)


@pytest.mark.asyncio
async def test_market_analysis_is_reported_as_underlying_usage() -> None:
    workspace_id = uuid4()
    underlying_id = uuid4()
    analysis_ids = [uuid4(), uuid4()]
    scalar_result = MagicMock()
    scalar_result.all.return_value = analysis_ids
    session = MagicMock()
    session.scalars = AsyncMock(return_value=scalar_result)

    repository = MarketAnalysisUnderlyingUsageRepository(session)

    usages = await repository.list_for_underlying(workspace_id, underlying_id)

    assert [(usage.reference_type, usage.object_id) for usage in usages] == [
        ("MARKET_ANALYSIS", analysis_ids[0]),
        ("MARKET_ANALYSIS", analysis_ids[1]),
    ]
    session.scalars.assert_awaited_once()
