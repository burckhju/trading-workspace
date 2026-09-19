from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.persistence.quote_identity import verified_identity
from app.features.product.domain.models import WarrantLifecycle


def _row(*, venue_mic: str, exchange: str):
    workspace = uuid4()
    warrant_id = uuid4()
    listing_id = uuid4()
    venue_id = uuid4()
    warrant = SimpleNamespace(
        id=warrant_id,
        workspace_id=workspace,
        version=1,
        lifecycle_status=WarrantLifecycle.ACTIVE,
        isin="DE000AB00001",
        wkn="AB0000",
    )
    listing = SimpleNamespace(
        id=listing_id,
        workspace_id=workspace,
        warrant_id=warrant_id,
        trading_venue_id=venue_id,
        lifecycle_status=WarrantLifecycle.ACTIVE,
        version=1,
        quotation_currency_code="EUR",
    )
    venue = SimpleNamespace(id=venue_id, mic=venue_mic, is_active=True)
    mapping = SimpleNamespace(
        id=uuid4(),
        workspace_id=workspace,
        warrant_listing_id=listing_id,
        provider=MarketDataProvider.GETTEX_DELAYED,
        status=MappingStatus.ACTIVE,
        validated_at=datetime(2026, 9, 18, tzinfo=UTC),
        provider_symbol=warrant.isin,
        provider_exchange_code=exchange,
        version=1,
    )
    return workspace, listing, warrant, venue, mapping


def test_gettex_identity_requires_listing_mic_to_match_provider_exchange():
    workspace, listing, warrant, venue, mapping = _row(venue_mic="XFRA", exchange="MUND")

    assert (
        verified_identity(
            workspace,
            listing,
            warrant,
            venue,
            MarketDataProvider.GETTEX_DELAYED,
            mapping,
        )
        is None
    )


def test_gettex_identity_accepts_matching_mund_listing():
    workspace, listing, warrant, venue, mapping = _row(venue_mic="MUND", exchange="MUND")

    identity = verified_identity(
        workspace,
        listing,
        warrant,
        venue,
        MarketDataProvider.GETTEX_DELAYED,
        mapping,
    )

    assert identity is not None
    assert identity.mic == "MUND"
    assert identity.exchange == "MUND"
