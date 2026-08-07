"""Tests for the daily provider-call budget."""

from datetime import UTC, datetime

import pytest

from app.features.market_data.domain.enums import (
    MarketDataCapability,
    MarketDataProvider,
)
from app.features.market_data.service.errors import MarketDataBudgetExhaustedError
from app.providers.shared.budget import DailyCallBudget
from tests.unit.backend.providers.shared.fakes import ManualClock

CAPABILITY = MarketDataCapability.HISTORICAL_DAILY_PRICES


@pytest.mark.asyncio
async def test_budget_applies_reserve_and_rejects_excess_usage() -> None:
    clock = ManualClock(datetime(2026, 8, 5, 10, tzinfo=UTC))
    budget = DailyCallBudget(
        configured_budget=20,
        safety_reserve_percent=10,
        clock=clock,
        provider=MarketDataProvider.EODHD,
    )

    assert budget.effective_budget == 18
    assert await budget.consume(18, capability=CAPABILITY) == 18
    with pytest.raises(MarketDataBudgetExhaustedError) as exc_info:
        await budget.consume(1, capability=CAPABILITY)

    assert exc_info.value.code == "MARKET_DATA_BUDGET_EXHAUSTED"
    assert exc_info.value.retryable is False


@pytest.mark.asyncio
async def test_budget_resets_at_utc_day_boundary() -> None:
    clock = ManualClock(datetime(2026, 8, 5, 23, 59, tzinfo=UTC))
    budget = DailyCallBudget(
        configured_budget=10,
        safety_reserve_percent=0,
        clock=clock,
        provider=MarketDataProvider.EODHD,
    )
    await budget.consume(10, capability=CAPABILITY)
    clock.advance(60)

    assert await budget.usage() == 0
    assert await budget.consume(10, capability=CAPABILITY) == 10


@pytest.mark.parametrize(
    ("configured_budget", "reserve"),
    [(0, 10), (10, -1), (10, 100)],
)
def test_budget_rejects_invalid_configuration(configured_budget: int, reserve: int) -> None:
    clock = ManualClock(datetime(2026, 8, 5, 10, tzinfo=UTC))
    with pytest.raises(ValueError):
        DailyCallBudget(
            configured_budget=configured_budget,
            safety_reserve_percent=reserve,
            clock=clock,
            provider=MarketDataProvider.EODHD,
        )


@pytest.mark.asyncio
async def test_external_usage_synchronization_never_reduces_local_usage() -> None:
    clock = ManualClock(datetime(2026, 8, 5, 10, tzinfo=UTC))
    budget = DailyCallBudget(
        configured_budget=20,
        safety_reserve_percent=0,
        clock=clock,
        provider=MarketDataProvider.EODHD,
    )
    await budget.consume(5, capability=MarketDataCapability.HISTORICAL_DAILY_PRICES)
    current = await budget.synchronize_usage(3, usage_day=budget.clock.utcnow().date())
    assert current == 5
    current = await budget.synchronize_usage(8, usage_day=budget.clock.utcnow().date())
    assert current == 8
