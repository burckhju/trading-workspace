from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.domain.models import WarrantProviderMapping


def test_warrant_provider_mapping_is_separate_and_normalized() -> None:
    now = datetime.now(UTC)
    mapping = WarrantProviderMapping(
        id=uuid4(),
        workspace_id=uuid4(),
        warrant_listing_id=uuid4(),
        provider=MarketDataProvider.EODHD,
        provider_symbol=" abcd ",
        provider_exchange_code=" xfra ",
        status=MappingStatus.ACTIVE,
        validated_at=now,
        validation_message=" ok ",
        created_at=now,
        updated_at=now,
        version=1,
    )
    assert mapping.provider_symbol == "ABCD"
    assert mapping.provider_exchange_code == "XFRA"
    assert mapping.validation_message == "ok"


def test_active_warrant_mapping_requires_validation() -> None:
    now = datetime.now(UTC)
    with pytest.raises(ValueError):
        WarrantProviderMapping(
            id=uuid4(),
            workspace_id=uuid4(),
            warrant_listing_id=uuid4(),
            provider=MarketDataProvider.EODHD,
            provider_symbol="ABCD",
            provider_exchange_code="XFRA",
            status=MappingStatus.ACTIVE,
            validated_at=None,
            validation_message=None,
            created_at=now,
            updated_at=now,
            version=1,
        )


@pytest.mark.asyncio
async def test_eodhd_warrant_quote_adapter_fails_closed_without_verified_transport() -> None:
    from app.features.market_data.service.errors import MarketDataConfigurationError
    from app.features.market_data.service.types import WarrantQuoteRequest
    from app.providers.eodhd.warrant_quote import EodhdWarrantQuoteAdapter

    request = WarrantQuoteRequest(
        workspace_id=uuid4(),
        warrant_listing_id=uuid4(),
        correlation_id=uuid4(),
        as_of=datetime.now(UTC),
    )
    with pytest.raises(MarketDataConfigurationError) as exc_info:
        await EodhdWarrantQuoteAdapter().get_warrant_listing_quote(request)
    assert exc_info.value.retryable is False
