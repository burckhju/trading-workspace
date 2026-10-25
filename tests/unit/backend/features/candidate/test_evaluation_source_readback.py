"""The existing evaluation read exposes stored sources without resolving latest."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.features.candidate.api.router import WORKSPACE_ID, list_candidate_evaluations


@pytest.mark.asyncio
async def test_evaluation_readback_keeps_exact_historical_sources() -> None:
    candidate_id, evaluation_id, analysis_id = (uuid4() for _ in range(3))
    evaluation = SimpleNamespace(
        id=evaluation_id,
        version=2,
        direction="LONG",
        model_id="TOP_DOWN_CANDIDATE",
        model_version="2",
        qualification="NOT_QUALIFIED",
        quality_status="GOOD",
        warnings=[],
        evaluated_at=datetime(2026, 10, 24, 12, tzinfo=UTC),
    )
    source = SimpleNamespace(
        role="MARKET",
        source_type="ANALYSIS",
        source_id=analysis_id,
        source_version=3,
        model_id="EOD_TREND_MOMENTUM",
        model_version="1.0.0",
    )
    service = SimpleNamespace(
        get=AsyncMock(),
        list_evaluations=AsyncMock(return_value=(evaluation,)),
        list_criteria=AsyncMock(return_value=()),
        list_sources=AsyncMock(return_value=(source,)),
    )

    result = await list_candidate_evaluations(candidate_id, service)

    assert len(result) == 1
    assert result[0].model_version == "2"
    assert [item.model_dump() for item in result[0].sources] == [vars(source)]
    service.get.assert_awaited_once_with(WORKSPACE_ID, candidate_id)
    service.list_sources.assert_awaited_once_with(evaluation_id)


@pytest.mark.asyncio
async def test_foreign_candidate_is_rejected_before_source_read() -> None:
    service = SimpleNamespace(
        get=AsyncMock(side_effect=ValueError("candidate not found")),
        list_evaluations=AsyncMock(),
        list_sources=AsyncMock(),
    )
    with pytest.raises(ValueError, match="candidate not found"):
        await list_candidate_evaluations(uuid4(), service)
    service.list_evaluations.assert_not_awaited()
    service.list_sources.assert_not_awaited()
