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
from app.features.market_data.service.errors import MarketDataMappingError
from app.features.market_data.service.types import DailyPriceRequest, MarketDataResult

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)


def price(listing_id: UUID, close: str = "101") -> DailyPrice:
    return DailyPrice(
        listing_id=listing_id,
        trading_date=date(2026, 8, 4),
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("99"),
        close=Decimal(close),
        adjusted_close=None,
        volume=None,
        currency="EUR",
        provider=MarketDataProvider.EODHD,
        provider_symbol="SAP.XETRA",
        retrieved_at=NOW,
        source_updated_at=None,
        quality_status=QualityStatus.VALID,
    )


class MappingRepo:
    def __init__(self, mapping: object) -> None:
        self.mapping = mapping

    async def get(self, workspace_id: UUID, mapping_id: UUID):
        return self.mapping


class PriceRepo:
    def __init__(self, existing: DailyPriceModel | None = None) -> None:
        self.existing = existing
        self.added: list[DailyPriceModel] = []
        self.flushed = False

    async def get(self, *args):
        return self.existing

    async def add(self, value: DailyPriceModel) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        self.flushed = True


class Uow:
    def __init__(
        self, mapping: object, existing: DailyPriceModel | None = None
    ) -> None:
        self.mappings = MappingRepo(mapping)
        self.daily_prices = PriceRepo(existing)
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ):
        if exc_type:
            await self.rollback()

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


class Provider:
    def __init__(self, result):
        self.result = result

    async def get_daily_prices(self, request):
        return self.result


def request(
    workspace_id: UUID, listing_id: UUID, mapping_id: UUID
) -> DailyPriceRequest:
    return DailyPriceRequest(
        workspace_id,
        listing_id,
        mapping_id,
        date(2026, 8, 4),
        date(2026, 8, 4),
        uuid4(),
    )


def result(value: DailyPrice):
    return MarketDataResult(
        (value,),
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


@pytest.mark.asyncio
async def test_import_inserts_and_commits() -> None:
    workspace_id, listing_id, mapping_id = uuid4(), uuid4(), uuid4()
    mapping = type("Mapping", (), {"listing_id": listing_id})()
    uow = Uow(mapping)
    service = DailyPriceImportService(
        uow=uow,
        provider=Provider(result(price(listing_id))),
        clock=lambda: NOW,
        id_factory=uuid4,
    )
    imported = await service.import_daily_prices(
        request(workspace_id, listing_id, mapping_id)
    )
    assert (imported.inserted, imported.updated, imported.unchanged) == (1, 0, 0)
    assert uow.committed and uow.daily_prices.flushed


@pytest.mark.asyncio
async def test_import_unchanged_does_not_commit() -> None:
    workspace_id, listing_id, mapping_id = uuid4(), uuid4(), uuid4()
    value = price(listing_id)
    from app.features.market_data.persistence.mapping import daily_price_to_model

    existing = daily_price_to_model(
        value, workspace_id=workspace_id, price_id=uuid4(), now=NOW
    )
    mapping = type("Mapping", (), {"listing_id": listing_id})()
    uow = Uow(mapping, existing)
    service = DailyPriceImportService(
        uow=uow, provider=Provider(result(value)), clock=lambda: NOW
    )
    imported = await service.import_daily_prices(
        request(workspace_id, listing_id, mapping_id)
    )
    assert imported.unchanged == 1
    assert not uow.committed and not uow.daily_prices.flushed


@pytest.mark.asyncio
async def test_import_rejects_cross_listing_provider_data_and_rolls_back() -> None:
    workspace_id, listing_id, mapping_id = uuid4(), uuid4(), uuid4()
    mapping = type("Mapping", (), {"listing_id": listing_id})()
    uow = Uow(mapping)
    service = DailyPriceImportService(
        uow=uow, provider=Provider(result(price(uuid4()))), clock=lambda: NOW
    )
    with pytest.raises(MarketDataMappingError):
        await service.import_daily_prices(request(workspace_id, listing_id, mapping_id))
    assert uow.rolled_back and not uow.committed
