"""Public, provider-neutral EOD read contract shared by charts and future consumers.

No provider calls, identity creation, commits or backfills belong in this reader.
Trading dates are dates, not observed-at timestamps. Received/source timestamps
remain independent metadata. A date-limited read is not a point-in-time backtest.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

MAX_SERIES_POINTS = 10_000


@dataclass(frozen=True)
class SeriesObservation:
    trading_date: date
    close: Decimal
    adjusted_close: Decimal | None
    currency: str
    provider: str
    provider_symbol: str
    received_at: datetime
    source_updated_at: datetime | None
    quality: str
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class SeriesCoverage:
    count: int
    first_date: date | None
    last_date: date | None


class TimeSeriesReader(Protocol):
    async def observations(
        self, workspace_id: UUID, instrument_id: UUID, start: date, end: date
    ) -> tuple[SeriesObservation, ...]: ...

    async def coverage(
        self, workspace_id: UUID, instrument_ids: tuple[UUID, ...], end: date
    ) -> dict[UUID, SeriesCoverage]: ...
