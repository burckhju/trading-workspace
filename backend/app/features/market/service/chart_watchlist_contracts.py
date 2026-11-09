"""Bounded read/write contracts; setup labels are projections, not financial states."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChartWatchlistActivationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    catalog_version: str = Field(min_length=1, max_length=80)
    confirmed: Literal[True]


class ChartWatchlistHistory(BaseModel):
    first_date: date | None = None
    last_date: date | None = None
    observation_count: int = 0
    last_received_at: datetime | None = None


class ChartWatchlistMapping(BaseModel):
    id: UUID
    version: int
    status: str
    provider_symbol: str
    provider_exchange_code: str
    validated_at: datetime | None


class ChartWatchlistRefresh(BaseModel):
    """Existing EOD job evidence from this backend process, not durable price history."""

    status: str
    reason: str | None = None
    checked_at: datetime | None = None
    last_success_at: datetime | None = None
    next_run_at: datetime | None = None
    scope: Literal["PROCESS_LOCAL"] = "PROCESS_LOCAL"


class ChartWatchlistItemResponse(BaseModel):
    code: str
    kind: Literal["INDEX", "ETF"]
    name: str
    group: str
    isin: str | None = None
    mic: str | None = None
    currency: str | None = None
    ticker: str | None = None
    source_url: str
    target_key: str | None = None
    setup_status: Literal["PENDING", "CONFIGURED", "BLOCKED"] = "PENDING"
    setup_reason: str | None = None
    last_attempt_at: datetime | None = None
    setup_completed_at: datetime | None = None
    history: ChartWatchlistHistory = Field(default_factory=ChartWatchlistHistory)
    mapping: ChartWatchlistMapping | None = None
    refresh: ChartWatchlistRefresh | None = None


class ChartWatchlistResponse(BaseModel):
    catalog_version: str
    name: str
    enabled: bool
    items: tuple[ChartWatchlistItemResponse, ...]
    scheduler: dict[str, Any] = Field(default_factory=dict)


class ChartWatchlistError(ValueError):
    """Stable, non-secret operation outcome suitable for API and retry diagnostics."""

    def __init__(self, code: str, *, status_code: int = 409) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code
