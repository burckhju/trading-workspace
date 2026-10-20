"""Persisted quote evidence exposed without implying a price series or fresh fetch."""

from dataclasses import dataclass
from datetime import datetime

from app.features.market_data.domain.models import WarrantQuoteSnapshot


@dataclass(frozen=True, slots=True)
class SavedQuoteEvidence:
    reason: str
    quote: WarrantQuoteSnapshot | None = None
    provider: str | None = None
    retrieved_at: datetime | None = None
    identity_key: str | None = None
    refresh_status: str = "LATEST_REFRESH_NOT_OBSERVED_BY_PERSISTED_READER"
    history_observations: int = 0
