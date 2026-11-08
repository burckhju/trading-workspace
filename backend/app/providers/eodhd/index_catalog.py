"""Exact index identities from EODHD's documented INDX symbol catalog.

The catalog supplies provider identity and currency, never a return basis or a
replacement instrument. Missing or conflicting metadata is not filled locally.
"""

from __future__ import annotations

import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError, field_validator

EODHD_INDEX_EXCHANGE = "INDX"
EODHD_INDEX_CATALOG_PATH = "/exchange-symbol-list/INDX"


class EodhdIndexCatalogEntry(BaseModel):
    """Provider fields required to qualify a direct index mapping."""

    model_config = ConfigDict(extra="ignore", frozen=True, strict=True)

    code: str = Field(alias="Code", min_length=1, max_length=100)
    exchange: str = Field(alias="Exchange", min_length=1, max_length=32)
    currency: str | None = Field(default=None, alias="Currency")
    instrument_type: str = Field(alias="Type", min_length=1, max_length=100)

    @field_validator("code", "exchange", "instrument_type")
    @classmethod
    def require_nonblank_metadata(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("index catalog identity fields must not be blank")
        return value


_INDEX_ROWS = TypeAdapter(Annotated[list[EodhdIndexCatalogEntry], Field(max_length=100_000)])


def exact_index_catalog_match(payload: object, *, symbol: str) -> EodhdIndexCatalogEntry | None:
    """Return one exact identity; never pick a favorable row from ambiguous data."""
    try:
        rows = _INDEX_ROWS.validate_python(payload, strict=True)
    except ValidationError as exc:
        raise ValueError("EODHD INDX catalog response has an invalid structure") from exc
    matches = [
        row
        for row in rows
        if row.code.upper() == symbol.upper() and row.exchange.upper() == EODHD_INDEX_EXCHANGE
    ]
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError("EODHD INDX catalog returned an ambiguous symbol and exchange match")
    match = matches[0]
    if match.instrument_type.strip().casefold() != "index":
        raise ValueError("EODHD INDX catalog entry has a conflicting instrument type")
    currency = (match.currency or "").strip().upper()
    if currency and re.fullmatch(r"[A-Z]{3}", currency) is None:
        raise ValueError("EODHD INDX catalog entry has an invalid currency")
    return match
