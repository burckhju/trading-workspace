"""Current original-document facts for the explicitly indicative review scope.

These facts do not certify historical terms, unchanged units or B58 suitability.
The execution owner remains the only source of quantities and acquisition costs.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from app.features.product.domain.price_scale_evidence import ProductPriceScaleBinding

type ReviewEvidenceStatus = Literal["AVAILABLE", "MISSING", "UNSUITABLE"]
VERIFICATION = "ORIGINAL_DOCUMENT_EXTRACTION_NOT_HISTORICAL_VERIFICATION"


@dataclass(frozen=True, slots=True)
class ProductReviewAcquisitionState:
    outcome: str
    attempted_at: datetime
    next_attempt_at: datetime
    problems: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProductReviewEvidence:
    workspace_id: UUID
    warrant_id: UUID
    known_at: datetime
    status: ReviewEvidenceStatus
    reasons: tuple[str, ...]
    revision_id: UUID | None
    recorded_at: datetime | None
    fingerprint: str
    binding: ProductPriceScaleBinding | None = None
    currency: str | None = None
    unit: str | None = None
    quality: str = "CURRENT_UNIT_HISTORY_ASSUMED"
    source_reference: str | None = None
    source_document_sha256: str | None = None
    reference_venue_mic: str | None = None
    maturity_on: date | None = None
    verification: str = VERIFICATION


@dataclass(frozen=True, slots=True)
class ProductDeadlineEvidence:
    workspace_id: UUID
    warrant_id: UUID
    known_at: datetime
    status: ReviewEvidenceStatus
    reasons: tuple[str, ...]
    revision_id: UUID | None
    recorded_at: datetime | None
    fingerprint: str
    terms_id: UUID | None = None
    maturity_on: date | None = None
    last_trading_on: date | None = None
    exit_listing_id: UUID | None = None
    exit_venue_mic: str | None = None
    source_reference: str | None = None
    verification: str = VERIFICATION
    product_document_revision_id: UUID | None = None
    listing_terms_revision_id: UUID | None = None
    exit_choice_revision_id: UUID | None = None
    product_document_source_reference: str | None = None


@dataclass(frozen=True, slots=True)
class ExtractedProductFacts:
    """Parser output, never a caller supplied trust flag or historical interval."""

    isin: str
    underlying_isin: str | None
    currency: str | None
    unit: str | None
    reference_venue_mic: str | None
    maturity_on: date | None
    last_trading_on: date | None = None
    last_trading_venue_mic: str | None = None
    issues: tuple[str, ...] = ()
