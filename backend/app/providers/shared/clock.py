"""Injectable time and sleeping abstractions for deterministic provider tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from time import monotonic
from typing import Protocol


class Clock(Protocol):
    """Supply UTC wall-clock and monotonic time values."""

    def utcnow(self) -> datetime:
        """Return the current timezone-aware UTC timestamp."""
        ...

    def monotonic(self) -> float:
        """Return a monotonically increasing time value in seconds."""
        ...


class Sleeper(Protocol):
    """Suspend asynchronous execution for a requested duration."""

    async def sleep(self, seconds: float) -> None:
        """Sleep for a non-negative number of seconds."""
        ...


class SystemClock:
    """Production clock backed by Python's system and monotonic clocks."""

    def utcnow(self) -> datetime:
        """Return the current UTC timestamp."""
        return datetime.now(UTC)

    def monotonic(self) -> float:
        """Return the process monotonic clock value."""
        return monotonic()


class AsyncioSleeper:
    """Production sleeper backed by ``asyncio.sleep``."""

    async def sleep(self, seconds: float) -> None:
        """Suspend the current task without blocking the event loop."""
        await asyncio.sleep(seconds)
