"""Provider-neutral read service for persisted market data."""

from __future__ import annotations

from datetime import date
from typing import Protocol
from uuid import UUID

from app.features.market_data.domain.models import DailyPrice


class MarketDataReader(Protocol):
    async def list_daily_prices(
        self, workspace_id: UUID, listing_id: UUID, start_date: date, end_date: date
    ) -> tuple[DailyPrice, ...]: ...
