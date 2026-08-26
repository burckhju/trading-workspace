from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from types import TracebackType
from uuid import UUID, uuid4

import pytest

from app.features.market_data.domain.enums import (
    CacheStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import DailyPrice
from app.features.market_data.persistence.models import DailyPriceModel
from app.features.market_data.service.application import DailyPriceImportService
from app.features.market_data.service.types import DailyPriceRequest, MarketDataResult

NOW = datetime(2026, 8, 26, 18, tzinfo=UTC)


class MappingRepo:
    def __init__(self, listing_id: UUID, instrument_id: UUID) -> None:
        self.mapping = type(
            "Mapping",
            (),
            {
                "listing_id": listing_id,
                "market_data_instrument_id": instrument_id,
            },
        )()

    async def get(self, workspace_id: UUID, mapping_id: UUID):
        return self.mapping


class PriceRepo:
    def __init__(self) -> None:
        self.added: list[DailyPriceModel] = []
        self.flushed = False

    async def get(self, *args):
        return None

    async def add(self, value: DailyPriceModel) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        self.flushed = True


class Uow:
    def __init__(self, listing_id: UUID, instrument_id: UUID) -> None:
        self.mappings = MappingRepo(listing_id, instrument_id)
        self.daily_prices = PriceRepo()
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        return None


class Provider:
    def __init__(self, value: DailyPrice) -> None:
        self.value = value

    async def get_daily_prices(self, request: DailyPriceRequest) -> MarketDataResult[DailyPrice]:
        return MarketDataResult(
            (self.value,),
            MarketDataProvider.EODHD,
            MarketDataCapability.HISTORICAL_DAILY_PRICES,
            uuid4(),
            NOW,
            CacheStatus.MISS,
            QualityStatus.VALID,
            (),
            0,
            1,
        )


def _price(listing_id: UUID) -> DailyPrice:
    return DailyPrice(
        listing_id=listing_id,
        trading_date=date(2026, 8, 25),
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("99"),
        close=Decimal("101"),
        adjusted_close=None,
        volume=None,
        currency="EUR",
        provider=MarketDataProvider.EODHD,
        provider_symbol="TEST.XETRA",
        retrieved_at=NOW,
        source_updated_at=None,
        quality_status=QualityStatus.VALID,
    )


@pytest.mark.asyncio
async def test_import_dual_writes_mapping_instrument_identity() -> None:
    workspace_id = uuid4()
    listing_id = uuid4()
    mapping_id = uuid4()
    instrument_id = uuid4()
    uow = Uow(listing_id, instrument_id)
    service = DailyPriceImportService(
        uow=uow,
        provider=Provider(_price(listing_id)),
        clock=lambda: NOW,
        id_factory=uuid4,
    )
    request = DailyPriceRequest(
        workspace_id,
        listing_id,
        mapping_id,
        date(2026, 8, 25),
        date(2026, 8, 25),
        uuid4(),
    )

    result = await service.import_daily_prices(request)

    assert result.inserted == 1
    assert uow.committed and uow.daily_prices.flushed
    assert len(uow.daily_prices.added) == 1
    assert uow.daily_prices.added[0].listing_id == listing_id
    assert uow.daily_prices.added[0].market_data_instrument_id == instrument_id
