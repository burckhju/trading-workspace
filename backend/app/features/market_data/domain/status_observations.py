"""Independent instrument-status facts; a point never establishes an interval."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.features.market_data.domain.original_market_status_evidence import (
    MarketStatus,
    OriginalMarketStatusEvidence,
    _utc,
)


@dataclass(frozen=True, slots=True)
class StatusRouteBinding:
    workspace_id: UUID
    warrant_id: UUID
    warrant_listing_id: UUID
    provider: str
    identity_key: str
    isin: str
    venue_mic: str

    def __post_init__(self) -> None:
        if (
            re.fullmatch(r"[0-9a-f]{64}", self.identity_key) is None
            or re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", self.isin) is None
            or re.fullmatch(r"[A-Z0-9]{4}", self.venue_mic) is None
            or not self.provider
        ):
            raise ValueError("ORIGINAL_MARKET_STATUS_ROUTE_INVALID")


@dataclass(frozen=True, slots=True)
class MarketStatusObservation:
    """First receipt of one source fact, or one explicitly observed delivery gap.

    The fingerprint identifies our canonical fact, not original response bytes.
    Re-receiving the same fact never resets any of its original/receipt clocks.
    """

    id: UUID
    fingerprint: str
    route: StatusRouteBinding
    captured_at: datetime
    retrieved_at: datetime | None
    original: OriginalMarketStatusEvidence | None
    reason: str | None

    def __post_init__(self) -> None:
        _utc(self.captured_at, "captured_at")
        if self.retrieved_at is not None:
            _utc(self.retrieved_at, "retrieved_at")
        if (
            re.fullmatch(r"[0-9a-f]{64}", self.fingerprint) is None
            or (self.retrieved_at is not None and self.retrieved_at > self.captured_at)
            or (self.original is None and not self.reason)
            or (
                self.original is not None
                and (
                    self.reason is not None
                    or self.original.isin != self.route.isin
                    or self.original.venue_mic != self.route.venue_mic
                    or self.retrieved_at is None
                    or self.original.generated_at > self.retrieved_at
                )
            )
        ):
            raise ValueError("ORIGINAL_MARKET_STATUS_OBSERVATION_INVALID")

    @property
    def kind(self) -> Literal["STATUS", "GAP"]:
        return "STATUS" if self.original is not None else "GAP"


@dataclass(frozen=True, slots=True)
class StatusSourceHistory:
    """Observed source/route provenance, never an inferred validity interval."""

    route: StatusRouteBinding
    source_contract: str | None
    source_reference: str | None
    first_captured_at: datetime
    last_captured_at: datetime


@dataclass(frozen=True, slots=True)
class StatusEvidenceRead:
    route: StatusRouteBinding
    event_at: datetime
    known_at: datetime
    point_verdict: Literal["OBSERVED_AT_INSTANT", "CONFLICTING_POINTS", "NO_POINT_AT_EVENT"]
    observed_status: MarketStatus | None
    point_observations: tuple[MarketStatusObservation, ...]
    latest_observations: tuple[MarketStatusObservation, ...]
    latest_capture: MarketStatusObservation | None
    latest_gap: MarketStatusObservation | None
    other_route_keys: tuple[str, ...] = ()
    source_contract: str | None = None
    source_reference: str | None = None
    source_history: tuple[StatusSourceHistory, ...] = ()
    definition_version: Literal["market-status-observations-v1"] = field(
        default="market-status-observations-v1", init=False
    )
    source_qualification: Literal["NOT_INDEPENDENTLY_VERIFIED"] = field(
        default="NOT_INDEPENDENTLY_VERIFIED", init=False
    )
    status_validity_interval: Literal["NOT_ESTABLISHED"] = field(
        default="NOT_ESTABLISHED", init=False
    )


def resolve_status_observations(
    observations: tuple[MarketStatusObservation, ...],
    *,
    route: StatusRouteBinding,
    event_at: datetime,
    known_at: datetime,
    source_contract: str | None = None,
    source_reference: str | None = None,
    other_route_keys: tuple[str, ...] = (),
    source_history: tuple[StatusSourceHistory, ...] = (),
) -> StatusEvidenceRead:
    """Resolve source points by event time, never by arrival order or price success.

    A delayed CLOSED point remains visible without retroactively declaring the
    current market closed. Opposing statuses at the same instant are a conflict,
    including when supplied in different envelopes. A gap cannot assert CLOSED
    or preserve an old OPEN. Source filtering is exact and has no fallback.
    """
    _utc(event_at, "event_at")
    _utc(known_at, "known_at")
    if event_at > known_at:
        raise ValueError("STATUS_EVENT_AFTER_KNOWN_AT")
    eligible = tuple(
        item
        for item in observations
        if item.route == route
        and item.captured_at <= known_at
        and (item.retrieved_at is None or item.retrieved_at <= known_at)
    )
    points = tuple(
        item
        for item in eligible
        if item.original is not None
        and item.original.generated_at <= known_at
        and (source_contract is None or item.original.source_contract == source_contract)
        and (source_reference is None or item.original.source_reference == source_reference)
    )
    at_event = tuple(
        sorted(
            (item for item in points if item.original and item.original.observed_at == event_at),
            key=lambda item: item.fingerprint,
        )
    )
    statuses = {item.original.status for item in at_event if item.original is not None}
    latest_at = max((item.original.observed_at for item in points if item.original), default=None)
    latest = tuple(
        sorted(
            (item for item in points if item.original and item.original.observed_at == latest_at),
            key=lambda item: item.fingerprint,
        )
    )
    gaps = tuple(item for item in eligible if item.original is None)

    def order(item: MarketStatusObservation) -> tuple[datetime, str]:
        return item.captured_at, item.fingerprint

    return StatusEvidenceRead(
        route=route,
        event_at=event_at,
        known_at=known_at,
        point_verdict=(
            "CONFLICTING_POINTS"
            if len(statuses) > 1
            else "OBSERVED_AT_INSTANT" if statuses else "NO_POINT_AT_EVENT"
        ),
        observed_status=next(iter(statuses)) if len(statuses) == 1 else None,
        point_observations=at_event,
        latest_observations=latest,
        latest_capture=max(eligible, key=order, default=None),
        latest_gap=max(gaps, key=order, default=None),
        other_route_keys=other_route_keys,
        source_contract=source_contract,
        source_reference=source_reference,
        source_history=source_history,
    )
