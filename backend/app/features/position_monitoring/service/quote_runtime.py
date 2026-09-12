from app.core.di import ApplicationContainer
from app.features.position_monitoring.service.quote_sources import (
    MultiSourceWarrantQuoteResolver,
    NamedWarrantQuoteSource,
)
from app.providers.stuttgart_delayed import StuttgartDelayedWarrantQuoteAdapter
from app.providers.vontobel_markets import VontobelMarketsWarrantQuoteAdapter


def build_warrant_quote_resolver(
    container: ApplicationContainer,
) -> MultiSourceWarrantQuoteResolver:
    """Build the shared runtime quote resolver for held-product valuation reads."""

    vontobel_settings = container.settings.market_data.vontobel_markets
    vontobel_provider = (
        VontobelMarketsWarrantQuoteAdapter(
            database=container.database,
            settings=vontobel_settings,
        )
        if vontobel_settings.enabled
        else None
    )
    stuttgart_settings = container.settings.market_data.stuttgart_delayed
    stuttgart_provider = (
        StuttgartDelayedWarrantQuoteAdapter(
            database=container.database,
            settings=stuttgart_settings,
        )
        if stuttgart_settings.enabled and stuttgart_settings.has_verified_schema
        else None
    )
    stuttgart_reason = (
        "STUTTGART_DELAYED_DISABLED"
        if not stuttgart_settings.enabled
        else "STUTTGART_DELAYED_SCHEMA_NOT_VERIFIED"
    )
    frankfurt_settings = container.settings.market_data.frankfurt
    return MultiSourceWarrantQuoteResolver(
        (
            NamedWarrantQuoteSource(
                "FRANKFURT_QUOTES",
                container.frankfurt,
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
                None,
                delayed=True,
                unavailable_reason=(
                    "Official MUND/MUNC delayed pre-trade source is reserved but not enabled until "
                    "payload schema, usage terms, and listing identity are verified"
                ),
            ),
        )
    )
