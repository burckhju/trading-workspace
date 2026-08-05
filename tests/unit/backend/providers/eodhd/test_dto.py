"""Tests for strict EODHD transport DTOs."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.providers.eodhd.dto import EodhdDailyPriceDto


def test_daily_price_dto_accepts_decimal_strings_and_ignores_new_fields() -> None:
    dto = EodhdDailyPriceDto.model_validate(
        {
            "date": "2026-08-04",
            "open": "100.1",
            "high": "105.2",
            "low": "99.8",
            "close": "104",
            "adjusted_close": None,
            "volume": None,
            "new_field": "safe",
        }
    )
    assert dto.open == Decimal("100.1")
    assert dto.volume is None


def test_daily_price_dto_rejects_binary_float_and_negative_volume() -> None:
    with pytest.raises(ValidationError, match="binary floating"):
        EodhdDailyPriceDto.model_validate(
            {"date": "2026-08-04", "open": 1.1, "high": "2", "low": "1", "close": "1"}
        )
    with pytest.raises(ValidationError, match="volume"):
        EodhdDailyPriceDto.model_validate(
            {
                "date": "2026-08-04",
                "open": "1",
                "high": "2",
                "low": "1",
                "close": "1",
                "volume": "-1",
            }
        )
