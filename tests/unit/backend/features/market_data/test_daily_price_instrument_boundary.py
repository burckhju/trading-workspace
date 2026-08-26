from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.features.market_data.domain.enums import MarketDataProvider, PriceType, QualityStatus
from app.features.market_data.domain.errors import InvalidDailyPrice
from app.features.market_data.domain.models import DailyPrice
from app.features.market_data.persistence.mapping import daily_price_to_model
from app.features.market_data.persistence.models import DailyPriceModel

NOW = datetime(2026, 8, 26, 18, tzinfo=UTC)


def _price(*, listing_id=None, market_data_instrument_id=None) -> DailyPrice:
    return DailyPrice(
        listing_id=listing_id,
        market_data_instrument_id=market_data_instrument_id,
        trading_date=date(2026, 8, 25),
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("99"),
        close=Decimal("101"),
        adjusted_close=None,
        volume=Decimal("1000"),
        currency="EUR",
        provider=MarketDataProvider.EODHD,
        provider_symbol="TEST.XETRA",
        retrieved_at=NOW,
        source_updated_at=None,
        quality_status=QualityStatus.VALID,
        price_type=PriceType.EOD,
    )


def test_daily_price_model_has_expand_identity_contract() -> None:
    table = DailyPriceModel.__table__
    assert table.c.listing_id.nullable is True
    assert table.c.market_data_instrument_id.nullable is True
    names = {constraint.name for constraint in table.constraints}
    assert "ck_daily_prices_internal_owner" in names
    assert "uq_daily_prices_listing_date_type" in names
    assert "uq_daily_prices_instrument_date_type" in names
    fks = {fk.parent.name: fk for fk in table.foreign_keys}
    assert fks["market_data_instrument_id"].ondelete == "RESTRICT"


def test_daily_price_domain_accepts_instrument_only_owner() -> None:
    instrument_id = uuid4()
    value = _price(market_data_instrument_id=instrument_id)
    assert value.listing_id is None
    assert value.market_data_instrument_id == instrument_id


def test_daily_price_domain_rejects_missing_owner() -> None:
    with pytest.raises(InvalidDailyPrice):
        _price()


def test_daily_price_mapping_can_dual_write_instrument_identity() -> None:
    listing_id = uuid4()
    instrument_id = uuid4()
    model = daily_price_to_model(
        _price(listing_id=listing_id),
        workspace_id=uuid4(),
        price_id=uuid4(),
        now=NOW,
        market_data_instrument_id=instrument_id,
    )
    assert model.listing_id == listing_id
    assert model.market_data_instrument_id == instrument_id
