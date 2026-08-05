"""UTC-resetting provider call budget with a configurable safety reserve."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date

from app.features.market_data.domain.enums import (
    MarketDataCapability,
    MarketDataProvider,
)
from app.features.market_data.service.errors import MarketDataBudgetExhaustedError
from app.providers.shared.clock import Clock


@dataclass(slots=True)
class DailyCallBudget:
    """Protect a single process from exceeding an effective daily call budget."""

    configured_budget: int
    safety_reserve_percent: int
    clock: Clock
    provider: MarketDataProvider
    _used: int = field(init=False, repr=False)
    _day: date = field(init=False, repr=False)
    _lock: asyncio.Lock = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.configured_budget < 1:
            raise ValueError("configured_budget must be positive")
        if not 0 <= self.safety_reserve_percent < 100:
            raise ValueError("safety_reserve_percent must be between 0 and 99")
        self._used = 0
        self._day = self.clock.utcnow().date()
        self._lock = asyncio.Lock()

    @property
    def effective_budget(self) -> int:
        """Return the usable budget after applying the configured reserve."""
        return int(self.configured_budget * (100 - self.safety_reserve_percent) / 100)

    async def consume(self, cost: int, *, capability: MarketDataCapability) -> int:
        """Atomically consume call units and return the new daily usage."""
        if cost < 1:
            raise ValueError("cost must be positive")
        async with self._lock:
            self._reset_if_needed(self.clock.utcnow().date())
            if self._used + cost > self.effective_budget:
                raise MarketDataBudgetExhaustedError(
                    "Daily provider call budget exhausted",
                    provider=self.provider,
                    capability=capability,
                    retryable=False,
                )
            self._used += cost
            return self._used

    async def synchronize_usage(self, used: int, *, usage_day: date) -> int:
        """Raise local usage to an externally observed value for the same UTC day."""
        if used < 0:
            raise ValueError("used must not be negative")
        async with self._lock:
            self._reset_if_needed(self.clock.utcnow().date())
            if usage_day == self._day:
                self._used = max(self._used, used)
            return self._used

    async def usage(self) -> int:
        """Return today's consumed call units after applying a UTC reset."""
        async with self._lock:
            self._reset_if_needed(self.clock.utcnow().date())
            return self._used

    def _reset_if_needed(self, current_day: date) -> None:
        if current_day != self._day:
            self._day = current_day
            self._used = 0
