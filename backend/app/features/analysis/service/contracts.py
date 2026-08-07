"""Ports consumed by the analysis application service."""

from __future__ import annotations

from datetime import date
from typing import Protocol
from uuid import UUID

from app.features.market_data.domain.models import DailyPrice


class AnalysisMarketDataReader(Protocol):
    async def list_daily_prices(
        self, workspace_id: UUID, listing_id: UUID, start_date: date, end_date: date
    ) -> tuple[DailyPrice, ...]: ...


class AnalysisReferenceReader(Protocol):
    async def validate_reference(
        self, workspace_id: UUID, underlying_id: UUID, listing_id: UUID
    ) -> bool: ...
