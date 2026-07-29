"""Clock abstraction for deterministic time-dependent code."""

from datetime import datetime
from typing import Protocol, runtime_checkable

from app.shared.utils import utc_now


@runtime_checkable
class Clock(Protocol):
    """Provide the current timezone-aware UTC time."""

    def now(self) -> datetime:
        """Return the current instant in UTC."""


class SystemClock:
    """Production clock backed by the operating system clock."""

    def now(self) -> datetime:
        """Return the current instant in UTC."""

        return utc_now()
