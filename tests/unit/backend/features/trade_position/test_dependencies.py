from types import SimpleNamespace

from app.features.market_data.domain.enums import MarketDataProvider
from app.features.trade_position.api.dependencies import _allowed_warrant_quote_providers


def container(
    *,
    frankfurt=None,
    frankfurt_reason: str = "FRANKFURT_DISABLED",
    vontobel=None,
    stuttgart=None,
    stuttgart_schema: bool = False,
    stuttgart_source: bool = False,
    gettex=None,
):
    return SimpleNamespace(
        frankfurt=frankfurt,
        vontobel=vontobel,
        stuttgart=stuttgart,
        gettex=gettex,
        settings=SimpleNamespace(
            market_data=SimpleNamespace(
                frankfurt=SimpleNamespace(readiness_reason=frankfurt_reason),
                stuttgart_delayed=SimpleNamespace(
                    has_verified_schema=stuttgart_schema,
                    has_source_configuration=stuttgart_source,
                ),
            )
        ),
    )


def test_allowed_quote_sources_require_runtime_and_provider_readiness() -> None:
    marker = object()
    blocked = _allowed_warrant_quote_providers(
        container(
            frankfurt=marker,
            frankfurt_reason="FRANKFURT_USAGE_NOT_APPROVED",
            stuttgart=marker,
            stuttgart_schema=False,
            stuttgart_source=True,
        )
    )
    assert blocked == frozenset()

    allowed = _allowed_warrant_quote_providers(
        container(
            frankfurt=marker,
            frankfurt_reason="CONFIGURED_NOT_PROBED",
            vontobel=marker,
            stuttgart=marker,
            stuttgart_schema=True,
            stuttgart_source=True,
            gettex=marker,
        )
    )
    assert allowed == frozenset(
        {
            MarketDataProvider.FRANKFURT_QUOTES,
            MarketDataProvider.VONTOBEL_MARKETS,
            MarketDataProvider.BOERSE_STUTTGART_DELAYED,
            MarketDataProvider.GETTEX_DELAYED,
        }
    )
