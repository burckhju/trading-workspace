from app.features.market.domain.enums import UnderlyingType
from app.features.market_data.persistence.instruments import MarketDataInstrumentModel


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
