"""Provider-neutral reference values required by top-down market discovery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from uuid import UUID


class MarketReferenceType(StrEnum):
    INDEX = "INDEX"
    SECTOR_INDEX = "SECTOR_INDEX"


class BenchmarkRole(StrEnum):
    BROAD_MARKET = "BROAD_MARKET"
    GROWTH_TECH = "GROWTH_TECH"
    SECTOR_REFERENCE = "SECTOR_REFERENCE"


@dataclass(frozen=True, slots=True)
class MarketReference:
    id: UUID
    workspace_id: UUID
    code: str
    name: str
    reference_type: MarketReferenceType
    region: str
    role: BenchmarkRole
    reference_version: str
    active: bool = True

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.name.strip() or not self.region.strip():
            raise ValueError("market reference code, name and region are required")
        if not self.reference_version.strip():
            raise ValueError("reference_version is required")


@dataclass(frozen=True, slots=True)
class Sector:
    id: UUID
    workspace_id: UUID
    code: str
    name: str
    classification_system: str
    classification_version: str
    active: bool = True

    def __post_init__(self) -> None:
        values = (
            self.code,
            self.name,
            self.classification_system,
            self.classification_version,
        )
        if any(not item.strip() for item in values):
            raise ValueError("sector reference fields must not be blank")


@dataclass(frozen=True, slots=True)
class UnderlyingSectorAssignment:
    underlying_id: UUID
    sector_id: UUID
    valid_from: date
    valid_to: date | None
    source: str
    source_reference: str | None
    quality_status: str

    def __post_init__(self) -> None:
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to must not precede valid_from")
        if not self.source.strip() or not self.quality_status.strip():
            raise ValueError("assignment source and quality status are required")


@dataclass(frozen=True, slots=True)
class UnderlyingBenchmarkAssignment:
    underlying_id: UUID
    market_reference_id: UUID
    role: BenchmarkRole
    valid_from: date
    valid_to: date | None
    source: str
    source_reference: str | None
    quality_status: str

    def __post_init__(self) -> None:
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to must not precede valid_from")
        if not self.source.strip() or not self.quality_status.strip():
            raise ValueError("assignment source and quality status are required")


@dataclass(frozen=True, slots=True)
class MarketReferenceListingAssignment:
    market_reference_id: UUID
    listing_id: UUID
    valid_from: date
    valid_to: date | None
    source: str
    source_reference: str | None
    quality_status: str

    def __post_init__(self) -> None:
        if self.valid_to is not None and self.valid_to < self.valid_from:
            raise ValueError("valid_to must not precede valid_from")
        if not self.source.strip() or not self.quality_status.strip():
            raise ValueError("assignment source and quality status are required")
