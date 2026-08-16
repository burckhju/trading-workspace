"""Unit tests for provider-independent market-data domain models."""

from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.features.market_data.domain.enums import (
    MappingStatus,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.errors import (
    InvalidDailyPrice,
    InvalidMarketDataValue,
    InvalidProviderInstrumentMapping,
)
from app.features.market_data.domain.models import (
    DailyPrice,
    ProviderInstrumentMapping,
    WarrantQuoteSnapshot,
)

UTC_NOW = datetime(2026, 8, 5, 10, 0, tzinfo=UTC)


def make_price(**overrides: object) -> DailyPrice:
    values: dict[str, object] = {
        "listing_id": uuid4(),
        "trading_date": date(2026, 8, 4),
        "open": Decimal("100.10"),
        "high": Decimal("105.20"),
        "low": Decimal("99.80"),
        "close": Decimal("104.00"),
        "adjusted_close": Decimal("103.50"),
        "volume": Decimal("123456"),
        "currency": " eur ",
        "provider": MarketDataProvider.EODHD,
        "provider_symbol": " sap ",
        "retrieved_at": UTC_NOW,
        "source_updated_at": None,
        "quality_status": QualityStatus.VALID,
        "warnings": ("", " verified "),
    }
    values.update(overrides)
    return DailyPrice(**values)  # type: ignore[arg-type]


def test_daily_price_normalizes_codes_and_warnings() -> None:
    price = make_price(open="100.10", volume=None)

    assert price.open == Decimal("100.10")
    assert price.currency == "EUR"
    assert price.provider_symbol == "SAP"
    assert price.volume is None
    assert price.warnings == ("verified",)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("open", Decimal("99.00")),
        ("close", Decimal("106.00")),
        ("volume", Decimal("-1")),
        ("adjusted_close", Decimal("0")),
    ],
)
def test_daily_price_rejects_invalid_values(field: str, value: Decimal) -> None:
    with pytest.raises(InvalidDailyPrice) as exc_info:
        make_price(**{field: value})

    assert exc_info.value.field == field


def test_daily_price_rejects_low_above_high() -> None:
    with pytest.raises(InvalidDailyPrice, match="low must not exceed high"):
        make_price(low=Decimal("110"))


def test_daily_price_rejects_binary_float_input() -> None:
    with pytest.raises(InvalidMarketDataValue, match="binary floating-point"):
        make_price(open=100.1)


def test_daily_price_requires_utc_timestamp() -> None:
    berlin_time = datetime(2026, 8, 5, 12, 0, tzinfo=timezone(timedelta(hours=2)))

    with pytest.raises(InvalidMarketDataValue, match="must use UTC"):
        make_price(retrieved_at=berlin_time)


def test_active_mapping_requires_successful_validation_timestamp() -> None:
    with pytest.raises(InvalidProviderInstrumentMapping) as exc_info:
        ProviderInstrumentMapping(
            id=uuid4(),
            workspace_id=uuid4(),
            listing_id=uuid4(),
            provider=MarketDataProvider.EODHD,
            provider_symbol="sap",
            provider_exchange_code="xetr",
            status=MappingStatus.ACTIVE,
            validated_at=None,
            validation_message=None,
            created_at=UTC_NOW,
            updated_at=UTC_NOW,
            version=1,
        )

    assert exc_info.value.field == "validated_at"


def test_mapping_normalizes_provider_identity() -> None:
    mapping = ProviderInstrumentMapping(
        id=uuid4(),
        workspace_id=uuid4(),
        listing_id=uuid4(),
        provider=MarketDataProvider.EODHD,
        provider_symbol=" sap ",
        provider_exchange_code=" xetr ",
        status=MappingStatus.ACTIVE,
        validated_at=UTC_NOW,
        validation_message=" valid ",
        created_at=UTC_NOW,
        updated_at=UTC_NOW,
        version=1,
    )

    assert mapping.provider_symbol == "SAP"
    assert mapping.provider_exchange_code == "XETR"
    assert mapping.validation_message == "valid"


def test_warrant_quote_snapshot_is_listing_specific_and_normalized() -> None:
    listing_id = uuid4()
    quote = WarrantQuoteSnapshot(
        warrant_listing_id=listing_id,
        bid="1.00",
        ask="1.04",
        currency=" eur ",
        provider_symbol=" test ",
        provider_exchange_code=" xetr ",
        observed_at=UTC_NOW,
    )

    assert quote.warrant_listing_id == listing_id
    assert quote.bid == Decimal("1.00")
    assert quote.ask == Decimal("1.04")
    assert quote.currency == "EUR"
    assert quote.provider_symbol == "TEST"
    assert quote.provider_exchange_code == "XETR"


def test_warrant_quote_snapshot_rejects_crossed_quote() -> None:
    with pytest.raises(InvalidMarketDataValue, match="ask must not be below bid"):
        WarrantQuoteSnapshot(
            warrant_listing_id=uuid4(),
            bid="1.05",
            ask="1.04",
            currency="EUR",
            provider_symbol="TEST",
            provider_exchange_code="XETR",
            observed_at=UTC_NOW,
        )
