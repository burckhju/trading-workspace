from app.core.di import ApplicationContainer
from app.features.position_monitoring.service.quote_sources import (
    MultiSourceWarrantQuoteResolver,
    NamedWarrantQuoteSource,
)


def build_warrant_quote_resolver(
    container: ApplicationContainer,
) -> MultiSourceWarrantQuoteResolver:
    """Build the shared runtime quote resolver for held-product valuation reads."""

    vontobel_provider = container.vontobel
    stuttgart_settings = container.settings.market_data.stuttgart_delayed
    stuttgart_provider = container.stuttgart
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
