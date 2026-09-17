from app.core.di import ApplicationContainer
from app.features.market_data.domain.enums import MarketDataProvider
from app.features.market_data.service.retained_quotes import RetainedWarrantQuoteProvider
from app.features.position_monitoring.service.quote_sources import (
    MultiSourceWarrantQuoteResolver,
    NamedWarrantQuoteSource,
)


def build_warrant_quote_resolver(
    container: ApplicationContainer,
) -> MultiSourceWarrantQuoteResolver:
    """Build the shared runtime quote resolver for held-product valuation reads."""

    vontobel_provider = (
        RetainedWarrantQuoteProvider(
            container.database, container.vontobel, MarketDataProvider.VONTOBEL_MARKETS
        )
        if container.vontobel is not None
        else None
    )
    stuttgart_settings = container.settings.market_data.stuttgart_delayed
    stuttgart_provider = (
        RetainedWarrantQuoteProvider(
            container.database, container.stuttgart, MarketDataProvider.BOERSE_STUTTGART_DELAYED
        )
        if container.stuttgart is not None
        else None
    )
    stuttgart_reason = (
        "STUTTGART_DELAYED_DISABLED"
        if not stuttgart_settings.enabled
        else "STUTTGART_DELAYED_SCHEMA_NOT_VERIFIED"
    )
    gettex_provider = (
        RetainedWarrantQuoteProvider(
            container.database, container.gettex, MarketDataProvider.GETTEX_DELAYED
        )
        if container.gettex is not None
        else None
    )
    gettex_reason = (
        "GETTEX_DELAYED_DISABLED"
        if not container.settings.market_data.gettex_delayed.enabled
        else "GETTEX_DELAYED_MAPPING_REQUIRED"
    )
    frankfurt_settings = container.settings.market_data.frankfurt
    return MultiSourceWarrantQuoteResolver(
        (
            NamedWarrantQuoteSource(
                "FRANKFURT_QUOTES",
                (
                    RetainedWarrantQuoteProvider(
                        container.database, container.frankfurt, MarketDataProvider.FRANKFURT_QUOTES
                    )
                    if container.frankfurt is not None
                    else None
                ),
                delayed=frankfurt_settings.feed_delay_seconds > 0,
                unavailable_reason="FRANKFURT_DISABLED",
            ),
            NamedWarrantQuoteSource(
                "VONTOBEL_MARKETS",
                vontobel_provider,
                unavailable_reason="VONTOBEL_MARKETS_DISABLED",
            ),
            NamedWarrantQuoteSource(
                "BOERSE_STUTTGART_DELAYED",
                stuttgart_provider,
                delayed=True,
                unavailable_reason=stuttgart_reason,
            ),
            NamedWarrantQuoteSource(
                "GETTEX_DELAYED",
                gettex_provider,
                delayed=True,
                unavailable_reason=gettex_reason,
            ),
        )
    )
