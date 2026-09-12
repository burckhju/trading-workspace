"""Offline, versioned monetary-currency catalogs. Validation is not source authentication."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    field_validator,
    model_validator,
)

SOURCE_URL = (
    "https://www.six-group.com/dam/download/financial-information/data-center/"
    "iso-currrency/lists/list-one.xml"
)
MAX_CATALOG_BYTES = 256_000
Code = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
Digest = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class CatalogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: Code
    name: str = Field(min_length=1, max_length=100)
    numeric_code: str = Field(pattern=r"^[0-9]{3}$")
    minor_unit: Annotated[StrictInt, Field(ge=0, le=6)]
    kind: Literal["CURRENCY"]

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        if value != value.strip() or any(ord(c) < 32 for c in value):
            raise ValueError("Currency names must not contain control or surrounding whitespace")
        return value

    @field_validator("code")
    @classmethod
    def monetary_only(cls, value: str) -> str:
        # Non-monetary ISO special codes and fund/accounting units are not quote currencies.
        if value in {
            "XAU",
            "XAG",
            "XPT",
            "XPD",
            "XTS",
            "XXX",
            "XBA",
            "XBB",
            "XBC",
            "XBD",
            "XDR",
            "XSU",
            "XUA",
            "XAD",
            "BOV",
            "CHE",
            "CHW",
            "CLF",
            "COU",
            "MXV",
            "USN",
            "UYI",
            "UYW",
        }:
            raise ValueError("Fund, metal, testing and accounting units are outside this catalog")
        return value


class CurrencyCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1]
    version: str = Field(min_length=1, max_length=50, pattern=r"^[A-Za-z0-9._-]+$")
    source_url: str

    @field_validator("source_url")
    @classmethod
    def official_source(cls, value: str) -> str:
        if value != SOURCE_URL:
            raise ValueError("Use the official SIX List One source reference")
        return value

    source_sha256: Digest
    source_published_on: date
    scope: str = Field(min_length=10, max_length=300)
    entries: tuple[CatalogEntry, ...] = Field(min_length=1, max_length=250)

    @model_validator(mode="after")
    def validate_catalog(self) -> CurrencyCatalog:
        if self.source_published_on > datetime.now(UTC).date():
            raise ValueError("Future-dated reference catalogs cannot be activated")
        if len({entry.code for entry in self.entries}) != len(self.entries):
            raise ValueError("Duplicate currency code")
        if len({entry.numeric_code for entry in self.entries}) != len(self.entries):
            raise ValueError("Duplicate numeric currency code")
        return self

    def document(self) -> dict[str, Any]:
        value = self.model_dump(mode="json")
        value["entries"] = sorted(value["entries"], key=lambda row: row["code"])
        return value

    @property
    def checksum(self) -> str:
        return fingerprint(self.document())


def fingerprint(value: object) -> str:
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError(f"Non-finite JSON constant is not allowed: {value}")


def parse_catalog(raw: str) -> CurrencyCatalog:
    if len(raw.encode("utf-8")) > MAX_CATALOG_BYTES:
        raise ValueError("Catalog exceeds 256000 bytes")
    value = json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    return CurrencyCatalog.model_validate(value)


def bundled_catalog() -> CurrencyCatalog:
    path = Path(__file__).with_name("data") / "currencies-v1.json"
    return parse_catalog(path.read_text(encoding="utf-8"))
