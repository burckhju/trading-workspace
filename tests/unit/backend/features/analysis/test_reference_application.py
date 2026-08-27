from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.features.analysis.domain.errors import AnalysisDataUnavailable
from app.features.analysis.service.reference_application import MarketReferenceAnalysisService


@pytest.mark.asyncio
async def test_create_market_reference_analysis_persists_listing_free_owner() -> None:
    workspace_id = uuid4()
    reference_id = uuid4()
    instrument_id = uuid4()
    session = AsyncMock()
    repository = SimpleNamespace(add_analysis=AsyncMock(), add_event=AsyncMock())
    identity = SimpleNamespace(
        for_market_reference=AsyncMock(return_value=SimpleNamespace(id=instrument_id))
    )
    service = MarketReferenceAnalysisService(session)
    service._repo = repository
    service._identity = identity
    service._active_reference = AsyncMock(return_value=SimpleNamespace(id=reference_id))

    analysis = await service.create_for_market_reference(
        workspace_id=workspace_id,
        market_reference_id=reference_id,
        actor="post-d01-coverage",
    )

    assert analysis.workspace_id == workspace_id
    assert analysis.market_data_instrument_id == instrument_id
    assert analysis.underlying_id is None
    assert analysis.listing_id is None
    assert analysis.created_by == "post-d01-coverage"
    repository.add_analysis.assert_awaited_once_with(analysis)
    session.flush.assert_awaited_once_with()
    repository.add_event.assert_awaited_once()
    event = repository.add_event.await_args.args[0]
    assert event.analysis_id == analysis.id
    assert event.event_type == "CREATED"
    assert event.to_status == "DRAFT"
    session.commit.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_create_market_reference_analysis_requires_active_reference() -> None:
    session = AsyncMock()
    service = MarketReferenceAnalysisService(session)
    service._active_reference = AsyncMock(return_value=None)

    with pytest.raises(AnalysisDataUnavailable, match="active market reference was not found"):
        await service.create_for_market_reference(
            workspace_id=uuid4(),
            market_reference_id=uuid4(),
            actor="post-d01-coverage",
        )

    session.flush.assert_not_awaited()
    session.commit.assert_not_awaited()
