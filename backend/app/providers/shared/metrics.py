"""Process-local, provider-independent operational metrics."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field


@dataclass(slots=True)
class ProviderMetrics:
    """Collect non-secret counters for one provider runtime."""

    _counters: dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    async def increment(self, name: str, value: int = 1) -> None:
        """Atomically increment one non-negative counter."""
        if value < 0:
            raise ValueError("metric increment must not be negative")
        async with self._lock:
            self._counters[name] = self._counters.get(name, 0) + value

    async def snapshot(self) -> dict[str, int]:
        """Return a stable copy of all counters."""
        async with self._lock:
            return dict(self._counters)
