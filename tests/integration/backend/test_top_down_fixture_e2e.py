from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from app.features.analysis.domain.calculator import calculate
from app.features.analysis.domain.enums import PriceField
from app.features.analysis.domain.models import AnalysisParameters, SnapshotRow
from app.features.analysis.domain.top_down import (
    TradingDirection,
    calculate_market_context,
    calculate_relative_strength,
)
from app.features.candidate.domain.models import CandidateEvaluationInput
from app.features.candidate.domain.enums import CandidateQualification
from app.features.candidate.domain.qualification import evaluate_candidate
from app.features.market_data.domain.enums import (
    CacheStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import DailyPrice
from app.features.market_data.service.application import DailyPriceImportService
from app.features.market_data.service.types import DailyPriceRequest, MarketDataResult

WORKSPACE_ID = UUID("00000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 8, 10, 12, tzinfo=UTC)


class MappingRepo:
    def __init__(self, listing_id: UUID) -> None:
        self.mapping = SimpleNamespace(listing_id=listing_id)

    async def get(self, workspace_id: UUID, mapping_id: UUID):
        assert workspace_id == WORKSPACE_ID
        return self.mapping


class PriceRepo:
    def __init__(self) -> None:
        self.rows = {}

    async def get(self, workspace_id, listing_id, trading_date, price_type):
        return self.rows.get((workspace_id, listing_id, trading_date, price_type))

    async def add(self, value) -> None:
        self.rows[(value.workspace_id, value.listing_id, value.trading_date, value.price_type)] = value

    async def flush(self) -> None:
        return None


class FixtureUow:
    def __init__(self, listing_id: UUID) -> None:
        self.mappings = MappingRepo(listing_id)
        self.daily_prices = PriceRepo()
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def commit(self):
        self.committed = True

    async def rollback(self):
        return None


@dataclass
class FixtureProvider:
    prices: tuple[DailyPrice, ...]

    async def get_daily_prices(self, request: DailyPriceRequest):
        return MarketDataResult(
            self.prices,
            MarketDataProvider.EODHD,
            MarketDataCapability.HISTORICAL_DAILY_PRICES,
            request.correlation_id,
            NOW,
            CacheStatus.MISS,
            QualityStatus.VALID,
            (),
            0,
            1,
        )


def _series(listing_id: UUID, symbol: str, *, start: Decimal, daily_step: Decimal) -> tuple[DailyPrice, ...]:
    values: list[DailyPrice] = []
    current = date(2025, 10, 1)
    price = start
    for index in range(220):
        # Deterministic weekday-only series, enough for FT-006 200-observation model.
        while current.weekday() >= 5:
            current += timedelta(days=1)
        close = price + daily_step * Decimal(index)
        values.append(
            DailyPrice(
                listing_id=listing_id,
                trading_date=current,
                open=close,
                high=close * Decimal("1.002"),
                low=close * Decimal("0.998"),
                close=close,
                adjusted_close=close,
                volume=Decimal("1000000"),
                currency="USD",
                provider=MarketDataProvider.EODHD,
                provider_symbol=symbol,
                retrieved_at=NOW,
                source_updated_at=None,
                quality_status=QualityStatus.VALID,
            )
        )
        current += timedelta(days=1)
    return tuple(values)


async def _import_and_analyze(
    *, listing_id: UUID, mapping_id: UUID, symbol: str, start: Decimal, daily_step: Decimal
):
    provider_prices = _series(listing_id, symbol, start=start, daily_step=daily_step)
    uow = FixtureUow(listing_id)
    imported = await DailyPriceImportService(
        uow=uow,
        provider=FixtureProvider(provider_prices),
        clock=lambda: NOW,
    ).import_daily_prices(
        DailyPriceRequest(
            WORKSPACE_ID,
            listing_id,
            mapping_id,
            provider_prices[0].trading_date,
            provider_prices[-1].trading_date,
            uuid4(),
        )
    )
    assert imported.inserted == 220
    assert uow.committed

    rows = tuple(
        SnapshotRow(
            trading_date=item.trading_date,
            open=item.open,
            high=item.high,
            low=item.low,
            close=item.close,
            adjusted_close=item.adjusted_close,
            volume=item.volume,
            currency=item.currency,
            provider=item.provider.value,
            provider_symbol=item.provider_symbol,
            quality_status="GOOD",
            warnings=(),
        )
        for item in provider_prices
    )
    computation = calculate(
        AnalysisParameters(price_field=PriceField.ADJUSTED_CLOSE),
        rows,
    )
    criteria = {item.code: item.classification for item in computation.criteria}
    prices = tuple(item.adjusted_close for item in provider_prices if item.adjusted_close is not None)
    return computation, criteria, prices


@pytest.mark.asyncio
async def test_fixture_provider_to_ft006_to_top_down_candidate_e2e() -> None:
    market_listing, sector_listing, stock_listing = uuid4(), uuid4(), uuid4()

    market, market_criteria, market_prices = await _import_and_analyze(
        listing_id=market_listing,
        mapping_id=uuid4(),
        symbol="GSPC.INDX",
        start=Decimal("5000"),
        daily_step=Decimal("5.0"),
    )
    sector, sector_criteria, sector_prices = await _import_and_analyze(
        listing_id=sector_listing,
        mapping_id=uuid4(),
        symbol="TECH.FIXTURE",
        start=Decimal("1000"),
        daily_step=Decimal("2.2"),
    )
    stock, stock_criteria, stock_prices = await _import_and_analyze(
        listing_id=stock_listing,
        mapping_id=uuid4(),
        symbol="MSFT.US",
        start=Decimal("300"),
        daily_step=Decimal("1.2"),
    )

    market_context = calculate_market_context(
        direction=TradingDirection.LONG,
        long_trend=market_criteria["LONG_TREND"],
        medium_trend=market_criteria["MEDIUM_TREND"],
        short_trend=market_criteria["SHORT_TREND"],
        quality_status=market.quality_status,
    )
    sector_rs = calculate_relative_strength(sector_prices, market_prices)
    stock_rs = calculate_relative_strength(stock_prices, sector_prices)

    result = evaluate_candidate(
        CandidateEvaluationInput(
            direction=TradingDirection.LONG,
            market_context=market_context.classification,
            market_quality=market_context.quality_status,
            sector_trend=sector_criteria["LONG_TREND"],
            sector_relative_strength=sector_rs.classification,
            sector_quality=sector.quality_status,
            underlying_long_trend=stock_criteria["LONG_TREND"],
            underlying_medium_trend=stock_criteria["MEDIUM_TREND"],
            underlying_short_trend=stock_criteria["SHORT_TREND"],
            underlying_relative_strength=stock_rs.classification,
            underlying_quality=stock.quality_status,
            momentum=stock_criteria["MOMENTUM_120"],
            volatility=next(item.value for item in stock.criteria if item.code == "VOLATILITY"),
            range_position=next(item.value for item in stock.criteria if item.code == "RANGE_POSITION"),
        )
    )

    assert market_context.classification.value == "FAVORABLE"
    assert sector_rs.classification.value == "POSITIVE"
    assert stock_rs.classification.value == "POSITIVE"
    assert result.qualification is CandidateQualification.QUALIFIED
    assert result.model_id == "TOP_DOWN_CANDIDATE"
    assert result.model_version == "1.0.0"
