"""Injectable in-memory TTL cache for technical provider responses."""

from __future__ import annotations

import asyncio
from collections.abc import Hashable
from dataclasses import dataclass
from datetime import timedelta

from app.providers.shared.clock import Clock


@dataclass(frozen=True, slots=True)
class CacheLookup[V]:
    """Describe whether a cache lookup returned fresh or stale data."""

    value: V | None
    hit: bool
    stale: bool


@dataclass(slots=True)
class _Entry[V]:
    value: V
    expires_at: float


class InMemoryTtlCache[K: Hashable, V]:
    """Single-process TTL cache with atomic access and explicit stale rejection."""

    def __init__(self, *, clock: Clock) -> None:
        self._clock = clock
        self._entries: dict[K, _Entry[V]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: K) -> CacheLookup[V]:
        """Return fresh data or report a rejected stale entry without serving it."""
        async with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return CacheLookup(value=None, hit=False, stale=False)
            if entry.expires_at <= self._clock.monotonic():
                del self._entries[key]
                return CacheLookup(value=None, hit=False, stale=True)
            return CacheLookup(value=entry.value, hit=True, stale=False)

    async def set(self, key: K, value: V, *, ttl: timedelta) -> None:
        """Store a value for a strictly positive TTL."""
        seconds = ttl.total_seconds()
        if seconds <= 0:
            raise ValueError("ttl must be positive")
        async with self._lock:
            self._entries[key] = _Entry(
                value=value,
                expires_at=self._clock.monotonic() + seconds,
            )

    async def delete(self, key: K) -> bool:
        """Delete one entry and report whether it existed."""
        async with self._lock:
            return self._entries.pop(key, None) is not None

    async def clear(self) -> None:
        """Remove all entries from this process-local cache."""
        async with self._lock:
            self._entries.clear()
