"""Runtime policy for quote providers eligible for persistent warrant bindings."""

from app.core.di import ApplicationContainer
from app.features.market_data.domain.enums import MarketDataProvider


def allowed_warrant_quote_providers(
    container: ApplicationContainer,
) -> frozenset[MarketDataProvider]:
    """Return providers that are configured strongly enough for persistent selection."""
    allowed: set[MarketDataProvider] = set()
    if (
        container.frankfurt is not None
        and container.settings.market_data.frankfurt.readiness_reason == "CONFIGURED_NOT_PROBED"
    ):
        allowed.add(MarketDataProvider.FRANKFURT_QUOTES)
    if container.vontobel is not None:
        allowed.add(MarketDataProvider.VONTOBEL_MARKETS)
    stuttgart = container.settings.market_data.stuttgart_delayed
    if (
        container.stuttgart is not None
        and stuttgart.has_verified_schema
        and stuttgart.has_source_configuration
    ):
        allowed.add(MarketDataProvider.BOERSE_STUTTGART_DELAYED)
    if container.gettex is not None:
        allowed.add(MarketDataProvider.GETTEX_DELAYED)
    return frozenset(allowed)
