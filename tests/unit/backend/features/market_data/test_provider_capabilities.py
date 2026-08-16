from app.features.market_data.domain.enums import MarketDataCapability, MarketDataProvider
from app.features.market_data.service.capabilities import (
    ProviderCapabilityStatus,
    resolve_provider_capability,
)


def test_eodhd_warrant_listing_quote_remains_unverified_and_unusable() -> None:
    resolution = resolve_provider_capability(
        MarketDataProvider.EODHD,
        MarketDataCapability.WARRANT_LISTING_QUOTE,
    )
    assert resolution.status is ProviderCapabilityStatus.UNVERIFIED
    assert resolution.usable is False
    assert "WarrantListing" in resolution.reason
