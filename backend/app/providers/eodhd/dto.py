"""Strict provider-specific DTOs for EODHD responses."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EodhdDailyPriceDto(BaseModel):
    """Validated representation of one EODHD daily-price response row."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adjusted_close: Decimal | None = Field(default=None, alias="adjusted_close")
    volume: Decimal | None = None

    @field_validator("open", "high", "low", "close", "adjusted_close", "volume", mode="before")
    @classmethod
    def reject_binary_float(cls, value: object) -> object:
        """Reject binary floats before Decimal conversion."""
        if isinstance(value, float):
            raise ValueError("binary floating-point values are not accepted")
        return value

    @field_validator("volume")
    @classmethod
    def validate_volume(cls, value: Decimal | None) -> Decimal | None:
        """Reject negative volume values."""
        if value is not None and value < 0:
            raise ValueError("volume must not be negative")
        return value


class EodhdSearchResultDto(BaseModel):
    """Validated subset of one EODHD Search API result."""

    model_config = ConfigDict(extra="ignore", frozen=True, populate_by_name=True)

    code: str = Field(alias="Code")
    exchange: str = Field(alias="Exchange")
    name: str | None = Field(default=None, alias="Name")
    type: str | None = Field(default=None, alias="Type")
    currency: str | None = Field(default=None, alias="Currency")
    isin: str | None = Field(default=None, alias="ISIN")


class EodhdUserDto(BaseModel):
    """Validated subset of the EODHD User API response."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    apiRequests: int = Field(ge=0)
    apiRequestsDate: date
    dailyRateLimit: int = Field(ge=1)
    extraLimit: int = Field(default=0, ge=0)
