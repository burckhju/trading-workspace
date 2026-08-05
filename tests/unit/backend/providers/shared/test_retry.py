"""Tests for bounded retry execution."""

from datetime import UTC, datetime, timedelta
from random import Random

import pytest

from app.features.market_data.service.errors import (
    MarketDataNotFoundError,
    MarketDataUnavailableError,
)
from app.providers.shared.retry import RetryPolicy
from tests.unit.backend.providers.shared.fakes import AdvancingSleeper, ManualClock


@pytest.mark.asyncio
async def test_retry_returns_retry_count_after_transient_failures() -> None:
    clock = ManualClock(datetime(2026, 8, 5, 10, tzinfo=UTC))
    sleeper = AdvancingSleeper(clock)
    policy = RetryPolicy(clock=clock, sleeper=sleeper, random=Random(1))
    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise MarketDataUnavailableError("temporary", retryable=True)
        return "ok"

    outcome = await policy.execute(operation)

    assert outcome.value == "ok"
    assert outcome.retry_count == 2
    assert attempts == 3
    assert len(sleeper.calls) == 2
    assert 0 <= sleeper.calls[0] <= 0.5
    assert 0 <= sleeper.calls[1] <= 1.0


@pytest.mark.asyncio
async def test_retry_after_takes_precedence_and_is_capped() -> None:
    clock = ManualClock(datetime(2026, 8, 5, 10, tzinfo=UTC))
    sleeper = AdvancingSleeper(clock)
    policy = RetryPolicy(clock=clock, sleeper=sleeper, random=Random(1))
    attempts = 0

    async def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise MarketDataUnavailableError(
                "temporary", retryable=True, retry_after=timedelta(seconds=90)
            )
        return "ok"

    await policy.execute(operation)
    assert sleeper.calls == [30.0]


@pytest.mark.asyncio
async def test_retry_does_not_repeat_permanent_error() -> None:
    clock = ManualClock(datetime(2026, 8, 5, 10, tzinfo=UTC))
    sleeper = AdvancingSleeper(clock)
    policy = RetryPolicy(clock=clock, sleeper=sleeper, random=Random(1))
    attempts = 0

    async def operation() -> None:
        nonlocal attempts
        attempts += 1
        raise MarketDataNotFoundError("missing", retryable=False)

    with pytest.raises(MarketDataNotFoundError):
        await policy.execute(operation)

    assert attempts == 1
    assert sleeper.calls == []


@pytest.mark.asyncio
async def test_retry_stops_when_delay_would_exceed_total_budget() -> None:
    clock = ManualClock(datetime(2026, 8, 5, 10, tzinfo=UTC))
    sleeper = AdvancingSleeper(clock)
    policy = RetryPolicy(
        clock=clock,
        sleeper=sleeper,
        random=Random(1),
        total_timeout_seconds=5,
    )

    async def operation() -> None:
        raise MarketDataUnavailableError(
            "temporary", retryable=True, retry_after=timedelta(seconds=6)
        )

    with pytest.raises(MarketDataUnavailableError):
        await policy.execute(operation)
    assert sleeper.calls == []
