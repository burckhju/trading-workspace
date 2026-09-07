from app.core.di import ApplicationContainer
from app.features.position_monitoring.service.quote_sources import (
    MultiSourceWarrantQuoteResolver,
    NamedWarrantQuoteSource,
)
from app.providers.eodhd.warrant_quote import EodhdWarrantQuoteAdapter
from app.providers.stuttgart_delayed import StuttgartDelayedWarrantQuoteAdapter


def build_warrant_quote_resolver(
    container: ApplicationContainer,
) -> MultiSourceWarrantQuoteResolver:
    """Build the shared runtime quote resolver for held-product valuation reads."""

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
    return MultiSourceWarrantQuoteResolver(
        (
            NamedWarrantQuoteSource("EODHD", EodhdWarrantQuoteAdapter()),
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
