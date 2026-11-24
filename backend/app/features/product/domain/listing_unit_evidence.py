"""Current listing units, with separate originals and no historical scale claim."""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Literal
from uuid import UUID

from app.features.product.domain.price_scale_evidence import ProductPriceScaleBinding

type ListingUnitStatus = Literal["AVAILABLE", "MISSING", "UNSUITABLE"]
type ListingUnitRuleRole = Literal[
    "EXCHANGE_RULES", "OPEN_MARKET_RULES", "EXECUTION_RULES", "PRODUCT_CLASSIFICATION"
]
QUALITY = "CURRENT_UNIT_HISTORY_ASSUMED"
VERIFICATION = "REVIEWED_ORIGINALS_NOT_HISTORICAL_OR_LIVE_MARKET_VERIFICATION"
SCHEMA_VERSION = "current-listing-unit-evidence-v1"


@dataclass(frozen=True, slots=True)
class ListingUnitRoute:
    __pydantic_config__: ClassVar[dict[str, str]] = {"extra": "forbid"}
    listing_id: UUID
    provider: str
    venue_mic: str
    currency: str


@dataclass(frozen=True, slots=True)
class ListingUnitRuleDocumentSpec:
    """A reviewed public original; transport callers cannot register these pins."""

    role: ListingUnitRuleRole
    source_reference: str
    document_sha256: str
    media_type: str


@dataclass(frozen=True, slots=True)
class ListingUnitRuleSet:
    version: str
    observed_at: datetime
    documents: tuple[ListingUnitRuleDocumentSpec, ...]
    effective_from: datetime | None = None
    venue_mic: str = "MUND"
    currency: str = "EUR"
    product_class: str = "CALL_WARRANT_ON_EQUITY"


@dataclass(frozen=True, slots=True)
class ListingUnitRuleOriginal:
    role: ListingUnitRuleRole
    filename: str
    media_type: str
    document: bytes
    retrieved_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ListingUnitRuleEvidence:
    __pydantic_config__: ClassVar[dict[str, str]] = {"extra": "forbid"}
    role: ListingUnitRuleRole
    filename: str
    media_type: str
    source_reference: str
    document_sha256: str
    document_base64: str
    retrieved_at: datetime | None


@dataclass(frozen=True, slots=True)
class ListingUnitRuleSource:
    role: ListingUnitRuleRole
    source_reference: str
    document_sha256: str
    retrieved_at: datetime | None


@dataclass(frozen=True, slots=True)
class ListingUnitPretradeEvidence:
    __pydantic_config__: ClassVar[dict[str, str]] = {"extra": "forbid"}
    file_name: str
    file_sha256: str
    file_bytes: int
    window_starts_at: datetime
    window_ends_at: datetime
    original_row: str
    row_sha256: str
    isin: str
    venue_mic: str
    currency: str
    observed_at: datetime
    retrieved_at: datetime | None
    parser_version: str = "gettex-delayed-pretrade-parser-v1"
    verification: str = "COMPLETE_GZIP_SCAN_WITH_CRC_AND_EXACT_TARGET_ROW"


@dataclass(frozen=True, slots=True)
class QualifiedGettexListingSource:
    """Internal result of the full-file validator, never a transport trust flag."""

    __pydantic_config__: ClassVar[dict[str, str]] = {"extra": "forbid"}
    rule_set_version: str
    rule_set_fingerprint: str
    rule_originals: tuple[ListingUnitRuleEvidence, ...]
    pretrade: ListingUnitPretradeEvidence
    qualified_at: datetime
    fingerprint: str


@dataclass(frozen=True, slots=True)
class ListingUnitImportCommand:
    request_id: UUID
    expected_revision_id: UUID | None
    route: ListingUnitRoute
    kid_revision_id: UUID
    reviewed_at: datetime
    review_reference: str


@dataclass(frozen=True, slots=True)
class ListingUnitBinding:
    __pydantic_config__: ClassVar[dict[str, str]] = {"extra": "forbid"}
    product: ProductPriceScaleBinding
    route: ListingUnitRoute
    listing_version: int
    trading_venue_id: UUID
    venue_version: int


@dataclass(frozen=True, slots=True)
class ListingUnitImportPreview:
    workspace_id: UUID
    warrant_id: UUID
    binding: ListingUnitBinding
    kid_revision_id: UUID
    kid_document_sha256: str
    product_class: str
    current_revision_id: UUID | None
    next_revision_number: int
    source_fingerprint: str
    fingerprint: str
    operation_status: Literal["READ_ONLY_PREVIEW"] = "READ_ONLY_PREVIEW"


@dataclass(frozen=True, slots=True)
class ListingUnitRevision:
    id: UUID
    workspace_id: UUID
    warrant_id: UUID
    listing_id: UUID
    revision_number: int
    previous_revision_id: UUID | None
    request_id: UUID
    request_fingerprint: str
    binding: ListingUnitBinding
    kid_revision_id: UUID
    kid_document_sha256: str
    product_class: str
    source: QualifiedGettexListingSource
    reviewed_at: datetime
    review_reference: str
    recorded_at: datetime
    recorded_by: UUID
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class ListingUnitRead:
    workspace_id: UUID
    warrant_id: UUID
    route: ListingUnitRoute
    known_at: datetime
    event_at: datetime
    status: ListingUnitStatus
    reasons: tuple[str, ...]
    revision_id: UUID | None
    revision_number: int
    recorded_at: datetime | None
    binding: ListingUnitBinding | None
    unit: str | None
    currency: str | None
    product_class: str | None
    imported_kid_revision_id: UUID | None
    imported_kid_document_sha256: str | None
    current_kid_revision_id: UUID | None
    rule_set_version: str | None
    rule_sources: tuple[ListingUnitRuleSource, ...]
    pretrade_file_name: str | None
    pretrade_file_sha256: str | None
    pretrade_row_sha256: str | None
    pretrade_observed_at: datetime | None
    fingerprint: str
    quality: str = QUALITY
    verification: str = VERIFICATION
    operation_status: Literal["READ_ONLY"] = "READ_ONLY"
