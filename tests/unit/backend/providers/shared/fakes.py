"""Deterministic test doubles for provider resilience tests."""

from datetime import UTC, datetime, timedelta


class ManualClock:
    """Controllable UTC and monotonic clock."""

    def __init__(self, current: datetime) -> None:
        if current.tzinfo != UTC:
            raise ValueError("current must use UTC")
        self.current = current
        self.elapsed = 0.0

    def utcnow(self) -> datetime:
        return self.current

    def monotonic(self) -> float:
        return self.elapsed

    def advance(self, seconds: float) -> None:
        self.elapsed += seconds
        self.current += timedelta(seconds=seconds)


class AdvancingSleeper:
    """Record sleeps and advance a manual clock immediately."""

    def __init__(self, clock: ManualClock) -> None:
        self.clock = clock
        self.calls: list[float] = []

    async def sleep(self, seconds: float) -> None:
        self.calls.append(seconds)
        self.clock.advance(seconds)
