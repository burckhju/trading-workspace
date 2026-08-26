from app.features.market.domain.enums import UnderlyingType
from app.features.market_data.persistence.instruments import MarketDataInstrumentModel


def test_ft001_underlying_universe_remains_stock_only() -> None:
    assert list(UnderlyingType) == [UnderlyingType.STOCK]


def test_market_data_instrument_is_identity_only() -> None:
    table = MarketDataInstrumentModel.__table__

    assert table.c.workspace_id.nullable is False
    assert table.c.kind.nullable is False
    assert table.c.listing_id.nullable is True
    assert table.c.market_reference_id.nullable is True
    assert table.c.created_at.nullable is False
    assert "active" not in table.c


def test_market_data_instrument_enforces_exclusive_owner_shape() -> None:
    table = MarketDataInstrumentModel.__table__
    constraint_names = {constraint.name for constraint in table.constraints}

    assert "ck_market_data_instruments_owner_matches_kind" in constraint_names
    assert "uq_market_data_instruments_listing" in constraint_names
    assert "uq_market_data_instruments_market_reference" in constraint_names


def test_market_data_instrument_delete_semantics_are_restrictive() -> None:
    table = MarketDataInstrumentModel.__table__
    foreign_keys = {foreign_key.parent.name: foreign_key for foreign_key in table.foreign_keys}

    assert foreign_keys["workspace_id"].ondelete == "RESTRICT"
    assert foreign_keys["listing_id"].ondelete == "RESTRICT"
    assert foreign_keys["market_reference_id"].ondelete == "RESTRICT"
