"""Commands and result types for the FT-001 application service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.features.market.domain.enums import LifecycleStatus, UnderlyingType


@dataclass(frozen=True, slots=True)
class Actor:
    id: str | None
    display_name: str


@dataclass(frozen=True, slots=True)
class CreateListing:
    trading_venue_id: UUID
    ticker: str
    currency_code: str
    is_primary: bool = True


@dataclass(frozen=True, slots=True)
class CreateUnderlying:
    workspace_id: UUID
    actor: Actor
    name: str
    primary_listing: CreateListing
    type: UnderlyingType = UnderlyingType.STOCK
    isin: str | None = None
    wkn: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateUnderlying:
    workspace_id: UUID
    underlying_id: UUID
    expected_version: int
    actor: Actor
    name: str | None = None
    isin: str | None | object = ...
    wkn: str | None | object = ...


@dataclass(frozen=True, slots=True)
class ChangeUnderlyingStatus:
    workspace_id: UUID
    underlying_id: UUID
    expected_version: int
    actor: Actor


@dataclass(frozen=True, slots=True)
class DeleteUnderlying:
    workspace_id: UUID
    underlying_id: UUID
    expected_version: int
    actor: Actor


@dataclass(frozen=True, slots=True)
class SearchUnderlyings:
    workspace_id: UUID
    query: str | None = None
    lifecycle_status: LifecycleStatus | None = None
    trading_venue_id: UUID | None = None
    currency_code: str | None = None
    offset: int = 0
    limit: int = 50


@dataclass(frozen=True, slots=True)
class UsageReference:
    reference_type: str
    object_id: UUID


@dataclass(frozen=True, slots=True)
class AddListing:
    workspace_id: UUID
    underlying_id: UUID
    actor: Actor
    trading_venue_id: UUID
    ticker: str
    currency_code: str
    is_primary: bool = False


@dataclass(frozen=True, slots=True)
class UpdateListing:
    workspace_id: UUID
    listing_id: UUID
    expected_version: int
    actor: Actor
    trading_venue_id: UUID | None = None
    ticker: str | None = None
    currency_code: str | None = None
    lifecycle_status: LifecycleStatus | None = None


@dataclass(frozen=True, slots=True)
class SetPrimaryListing:
    workspace_id: UUID
    underlying_id: UUID
    listing_id: UUID
    expected_listing_version: int
    actor: Actor


@dataclass(frozen=True, slots=True)
class AuditEventView:
    id: UUID
    aggregate_type: str
    aggregate_id: UUID
    occurred_at: datetime
    actor_display_name: str
    change_type: str
    version_before: int | None
    version_after: int | None
    field_changes: dict[str, dict[str, Any]]


@dataclass(frozen=True, slots=True)
class UsageSummary:
    usage_type: str
    count: int
    object_ids: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class CreateTradingVenue:
    actor: Actor
    mic: str
    name: str
    country_code: str
    timezone: str


@dataclass(frozen=True, slots=True)
class UpdateTradingVenue:
    venue_id: UUID
    expected_version: int
    actor: Actor
    name: str | None = None
    country_code: str | None = None
    timezone: str | None = None


@dataclass(frozen=True, slots=True)
class ChangeTradingVenueStatus:
    venue_id: UUID
    expected_version: int
    actor: Actor


@dataclass(frozen=True, slots=True)
class CreateIssuer:
    actor: Actor
    legal_name: str
    display_name: str
    country_code: str | None = None
    lei: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateIssuer:
    issuer_id: UUID
    expected_version: int
    actor: Actor
    legal_name: str | None = None
    display_name: str | None = None
    country_code: str | None | object = ...
    lei: str | None | object = ...


@dataclass(frozen=True, slots=True)
class ChangeIssuerStatus:
    issuer_id: UUID
    expected_version: int
    actor: Actor
