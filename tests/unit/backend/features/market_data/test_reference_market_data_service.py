from datetime import date
from decimal import Decimal

import pytest

from app.features.market.api.top_down_market_data_dtos import ReferenceDailyPriceImportRequest
from app.features.market_data.service.reference_market_data import ReferenceMarketDataService
from app.providers.eodhd.dto import EodhdDailyPriceDto


def _price(**overrides: object) -> EodhdDailyPriceDto:
    values: dict[str, object] = {
        "date": date(2026, 8, 26),
        "open": Decimal("100"),
        "high": Decimal("110"),
        "low": Decimal("90"),
        "close": Decimal("105"),
        "adjusted_close": Decimal("105"),
        "volume": Decimal("1000"),
    }
    values.update(overrides)
    return EodhdDailyPriceDto.model_validate(values)


def test_reference_ohlc_validation_accepts_consistent_prices() -> None:
    ReferenceMarketDataService._validate_ohlc(_price())


def test_reference_ohlc_validation_rejects_close_outside_range() -> None:
    with pytest.raises(ValueError, match="inconsistent OHLC"):
        ReferenceMarketDataService._validate_ohlc(_price(close=Decimal("120")))


def test_reference_import_request_rejects_reverse_period() -> None:
    with pytest.raises(ValueError, match="end_date"):
        ReferenceDailyPriceImportRequest(
            start_date=date(2026, 8, 27),
            end_date=date(2026, 8, 26),
        )
