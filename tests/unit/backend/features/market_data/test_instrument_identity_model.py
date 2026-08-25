from app.features.analysis.persistence.models import MarketAnalysisModel
from app.features.market.domain.enums import UnderlyingType
from app.features.market_data.persistence.instruments import MarketDataInstrumentModel
from app.features.market_data.persistence.models import DailyPriceModel, ProviderInstrumentMappingModel


def test_ft001_underlying_universe_remains_stock_only() -> None:
    assert list(UnderlyingType) == [UnderlyingType.STOCK]


def test_market_data_instrument_has_asset_neutral_owner_columns() -> None:
    table = MarketDataInstrumentModel.__table__

    assert table.c.kind.nullable is False
    assert table.c.listing_id.nullable is True
    assert table.c.market_reference_id.nullable is True
    assert table.c.active.nullable is False

    constraint_names = {constraint.name for constraint in table.constraints}
    assert "ck_market_data_instruments_owner_matches_kind" in constraint_names
    assert "uq_market_data_instruments_workspace_listing" in constraint_names
    assert "uq_market_data_instruments_workspace_reference" in constraint_names


def test_expand_phase_consumers_accept_reference_owned_identity() -> None:
    mapping = ProviderInstrumentMappingModel.__table__
    prices = DailyPriceModel.__table__
    analyses = MarketAnalysisModel.__table__

    assert mapping.c.market_data_instrument_id.nullable is True
    assert mapping.c.listing_id.nullable is True
    assert prices.c.market_data_instrument_id.nullable is True
    assert prices.c.listing_id.nullable is True
    assert analyses.c.market_data_instrument_id.nullable is True
    assert analyses.c.underlying_id.nullable is True
    assert analyses.c.listing_id.nullable is True

    assert "ck_provider_instrument_mappings_internal_owner" in {
        constraint.name for constraint in mapping.constraints
    }
    assert "ck_daily_prices_internal_owner" in {
        constraint.name for constraint in prices.constraints
    }
    assert "ck_market_analyses_internal_owner" in {
        constraint.name for constraint in analyses.constraints
    }
