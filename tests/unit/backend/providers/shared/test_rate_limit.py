"""Tests for the local token-bucket limiter."""

from datetime import UTC, datetime

import pytest

from app.providers.shared.rate_limit import TokenBucketRateLimiter
from tests.unit.backend.providers.shared.fakes import AdvancingSleeper, ManualClock


@pytest.mark.asyncio
async def test_token_bucket_allows_burst_then_waits_for_refill() -> None:
    clock = ManualClock(datetime(2026, 8, 5, 10, tzinfo=UTC))
    sleeper = AdvancingSleeper(clock)
    limiter = TokenBucketRateLimiter(
        requests_per_second=2,
        burst_capacity=2,
        clock=clock,
        sleeper=sleeper,
    )

    await limiter.acquire()
    await limiter.acquire()
    await limiter.acquire()

    assert sleeper.calls == [0.5]


@pytest.mark.asyncio
async def test_token_bucket_refills_without_sleep_after_time_advance() -> None:
    clock = ManualClock(datetime(2026, 8, 5, 10, tzinfo=UTC))
    sleeper = AdvancingSleeper(clock)
    limiter = TokenBucketRateLimiter(
        requests_per_second=1,
        burst_capacity=1,
        clock=clock,
        sleeper=sleeper,
    )
    await limiter.acquire()
    clock.advance(1)
    await limiter.acquire()

    assert sleeper.calls == []


@pytest.mark.asyncio
async def test_token_bucket_rejects_cost_above_capacity() -> None:
    clock = ManualClock(datetime(2026, 8, 5, 10, tzinfo=UTC))
    limiter = TokenBucketRateLimiter(
        requests_per_second=1,
        burst_capacity=1,
        clock=clock,
        sleeper=AdvancingSleeper(clock),
    )

    with pytest.raises(ValueError, match="cost"):
        await limiter.acquire(cost=2)
