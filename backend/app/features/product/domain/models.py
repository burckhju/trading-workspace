"""SQLAlchemy-independent FT-004 warrant domain model."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID


class ProductFamily(StrEnum):
    WARRANT = "WARRANT"


class OptionDirection(StrEnum):
    CALL = "CALL"
    PUT = "PUT"


class WarrantLifecycle(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


@dataclass(frozen=True, slots=True)
class Warrant:
    id: UUID
    workspace_id: UUID
    issuer_id: UUID
    underlying_id: UUID
    display_name: str
    isin: str | None
    wkn: str | None
    lifecycle_status: WarrantLifecycle
    version: int
    created_at: datetime
    updated_at: datetime
    product_family: ProductFamily = ProductFamily.WARRANT

    def __post_init__(self) -> None:
        name = self.display_name.strip()
        if not name:
            raise ValueError("display_name must not be blank")
        object.__setattr__(self, "display_name", name)
        object.__setattr__(self, "isin", _optional_upper(self.isin))
        object.__setattr__(self, "wkn", _optional_upper(self.wkn))
        if self.version < 1:
            raise ValueError("version must be positive")

    def with_status(self, status: WarrantLifecycle, *, now: datetime) -> Warrant:
        if self.lifecycle_status is status:
            return self
        return replace(self, lifecycle_status=status, version=self.version + 1, updated_at=now)


@dataclass(frozen=True, slots=True)
class WarrantTermsVersion:
    id: UUID
    warrant_id: UUID
    version_no: int
    effective_from: datetime
    effective_to: datetime | None
    option_direction: OptionDirection
    strike: Decimal
    maturity_date: date
    ratio: Decimal
    created_at: datetime

    def __post_init__(self) -> None:
        if self.version_no < 1:
            raise ValueError("version_no must be positive")
        if self.strike < 0:
            raise ValueError("strike must be non-negative")
        if self.ratio <= 0:
            raise ValueError("ratio must be greater than zero")
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("effective_to must be after effective_from")


@dataclass(frozen=True, slots=True)
class WarrantListing:
    id: UUID
    workspace_id: UUID
    warrant_id: UUID
    trading_venue_id: UUID
    symbol: str
    quotation_currency_code: str
    lifecycle_status: WarrantLifecycle
    version: int
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        symbol = self.symbol.strip().upper()
        currency = self.quotation_currency_code.strip().upper()
        if not symbol:
            raise ValueError("symbol must not be blank")
        if len(currency) != 3:
            raise ValueError("quotation_currency_code must be a 3-letter code")
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "quotation_currency_code", currency)
        if self.version < 1:
            raise ValueError("version must be positive")


def _optional_upper(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None
