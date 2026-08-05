"""SQLAlchemy-independent FT-001 domain entities and invariants."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from app.features.market.domain.errors import (
    ConcurrentModification,
    MultiplePrimaryListings,
    NotOperationallyComplete,
    PrimaryListingRequired,
    UnsupportedUnderlyingType,
)
from app.features.market.domain.normalization import (
    normalize_code,
    normalize_isin,
    normalize_name,
    normalize_ticker,
    normalize_wkn,
)
from app.features.market.domain.enums import (
    DataOrigin,
    LifecycleStatus,
    QualityStatus,
    UnderlyingType,
)


@dataclass(frozen=True, slots=True)
class Listing:
    id: UUID
    workspace_id: UUID
    underlying_id: UUID
    trading_venue_id: UUID
    ticker: str
    currency_code: str
    lifecycle_status: LifecycleStatus
    is_primary: bool
    version: int
    created_at: datetime
    updated_at: datetime
    data_origin: DataOrigin = DataOrigin.MANUAL

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", normalize_ticker(self.ticker))
        object.__setattr__(self, "currency_code", normalize_code(self.currency_code))
        if self.version < 1:
            raise ValueError("Listing version must be positive")

    @property
    def is_active_primary(self) -> bool:
        return self.lifecycle_status is LifecycleStatus.ACTIVE and self.is_primary

    def with_changes(self, *, now: datetime, **changes: object) -> Listing:
        return replace(self, updated_at=now, version=self.version + 1, **changes)


@dataclass(frozen=True, slots=True)
class Underlying:
    id: UUID
    workspace_id: UUID
    type: UnderlyingType
    name: str
    isin: str | None
    wkn: str | None
    lifecycle_status: LifecycleStatus
    quality_status: QualityStatus
    version: int
    created_at: datetime
    updated_at: datetime
    data_origin: DataOrigin = DataOrigin.MANUAL

    def __post_init__(self) -> None:
        if self.type is not UnderlyingType.STOCK:
            raise UnsupportedUnderlyingType("Only stocks are supported", field="type")
        object.__setattr__(self, "name", normalize_name(self.name))
        object.__setattr__(self, "isin", normalize_isin(self.isin))
        object.__setattr__(self, "wkn", normalize_wkn(self.wkn))
        if self.version < 1:
            raise ValueError("Underlying version must be positive")

    def with_master_data(
        self,
        *,
        now: datetime,
        name: str | None = None,
        isin: str | None | object = ...,
        wkn: str | None | object = ...,
    ) -> Underlying:
        changes: dict[str, object] = {}
        if name is not None:
            changes["name"] = normalize_name(name)
        if isin is not ...:
            changes["isin"] = normalize_isin(isin if isinstance(isin, str) else None)
        if wkn is not ...:
            changes["wkn"] = normalize_wkn(wkn if isinstance(wkn, str) else None)
        if not changes or all(getattr(self, key) == value for key, value in changes.items()):
            return self
        quality = (
            QualityStatus.COMPLETE
            if self.quality_status is QualityStatus.VERIFIED
            else self.quality_status
        )
        return replace(
            self,
            **changes,
            quality_status=quality,
            updated_at=now,
            version=self.version + 1,
        )

    def deactivate(self, *, now: datetime) -> Underlying:
        if self.lifecycle_status is LifecycleStatus.INACTIVE:
            return self
        return replace(
            self,
            lifecycle_status=LifecycleStatus.INACTIVE,
            updated_at=now,
            version=self.version + 1,
        )

    def reactivate(self, *, now: datetime, listings: tuple[Listing, ...]) -> Underlying:
        ensure_operational_listing_invariant(listings)
        if self.quality_status is QualityStatus.DRAFT:
            raise NotOperationallyComplete("Draft underlying cannot be reactivated")
        if self.lifecycle_status is LifecycleStatus.ACTIVE:
            return self
        return replace(
            self,
            lifecycle_status=LifecycleStatus.ACTIVE,
            updated_at=now,
            version=self.version + 1,
        )

    def verify(self, *, now: datetime, listings: tuple[Listing, ...]) -> Underlying:
        ensure_operational_listing_invariant(listings)
        if self.quality_status is QualityStatus.DRAFT:
            raise NotOperationallyComplete("Only complete underlyings can be verified")
        if self.quality_status is QualityStatus.VERIFIED:
            return self
        return replace(
            self,
            quality_status=QualityStatus.VERIFIED,
            updated_at=now,
            version=self.version + 1,
        )


def ensure_expected_version(expected: int, actual: int) -> None:
    if expected != actual:
        raise ConcurrentModification(
            f"Expected version {expected}, but current version is {actual}", field="version"
        )


def ensure_operational_listing_invariant(listings: tuple[Listing, ...]) -> None:
    active_primary_count = sum(listing.is_active_primary for listing in listings)
    if active_primary_count == 0:
        raise PrimaryListingRequired("Exactly one active primary listing is required")
    if active_primary_count > 1:
        raise MultiplePrimaryListings("Multiple active primary listings are not allowed")


def determine_quality_status(*, name: str, listings: tuple[Listing, ...]) -> QualityStatus:
    normalize_name(name)
    try:
        ensure_operational_listing_invariant(listings)
    except PrimaryListingRequired:
        return QualityStatus.DRAFT
    return QualityStatus.COMPLETE
