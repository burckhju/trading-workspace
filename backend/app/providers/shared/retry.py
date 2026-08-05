"""Bounded asynchronous retry execution for provider operations."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from random import Random
from typing import TypeVar

from app.features.market_data.service.errors import MarketDataError
from app.providers.shared.clock import Clock, Sleeper

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RetryOutcome[T]:
    """Successful operation value and number of retries consumed."""

    value: T
    retry_count: int


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Execute retryable operations with exponential full-jitter backoff."""

    clock: Clock
    sleeper: Sleeper
    random: Random
    max_attempts: int = 3
    base_delay_seconds: float = 0.5
    max_retry_after_seconds: float = 30.0
    total_timeout_seconds: float = 45.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least one")
        if self.base_delay_seconds < 0:
            raise ValueError("base_delay_seconds must not be negative")
        if self.max_retry_after_seconds < 0 or self.total_timeout_seconds <= 0:
            raise ValueError("retry time limits must be positive")

    async def execute(self, operation: Callable[[], Awaitable[T]]) -> RetryOutcome[T]:
        """Execute an operation and retry only explicit retryable market-data errors."""
        started_at = self.clock.monotonic()
        attempt = 1
        while True:
            try:
                return RetryOutcome(value=await operation(), retry_count=attempt - 1)
            except MarketDataError as error:
                if not error.retryable or attempt >= self.max_attempts:
                    raise
                delay = self._delay_seconds(error, retry_index=attempt - 1)
                elapsed = self.clock.monotonic() - started_at
                if elapsed + delay > self.total_timeout_seconds:
                    raise
                await self.sleeper.sleep(delay)
                attempt += 1

    def _delay_seconds(self, error: MarketDataError, *, retry_index: int) -> float:
        if error.retry_after is not None:
            return min(
                max(error.retry_after.total_seconds(), 0.0),
                self.max_retry_after_seconds,
            )
        ceiling = self.base_delay_seconds * (2**retry_index)
        return self.random.uniform(0.0, ceiling)
