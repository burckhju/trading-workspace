from app.features.analysis.persistence.models import MarketAnalysisModel


def test_market_analysis_model_has_expand_identity_contract() -> None:
    table = MarketAnalysisModel.__table__
    assert table.c.market_data_instrument_id.nullable is True
    assert table.c.listing_id.nullable is True
    assert table.c.underlying_id.nullable is True

    names = {constraint.name for constraint in table.constraints}
    assert "ck_market_analyses_owner_shape" in names

    fks = {fk.parent.name: fk for fk in table.foreign_keys}
    assert fks["market_data_instrument_id"].ondelete == "RESTRICT"


def test_market_analysis_has_instrument_lookup_index() -> None:
    names = {index.name for index in MarketAnalysisModel.__table__.indexes}
    assert "ix_market_analyses_workspace_instrument_created" in names
