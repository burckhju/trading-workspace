"""Documented product price units, without execution or adjustment arithmetic."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import ClassVar, Final, Literal
from uuid import UUID

MAX_MANIFEST_BYTES = 64_000
MAX_DOCUMENT_BYTES = 2_000_000
SCHEMA_VERSION: Final = "product-price-scale-evidence-v1"
VERIFICATION: Final = "MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION"
type PriceScaleStatus = Literal["UNCHANGED_ORIGINAL", "ADJUSTMENT_REQUIRED", "WITHDRAWN"]


def aware(value: datetime) -> bool:
    return isinstance(value, datetime) and value.utcoffset() is not None


def reference(value: str, maximum: int = 1000) -> None:
    if not isinstance(value, str) or not 3 <= len(value.strip()) <= maximum or "\x00" in value:
        raise ValueError("A concrete bounded evidence reference is required")


def sha256_text(value: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError("An exact lowercase SHA256 is required")


@dataclass(frozen=True, slots=True)
class ProductPriceScaleBinding:
    __pydantic_config__: ClassVar[dict[str, str]] = {"extra": "forbid"}
    warrant_id: UUID
    isin: str
    issuer_id: UUID
    underlying_id: UUID
    current_terms_id: UUID

    def __post_init__(self) -> None:
        if (
            len(self.isin) != 12
            or not self.isin[:2].isalpha()
            or not self.isin[-1].isdigit()
            or any(
                character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" for character in self.isin
            )
        ):
            raise ValueError("An exact uppercase product ISIN is required")


@dataclass(frozen=True, slots=True)
class ProductPriceScaleManifest:
    __pydantic_config__: ClassVar[dict[str, str]] = {"extra": "forbid"}
    scale_id: str
    source_version: str
    binding: ProductPriceScaleBinding
    axis: Literal["WARRANT"]
    currency: str
    unit: Literal["CURRENCY_PER_WARRANT"]
    valid_from: datetime
    valid_until: datetime
    status: PriceScaleStatus
    source_publisher: str
    source_reference: str
    source_document_sha256: str
    source_published_at: datetime | None = None
    source_published_on: date | None = None
    schema_version: Literal["product-price-scale-evidence-v1"] = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for value in (self.scale_id, self.source_version, self.source_publisher):
            reference(value, 200)
        reference(self.source_reference)
        sha256_text(self.source_document_sha256)
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError("Unknown product price scale schema")
        if self.axis != "WARRANT" or self.unit != "CURRENCY_PER_WARRANT":
            raise ValueError("Only original currency units per warrant are supported")
        if len(self.currency) != 3 or any(
            character not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" for character in self.currency
        ):
            raise ValueError("An exact uppercase currency code is required")
        if self.status not in {
            "UNCHANGED_ORIGINAL",
            "ADJUSTMENT_REQUIRED",
            "WITHDRAWN",
        }:
            raise ValueError("Unknown price scale evidence status")
        if (
            not aware(self.valid_from)
            or not aware(self.valid_until)
            or self.valid_until.year == datetime.max.year
            or self.valid_from.astimezone(UTC) >= self.valid_until.astimezone(UTC)
        ):
            raise ValueError("An explicit finite offset-aware validity interval is required")
        if self.source_published_at is not None and (
            not aware(self.source_published_at) or self.source_published_on is not None
        ):
            raise ValueError("Preserve publication clock or date precision without inventing time")


@dataclass(frozen=True, slots=True)
class ProductPriceScaleImportCommand:
    request_id: UUID
    supersedes_revision_id: UUID | None
    manifest_json: str
    manifest_sha256: str
    document_filename: str
    document_media_type: str
    document_base64: str
    document_sha256: str
    reviewed_at: datetime
    review_reference: str
    retrieved_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ProductPriceScaleSource:
    __pydantic_config__: ClassVar[dict[str, str]] = {"extra": "forbid"}
    manifest_sha256: str
    document_sha256: str
    document_filename: str
    document_media_type: str
    publisher: str
    reference: str
    published_at: datetime | None
    published_on: date | None
    retrieved_at: datetime | None
    reviewed_at: datetime
    review_reference: str
    recorded_by: UUID


@dataclass(frozen=True, slots=True)
class ProductPriceScaleRevision:
    id: UUID
    workspace_id: UUID
    warrant_id: UUID
    revision_number: int
    supersedes_revision_id: UUID | None
    request_id: UUID
    request_fingerprint: str
    recorded_at: datetime
    manifest: ProductPriceScaleManifest
    source: ProductPriceScaleSource
    manifest_json: str
    document_base64: str
    verification: Literal["MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION"] = VERIFICATION


@dataclass(frozen=True, slots=True)
class ProductPriceScaleCurrent:
    workspace_id: UUID
    warrant_id: UUID
    known_at: datetime
    revision_id: UUID | None
    supersedes_revision_id: UUID | None
    revision_number: int | None
    manifest: ProductPriceScaleManifest | None
    binding: ProductPriceScaleBinding | None
    source: ProductPriceScaleSource | None
    recorded_at: datetime | None
    read_at: datetime
    status: Literal["AVAILABLE", "MISSING", "UNSUITABLE"]
    reasons: tuple[str, ...]
    fingerprint: str
    verification: Literal["MANUAL_DOCUMENT_REVIEW_NOT_INDEPENDENT_VERIFICATION"] = VERIFICATION
    operation_status: Literal["READ_ONLY"] = "READ_ONLY"
