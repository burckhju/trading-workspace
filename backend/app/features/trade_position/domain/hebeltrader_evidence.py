"""Append-only references to owner facts, never a second execution ledger."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.features.trade_position.domain.price_binding import PriceBinding


def _reference(value: str) -> None:
    if not 3 <= len(value.strip()) <= 1000:
        raise ValueError("evidence reference must contain 3 to 1000 characters")


@dataclass(frozen=True, slots=True)
class EntryOrderEvidence:
    """An explicitly reviewed order group; membership is never inferred from time."""

    source_reference: str
    execution_ids: tuple[UUID, ...]
    complete: bool

    def __post_init__(self) -> None:
        _reference(self.source_reference)
        if not self.execution_ids or len(set(self.execution_ids)) != len(self.execution_ids):
            raise ValueError("entry group requires distinct execution references")


@dataclass(frozen=True, slots=True)
class UnderlyingTradeEvidence:
    """Reviewed original trade and its exact execution-specific as-of selection.

    A date-only source stays a date. The separate recording clock belongs to the
    enclosing immutable revision; a late historical review has no age cutoff.
    ``last_trade_verified`` records review of the source's as-of selection, not
    an inference from a conveniently close timestamp or a daily OHLC bar.
    """

    execution_id: UUID
    source_reference: str
    price: Decimal
    binding: PriceBinding
    scale_reference: str
    last_trade_verified: bool
    observed_at: datetime | None = None
    observed_on: date | None = None
    observation_timezone: str | None = None
    price_kind: Literal["TRADE"] = "TRADE"

    def __post_init__(self) -> None:
        _reference(self.source_reference)
        _reference(self.scale_reference)
        if not self.price.is_finite() or self.price <= 0:
            raise ValueError("underlying trade price must be finite and positive")
        if self.price_kind != "TRADE":
            raise ValueError("historical entry evidence requires an original trade")
        if (self.observed_at is None) == (self.observed_on is None):
            raise ValueError("provide either an original timestamp or an original date")
        if self.observed_at is not None:
            if self.observed_at.tzinfo is None or self.observation_timezone is not None:
                raise ValueError("original timestamp requires offset and no invented date timezone")
        elif self.observation_timezone is None:
            raise ValueError("original date requires its source timezone")
        else:
            try:
                ZoneInfo(self.observation_timezone)
            except (ZoneInfoNotFoundError, ValueError) as error:
                raise ValueError("original date requires a valid source timezone") from error


@dataclass(frozen=True, slots=True)
class Z1SaleEvidence:
    """Explicit attribution of a real SELL, not a target hit or order request."""

    execution_id: UUID
    source_reference: str

    def __post_init__(self) -> None:
        _reference(self.source_reference)


@dataclass(frozen=True, slots=True)
class HebeltraderEvidenceDeclaration:
    entry_order: EntryOrderEvidence | None = None
    source_version_id: UUID | None = None
    underlying_trades: tuple[UnderlyingTradeEvidence, ...] = ()
    z1_sales: tuple[Z1SaleEvidence, ...] = ()
    z1_sales_reviewed: bool = False
    source_scale_reference: str | None = None
    scale_review_status: Literal["UNVERIFIED", "UNCHANGED_VERIFIED", "ADJUSTMENT_REQUIRED"] = (
        "UNVERIFIED"
    )
    scale_review_reference: str | None = None

    def __post_init__(self) -> None:
        for values in (self.underlying_trades, self.z1_sales):
            ids = [item.execution_id for item in values]
            if len(ids) != len(set(ids)) or len(ids) > 2000:
                raise ValueError("evidence requires distinct bounded execution references")
        if self.entry_order is not None and len(self.entry_order.execution_ids) > 2000:
            raise ValueError("entry group exceeds evidence bound")
        if self.z1_sales and not self.z1_sales_reviewed:
            raise ValueError("Z1 sale attribution requires explicit review")
        if self.source_scale_reference is not None:
            _reference(self.source_scale_reference)
        if self.scale_review_reference is not None:
            _reference(self.scale_review_reference)
        if self.scale_review_status not in {
            "UNVERIFIED",
            "UNCHANGED_VERIFIED",
            "ADJUSTMENT_REQUIRED",
        }:
            raise ValueError("unknown scale review status")
        if self.scale_review_status == "UNCHANGED_VERIFIED" and (
            self.source_scale_reference is None or self.scale_review_reference is None
        ):
            raise ValueError("unchanged comparison scales require a reviewed source reference")


@dataclass(frozen=True, slots=True)
class HebeltraderEvidenceRevision:
    id: UUID
    workspace_id: UUID
    trade_id: UUID
    position_id: UUID
    product_id: UUID
    underlying_id: UUID
    declaration: HebeltraderEvidenceDeclaration
    recorded_at: datetime
    recorded_by: UUID
    request_id: UUID
    request_fingerprint: str
    supersedes_evidence_id: UUID | None = None

    def __post_init__(self) -> None:
        if self.recorded_at.tzinfo is None:
            raise ValueError("evidence recording time must be timezone-aware")
        if self.id == self.supersedes_evidence_id:
            raise ValueError("evidence cannot supersede itself")
