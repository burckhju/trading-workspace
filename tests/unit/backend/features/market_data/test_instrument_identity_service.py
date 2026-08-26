from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from app.features.market_data.persistence.instruments import MarketDataInstrumentModel
from app.features.market_data.service.instrument_identity import MarketDataInstrumentIdentityService


def _session() -> Mock:
    session = Mock()
    session.scalar = AsyncMock()
    session.flush = AsyncMock()
    session.add = Mock()
    return session


@pytest.mark.asyncio
async def test_for_listing_returns_existing_identity() -> None:
    session = _session()
    workspace_id = uuid4()
    listing_id = uuid4()
    existing = MarketDataInstrumentModel(
        id=uuid4(),
        workspace_id=workspace_id,
        kind="LISTING",
        listing_id=listing_id,
        market_reference_id=None,
        created_at=datetime.now(UTC),
    )
    session.scalar.return_value = existing

    result = await MarketDataInstrumentIdentityService(session).for_listing(
        workspace_id=workspace_id,
        listing_id=listing_id,
    )

    assert result is existing
    session.add.assert_not_called()
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_for_listing_creates_identity_for_owner_in_workspace() -> None:
    session = _session()
    workspace_id = uuid4()
    listing_id = uuid4()
    session.scalar.side_effect = [None, listing_id]

    result = await MarketDataInstrumentIdentityService(session).for_listing(
        workspace_id=workspace_id,
        listing_id=listing_id,
    )

    assert result.workspace_id == workspace_id
    assert result.kind == "LISTING"
    assert result.listing_id == listing_id
    assert result.market_reference_id is None
    session.add.assert_called_once_with(result)
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_for_listing_rejects_owner_from_other_workspace() -> None:
    session = _session()
    session.scalar.side_effect = [None, None]

    with pytest.raises(ValueError, match="listing not found in workspace"):
        await MarketDataInstrumentIdentityService(session).for_listing(
            workspace_id=uuid4(),
            listing_id=uuid4(),
        )


@pytest.mark.asyncio
async def test_for_market_reference_creates_identity_for_owner_in_workspace() -> None:
    session = _session()
    workspace_id = uuid4()
    reference_id = uuid4()
    session.scalar.side_effect = [None, reference_id]

    result = await MarketDataInstrumentIdentityService(session).for_market_reference(
        workspace_id=workspace_id,
        market_reference_id=reference_id,
    )

    assert result.workspace_id == workspace_id
    assert result.kind == "MARKET_REFERENCE"
    assert result.listing_id is None
    assert result.market_reference_id == reference_id
    session.add.assert_called_once_with(result)
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_resolves_identity_and_rejects_missing_identity() -> None:
    session = _session()
    workspace_id = uuid4()
    instrument_id = uuid4()
    existing = MarketDataInstrumentModel(
        id=instrument_id,
        workspace_id=workspace_id,
        kind="MARKET_REFERENCE",
        listing_id=None,
        market_reference_id=uuid4(),
        created_at=datetime.now(UTC),
    )
    session.scalar.side_effect = [existing, None]
    service = MarketDataInstrumentIdentityService(session)

    assert await service.get(workspace_id=workspace_id, instrument_id=instrument_id) is existing
    with pytest.raises(ValueError, match="market-data instrument not found in workspace"):
        await service.get(workspace_id=workspace_id, instrument_id=uuid4())
