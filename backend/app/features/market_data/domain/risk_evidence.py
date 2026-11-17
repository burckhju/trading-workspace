"""Persisted quote evidence exposed without implying a price series or fresh fetch."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.features.market_data.domain.models import WarrantQuoteSnapshot


@dataclass(frozen=True, slots=True)
class SavedQuoteRouteBinding:
    """Current selected route, explicitly bound to the held instrument."""

    workspace_id: UUID
    position_id: UUID
    warrant_id: UUID
    warrant_listing_id: UUID
    trading_venue_id: UUID
    venue_mic: str
    currency: str
    identity_key: str
    selection_id: UUID
    selected_at: datetime


@dataclass(frozen=True, slots=True)
class SavedQuoteProvenance:
    """Provenance of the current mutable last-success, never a historical replay.

    The fingerprint covers the complete stored JSON value, canonically encoded;
    it is not a hash of original provider response bytes. This store records no
    capture timestamp. Neither retrieval nor observation time can replace it.
    """

    read_at: datetime
    raw_payload_fingerprint: str
    retrieved_at: datetime | None = None
    quality_status: str | None = None
    warnings: tuple[str, ...] = ()
    reason_code: str | None = None
    stored_at: None = field(default=None, init=False)
    stored_at_status: Literal["NOT_RECORDED_BY_LAST_SUCCESS_STORE"] = field(
        default="NOT_RECORDED_BY_LAST_SUCCESS_STORE", init=False
    )
    storage_kind: Literal["LAST_SUCCESS"] = field(default="LAST_SUCCESS", init=False)
    mutable: Literal[True] = field(default=True, init=False)
    historical_read: Literal[False] = field(default=False, init=False)


@dataclass(frozen=True, slots=True)
class SavedQuoteEvidence:
    reason: str
    quote: WarrantQuoteSnapshot | None = None
    provider: str | None = None
    retrieved_at: datetime | None = None
    identity_key: str | None = None
    refresh_status: str = "LATEST_REFRESH_NOT_OBSERVED_BY_PERSISTED_READER"
    history_observations: int = 0
    route: SavedQuoteRouteBinding | None = None
    provenance: SavedQuoteProvenance | None = None
