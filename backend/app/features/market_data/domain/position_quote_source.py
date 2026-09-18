"""Domain values for a persistent, fail-closed position quote-source decision."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.features.market_data.domain.enums import MarketDataProvider


class PositionQuoteSourceSelectionStatus(StrEnum):
    SELECTED = "SELECTED"
    NO_VERIFIED_QUOTE_SOURCE = "NO_VERIFIED_QUOTE_SOURCE"
    AMBIGUOUS_SOURCE = "AMBIGUOUS_SOURCE"


@dataclass(frozen=True, slots=True)
class PositionQuoteSourceCandidate:
    provider: MarketDataProvider
    listing_id: UUID
    mapping_id: UUID
    mapping_version: int
    identity_key: str
    currency: str
    mic: str
    provider_exchange_code: str


@dataclass(frozen=True, slots=True)
class PositionQuoteSourceDecision:
    status: PositionQuoteSourceSelectionStatus
    reason: str
    candidates: tuple[PositionQuoteSourceCandidate, ...]
    selected: PositionQuoteSourceCandidate | None = None
