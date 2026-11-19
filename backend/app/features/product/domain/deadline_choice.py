"""Explicit personal product exit listing; no provider or calendar inference."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

DEFINITION_VERSION = "product-deadline-exit-choice-v1"


@dataclass(frozen=True, slots=True)
class ProductDeadlineExitChoice:
    workspace_id: UUID
    warrant_id: UUID
    known_at: datetime
    status: Literal["AVAILABLE", "MISSING", "UNSUITABLE"]
    reasons: tuple[str, ...]
    revision_id: UUID | None
    revision_number: int
    recorded_at: datetime | None
    terms_id: UUID
    current_terms_id: UUID
    exit_listing_id: UUID | None
    exit_listing_version: int | None
    trading_venue_id: UUID | None
    exit_venue_mic: str | None
    venue_version: int | None
    quotation_currency_code: str | None
    fingerprint: str
    verification: Literal["PERSONAL_EXIT_LISTING_CHOICE"] = "PERSONAL_EXIT_LISTING_CHOICE"
    definition_version: str = DEFINITION_VERSION


@dataclass(frozen=True, slots=True)
class ProductDeadlineListingOption:
    listing_id: UUID
    listing_version: int
    venue_name: str
    venue_mic: str
    venue_version: int
    quotation_currency_code: str
    symbol: str | None


@dataclass(frozen=True, slots=True)
class ProductDeadlineChoiceReport:
    warrant_id: UUID
    status: Literal["AVAILABLE", "MISSING", "UNSUITABLE"]
    reasons: tuple[str, ...]
    revision_number: int
    selected_listing_id: UUID | None
    selected_venue_mic: str | None
    terms_id: UUID
    recorded_at: datetime | None
    available_listings: tuple[ProductDeadlineListingOption, ...]
    definition_version: str = DEFINITION_VERSION
