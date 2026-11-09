"""Versioned security identities; provider symbols remain live provider evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ChartWatchlistDefinition(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z0-9_]+$")
    kind: Literal["INDEX", "ETF"]
    name: str = Field(min_length=1, max_length=200)
    group: str = Field(min_length=1, max_length=100)
    isin: str | None = Field(default=None, pattern=r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
    mic: str | None = Field(default=None, pattern=r"^[A-Z0-9]{4}$")
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    ticker: str | None = Field(default=None, min_length=1, max_length=32)
    source_url: str = Field(max_length=1000)
    exchange_name: str | None = Field(default=None, min_length=1, max_length=200)
    country_code: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    timezone: str | None = Field(default=None, max_length=64)
    venue_source_url: str | None = Field(default=None, max_length=1000)
    return_basis: Literal["PRICE_INDEX"] | None = None
    basis_source_url: str | None = Field(default=None, max_length=1000)
    reviewed_on: date
    sources: tuple[dict[str, str], ...] = ()

    @field_validator("source_url", "venue_source_url", "basis_source_url")
    @classmethod
    def https_source(cls, value: str | None) -> str | None:
        if value is not None:
            parsed = urlparse(value)
            if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
                raise ValueError("An HTTPS source reference without credentials is required")
        return value

    @model_validator(mode="after")
    def identity_shape(self) -> ChartWatchlistDefinition:
        if self.kind == "ETF" and not all(
            (
                self.isin,
                self.mic,
                self.currency,
                self.ticker,
                self.exchange_name,
                self.country_code,
                self.timezone,
                self.venue_source_url,
            )
        ):
            raise ValueError("ETF entries require complete, sourced listing identities")
        if self.kind == "INDEX" and (
            self.code != "SP500" or any((self.isin, self.mic, self.currency, self.ticker))
        ):
            raise ValueError("Only the direct SP500 reference is supported without listing fields")
        if self.return_basis is not None and (
            self.kind != "INDEX"
            or self.basis_source_url != "https://fred.stlouisfed.org/series/SP500"
        ):
            raise ValueError("Only the reviewed SP500 price-index evidence may be confirmed")
        if (self.return_basis is None) != (self.basis_source_url is None):
            raise ValueError("Return-basis evidence requires both basis and source")
        return self


class _EtfUniverse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    schema_version: Literal[1]
    catalog_version: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    items: tuple[ChartWatchlistDefinition, ...] = Field(min_length=30, max_length=30)


@dataclass(frozen=True, slots=True)
class ChartWatchlistCatalog:
    catalog_version: str
    name: str
    items: tuple[ChartWatchlistDefinition, ...]

    def __post_init__(self) -> None:
        if not 1 <= len(self.items) <= 100:
            raise ValueError("Chart watchlists require one to 100 bounded members")
        if len({item.code for item in self.items}) != len(self.items):
            raise ValueError("Duplicate watchlist code")
        identities = [item.isin for item in self.items if item.kind == "ETF"]
        if len(set(identities)) != len(identities):
            raise ValueError("Duplicate ETF security identity")

    @property
    def checksum(self) -> str:
        payload: dict[str, Any] = {
            "catalog_version": self.catalog_version,
            "name": self.name,
            "items": [item.model_dump(mode="json") for item in self.items],
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


def bundled_chart_watchlist_catalog() -> ChartWatchlistCatalog:
    path = Path(__file__).with_name("etf_chart_universe_v1.json")
    universe = _EtfUniverse.model_validate_json(path.read_text(encoding="utf-8"))
    if any(item.kind != "ETF" for item in universe.items):
        raise ValueError("The ETF universe must contain exactly 30 ETF identities")
    index = ChartWatchlistDefinition(
        code="SP500",
        kind="INDEX",
        name="S&P 500",
        group="Marktindex",
        source_url="https://fred.stlouisfed.org/series/SP500",
        return_basis="PRICE_INDEX",
        basis_source_url="https://fred.stlouisfed.org/series/SP500",
        sources=(
            {
                "role": "index_identity",
                "url": "https://www.spglobal.com/spdji/en/indices/equity/sp-500/",
            },
            {
                "role": "index_return_basis",
                "url": "https://fred.stlouisfed.org/series/SP500",
            },
        ),
        reviewed_on=date(2026, 11, 9),
    )
    return ChartWatchlistCatalog(
        universe.catalog_version, "S&P 500 und 30 ETFs", (index, *universe.items)
    )
