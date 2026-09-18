from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.domain.position_quote_source import (
    PositionQuoteSourceCandidate,
    PositionQuoteSourceSelectionStatus,
)
from app.features.market_data.service.position_quote_source import (
    POSITION_QUOTE_SOURCE_POLICY_V1,
    PositionQuoteSourceSelector,
    choose_position_quote_source,
)


def candidate(
    provider: MarketDataProvider = MarketDataProvider.GETTEX_DELAYED,
    *,
    listing_id=None,
    mapping_id=None,
    currency: str = "EUR",
) -> PositionQuoteSourceCandidate:
    return PositionQuoteSourceCandidate(
        provider=provider,
        listing_id=listing_id or uuid4(),
        mapping_id=mapping_id or uuid4(),
        mapping_version=1,
        identity_key="a" * 64,
        currency=currency,
        mic="XSTU",
        provider_exchange_code=(
            "MUND" if provider is MarketDataProvider.GETTEX_DELAYED else "ISSUER"
        ),
    )


def test_policy_selects_only_one_verified_route():
    route = candidate()
    decision = choose_position_quote_source((route,))
    assert decision.status is PositionQuoteSourceSelectionStatus.SELECTED
    assert decision.selected == route
    assert decision.reason == "UNIQUE_VERIFIED_ROUTE"


def test_policy_is_fail_closed_for_multiple_routes():
    listing = uuid4()
    decision = choose_position_quote_source(
        (
            candidate(MarketDataProvider.GETTEX_DELAYED, listing_id=listing),
            candidate(MarketDataProvider.VONTOBEL_MARKETS, listing_id=listing),
        )
    )
    assert decision.status is PositionQuoteSourceSelectionStatus.AMBIGUOUS_SOURCE
    assert decision.selected is None
    assert decision.reason == "MULTIPLE_VERIFIED_QUOTE_SOURCES"


def test_policy_uses_exact_currency_and_preferred_listing_without_guessing_provider():
    preferred, alternate = uuid4(), uuid4()
    preferred_route = candidate(listing_id=preferred, currency="EUR")
    decision = choose_position_quote_source(
        (
            preferred_route,
            candidate(listing_id=alternate, currency="EUR"),
            candidate(listing_id=uuid4(), currency="USD"),
        ),
        preferred_listing_id=preferred,
        expected_currency="EUR",
    )
    assert decision.status is PositionQuoteSourceSelectionStatus.SELECTED
    assert decision.selected == preferred_route
    assert decision.reason == "UNIQUE_VERIFIED_ROUTE_ON_PREFERRED_LISTING"

    missing = choose_position_quote_source(
        (candidate(currency="USD"),),
        expected_currency="EUR",
    )
    assert missing.status is PositionQuoteSourceSelectionStatus.NO_VERIFIED_QUOTE_SOURCE
    assert missing.selected is None


@pytest.mark.asyncio
async def test_selector_persists_failure_state_and_is_idempotent():
    workspace, position, warrant = uuid4(), uuid4(), uuid4()
    repository = SimpleNamespace(
        lock_open_position=AsyncMock(return_value=True),
        active_for_position=AsyncMock(return_value=None),
        verified_candidates=AsyncMock(return_value=()),
        add=AsyncMock(),
    )
    selector = PositionQuoteSourceSelector(repository, {MarketDataProvider.GETTEX_DELAYED})
    now = datetime(2026, 9, 18, 20, tzinfo=UTC)

    row = await selector.select_once(
        workspace_id=workspace,
        position_id=position,
        warrant_id=warrant,
        expected_currency="EUR",
        selected_at=now,
    )
    assert row.selection_status == "NO_VERIFIED_QUOTE_SOURCE"
    assert row.selection_reason == "NO_VERIFIED_QUOTE_SOURCE"
    assert row.provider is None and row.identity_key is None
    assert row.policy_version == POSITION_QUOTE_SOURCE_POLICY_V1
    assert row.evidence["enabled_providers"] == ["GETTEX_DELAYED"]
    repository.add.assert_awaited_once_with(row)

    repository.active_for_position.return_value = row
    repeated = await selector.select_once(
        workspace_id=workspace,
        position_id=position,
        warrant_id=warrant,
    )
    assert repeated is row
    repository.verified_candidates.assert_awaited_once()
    repository.add.assert_awaited_once()


@pytest.mark.asyncio
async def test_selector_rejects_non_open_or_foreign_position():
    repository = SimpleNamespace(
        lock_open_position=AsyncMock(return_value=False),
        active_for_position=AsyncMock(),
        verified_candidates=AsyncMock(),
        add=AsyncMock(),
    )
    selector = PositionQuoteSourceSelector(repository, {MarketDataProvider.GETTEX_DELAYED})
    with pytest.raises(ValueError, match="OPEN_POSITION_NOT_FOUND"):
        await selector.select_once(
            workspace_id=uuid4(),
            position_id=uuid4(),
            warrant_id=uuid4(),
        )
    repository.active_for_position.assert_not_awaited()
    repository.add.assert_not_awaited()
