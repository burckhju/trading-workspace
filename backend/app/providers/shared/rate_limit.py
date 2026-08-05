"""Single-process token-bucket rate limiting for provider requests."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from app.providers.shared.clock import Clock, Sleeper


@dataclass(slots=True)
class TokenBucketRateLimiter:
    """Throttle calls using continuously refilled process-local tokens."""

    requests_per_second: float
    burst_capacity: float
    clock: Clock
    sleeper: Sleeper
    _tokens: float = field(init=False, repr=False)
    _last_refill: float = field(init=False, repr=False)
    _lock: asyncio.Lock = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.requests_per_second <= 0:
            raise ValueError("requests_per_second must be positive")
        if self.burst_capacity < 1:
            raise ValueError("burst_capacity must be at least one")
        self._tokens = self.burst_capacity
        self._last_refill = self.clock.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, *, cost: float = 1.0) -> None:
        """Wait until the requested token cost is available."""
        if cost <= 0 or cost > self.burst_capacity:
            raise ValueError("cost must be positive and not exceed burst_capacity")
        while True:
            async with self._lock:
                self._refill()
                if self._tokens >= cost:
                    self._tokens -= cost
                    return
                wait_seconds = (cost - self._tokens) / self.requests_per_second
            await self.sleeper.sleep(wait_seconds)

    def _refill(self) -> None:
        now = self.clock.monotonic()
        elapsed = max(now - self._last_refill, 0.0)
        self._tokens = min(
            self.burst_capacity,
            self._tokens + elapsed * self.requests_per_second,
        )
        self._last_refill = now
