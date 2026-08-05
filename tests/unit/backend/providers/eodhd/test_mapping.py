from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.domain.models import ProviderInstrumentMapping
from app.features.market_data.service.errors import MarketDataMappingError
from app.providers.eodhd.dto import EodhdDailyPriceDto
from app.providers.eodhd.mapping import map_daily_price


def mapping() -> ProviderInstrumentMapping:
    now = datetime(2026, 8, 5, tzinfo=UTC)
    return ProviderInstrumentMapping(
        id=uuid4(), workspace_id=uuid4(), listing_id=uuid4(),
        provider=MarketDataProvider.EODHD, provider_symbol="aapl",
        provider_exchange_code="us", status=MappingStatus.ACTIVE,
        validated_at=now, validation_message=None, created_at=now,
        updated_at=now, version=1,
    )


def test_maps_eodhd_row_to_internal_daily_price() -> None:
    result = map_daily_price(
        EodhdDailyPriceDto(date=date(2026, 8, 4), open="100", high="110", low="99", close="108", adjusted_close="107", volume="12"),
        mapping=mapping(), currency="usd", retrieved_at=datetime(2026, 8, 5, tzinfo=UTC),
    )
    assert result.currency == "USD"
    assert result.provider_symbol == "AAPL"
    assert result.close == Decimal("108")


def test_rejects_domain_inconsistent_ohlc() -> None:
    with pytest.raises(MarketDataMappingError):
        map_daily_price(
            EodhdDailyPriceDto(date=date(2026, 8, 4), open="120", high="110", low="99", close="108"),
            mapping=mapping(), currency="USD", retrieved_at=datetime(2026, 8, 5, tzinfo=UTC),
        )
