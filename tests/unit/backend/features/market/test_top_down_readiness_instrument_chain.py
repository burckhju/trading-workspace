from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.features.market.service.top_down_readiness import (
    MarketDataTopDownReferenceAdministrationService,
)
from app.features.market_data.domain.enums import MappingStatus


@pytest.mark.asyncio
async def test_readiness_no_longer_requires_listing_assignment() -> None:
    session = AsyncMock()
    service = MarketDataTopDownReferenceAdministrationService(session)
    reference = SimpleNamespace(
        id=uuid4(),
        code="DAX",
        reference_type="INDEX",
        active=True,
    )
    service.list_market_references = AsyncMock(return_value=(reference,))  # type: ignore[method-assign]
    session.scalar.side_effect = [None, None]

    result = (await service.reference_readiness(uuid4()))[0]

    assert result.listing_id is None
    assert "NO_ACTIVE_LISTING_ASSIGNMENT" not in result.blockers
    assert "NO_MARKET_DATA_INSTRUMENT" in result.blockers
    assert result.ready is False


@pytest.mark.asyncio
async def test_direct_market_data_chain_can_be_ready_without_listing() -> None:
    session = AsyncMock()
    service = MarketDataTopDownReferenceAdministrationService(session)
    workspace_id = uuid4()
    reference = SimpleNamespace(
        id=uuid4(),
        code="SP500",
        reference_type="INDEX",
        active=True,
    )
    instrument = SimpleNamespace(id=uuid4())
    mapping = SimpleNamespace(id=uuid4(), status=MappingStatus.ACTIVE)
    analysis_id = uuid4()

    service.list_market_references = AsyncMock(return_value=(reference,))  # type: ignore[method-assign]
    session.scalar.side_effect = [None, instrument, mapping]
    price_result = Mock()
    price_result.one.return_value = (61, date(2026, 8, 26))
    analysis_result = Mock()
    analysis_result.first.return_value = (analysis_id, 1)
    session.execute.side_effect = [price_result, analysis_result]

    result = (await service.reference_readiness(workspace_id))[0]

    assert result.listing_id is None
    assert result.provider_mapping_id == mapping.id
    assert result.provider_mapping_active is True
    assert result.daily_price_count == 61
    assert result.completed_analysis_id == analysis_id
    assert result.completed_analysis_version == 1
    assert result.blockers == ()
    assert result.ready is True
