from datetime import UTC, date, datetime, timedelta
from random import Random
from uuid import uuid4

import pytest

from app.features.market_data.domain.enums import CacheStatus, MappingStatus, MarketDataCapability, MarketDataProvider
from app.features.market_data.domain.models import ProviderInstrumentMapping
from app.features.market_data.service.types import DailyPriceRequest, LatestDailyPriceRequest
from app.providers.eodhd.adapter import EodhdMarketDataAdapter
from app.providers.shared.budget import DailyCallBudget
from app.providers.shared.cache import InMemoryTtlCache
from app.providers.shared.rate_limit import TokenBucketRateLimiter
from app.providers.shared.retry import RetryPolicy


class FakeClock:
    def __init__(self):
        self.now = datetime(2026, 8, 5, 12, tzinfo=UTC)
        self.mono = 0.0
    def utcnow(self): return self.now
    def monotonic(self): return self.mono

class FakeSleeper:
    def __init__(self, clock): self.clock=clock
    async def sleep(self, seconds): self.clock.mono += seconds

class FakeClient:
    def __init__(self): self.calls=[]
    async def get_json(self, path, *, capability, params=None):
        self.calls.append((path, capability, params))
        return [
            {"date":"2026-08-01","open":"10","high":"12","low":"9","close":"11","adjusted_close":"11","volume":"100"},
            {"date":"2026-08-04","open":"11","high":"13","low":"10","close":"12","adjusted_close":"12","volume":None},
        ]

class Mappings:
    def __init__(self, value): self.value=value
    async def get_mapping(self, workspace_id, mapping_id): return self.value

class Currencies:
    async def get_currency(self, workspace_id, listing_id): return "USD"


def make_adapter():
    clock=FakeClock(); sleeper=FakeSleeper(clock); client=FakeClient()
    now=clock.utcnow(); mapping=ProviderInstrumentMapping(
        id=uuid4(), workspace_id=uuid4(), listing_id=uuid4(), provider=MarketDataProvider.EODHD,
        provider_symbol="AAPL", provider_exchange_code="US", status=MappingStatus.ACTIVE,
        validated_at=now, validation_message=None, created_at=now, updated_at=now, version=1,
    )
    adapter=EodhdMarketDataAdapter(
        client=client, mappings=Mappings(mapping), currencies=Currencies(),
        cache=InMemoryTtlCache(clock=clock),
        retry_policy=RetryPolicy(clock=clock, sleeper=sleeper, random=Random(0)),
        rate_limiter=TokenBucketRateLimiter(requests_per_second=10, burst_capacity=2, clock=clock, sleeper=sleeper),
        call_budget=DailyCallBudget(configured_budget=100, safety_reserve_percent=0, clock=clock, provider=MarketDataProvider.EODHD),
        clock=clock,
    )
    return adapter, client, mapping


@pytest.mark.asyncio
async def test_historical_fetch_maps_and_caches() -> None:
    adapter, client, mapping = make_adapter()
    request=DailyPriceRequest(workspace_id=mapping.workspace_id, listing_id=mapping.listing_id, mapping_id=mapping.id, start_date=date(2026,8,1), end_date=date(2026,8,4), correlation_id=uuid4())
    first=await adapter.get_daily_prices(request)
    second=await adapter.get_daily_prices(request)
    assert [p.trading_date for p in first.data] == [date(2026,8,1), date(2026,8,4)]
    assert first.cache_status is CacheStatus.MISS
    assert first.provider_call_cost == 1
    assert second.cache_status is CacheStatus.HIT
    assert second.provider_call_cost == 0
    assert len(client.calls) == 1
    assert client.calls[0][0] == "/eod/AAPL.US"


@pytest.mark.asyncio
async def test_latest_returns_newest_completed_row() -> None:
    adapter, _, mapping = make_adapter()
    result=await adapter.get_latest_completed_daily_price(LatestDailyPriceRequest(workspace_id=mapping.workspace_id, listing_id=mapping.listing_id, mapping_id=mapping.id, correlation_id=uuid4(), as_of_date=date(2026,8,4)))
    assert result.data is not None
    assert result.data.trading_date == date(2026,8,4)
    assert result.capability is MarketDataCapability.LATEST_COMPLETED_DAILY_PRICE

@pytest.mark.asyncio
async def test_validate_mapping_requires_exact_symbol_and_exchange_match() -> None:
    adapter, client, mapping = make_adapter()
    async def search(path, *, capability, params=None):
        client.calls.append((path, capability, params))
        return [{"Code": mapping.provider_symbol, "Exchange": mapping.provider_exchange_code, "Currency": "EUR"}]
    client.get_json = search
    result = await adapter.validate_mapping(mapping)
    assert result.status is MappingStatus.ACTIVE
    assert result.currency == "EUR"


@pytest.mark.asyncio
async def test_validate_mapping_marks_non_matching_search_result_invalid() -> None:
    adapter, client, mapping = make_adapter()
    async def search(path, *, capability, params=None):
        return [{"Code": "OTHER", "Exchange": mapping.provider_exchange_code}]
    client.get_json = search
    result = await adapter.validate_mapping(mapping)
    assert result.status is MappingStatus.INVALID
