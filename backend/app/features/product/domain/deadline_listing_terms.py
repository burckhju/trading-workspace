"""Original listing-date evidence with explicit user-supplied provenance limits."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from uuid import UUID

PARSER_VERSION = "stuttgart-listing-terms-original-v1"
VERIFICATION = "USER_SUPPLIED_ORIGINAL_NOT_INDEPENDENT_VERIFICATION"


@dataclass(frozen=True, slots=True)
class OriginalListingTermsFacts:
    isin: str
    wkn: str
    source_reference: str
    last_trading_on: date | None
    issues: tuple[str, ...]
    venue_mic: Literal["XSTU"] = "XSTU"
    parser_version: str = PARSER_VERSION


@dataclass(frozen=True, slots=True)
class ProductListingTermsRead:
    workspace_id: UUID
    warrant_id: UUID
    known_at: datetime
    status: Literal["AVAILABLE", "MISSING", "UNSUITABLE"]
    reasons: tuple[str, ...]
    revision_id: UUID | None
    revision_number: int
    recorded_at: datetime | None
    fingerprint: str
    terms_id: UUID | None
    last_trading_on: date | None
    venue_mic: str | None
    source_reference: str | None
    document_sha256: str | None
    verification: str = VERIFICATION
    receipt_time_basis: Literal["FILE_RECEIVED_AT"] = "FILE_RECEIVED_AT"
