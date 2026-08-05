"""Canonical normalization and formal identifier validation for FT-001."""

from __future__ import annotations

import re

from app.features.market.domain.errors import InvalidIsin, InvalidWkn

_ISIN_PATTERN = re.compile(r"^[A-Z0-9]{12}$")
_WKN_PATTERN = re.compile(r"^[A-Z0-9]{6}$")


def normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def normalize_name(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Name must not be blank")
    return normalized


def normalize_isin(value: str | None) -> str | None:
    normalized = normalize_optional(value)
    if normalized is None:
        return None
    normalized = normalized.replace(" ", "").replace("-", "").upper()
    if not _ISIN_PATTERN.fullmatch(normalized) or not _has_valid_isin_checksum(normalized):
        raise InvalidIsin("ISIN must be a valid ISO-6166 identifier", field="isin")
    return normalized


def normalize_wkn(value: str | None) -> str | None:
    normalized = normalize_optional(value)
    if normalized is None:
        return None
    normalized = normalized.replace(" ", "").upper()
    if not _WKN_PATTERN.fullmatch(normalized):
        raise InvalidWkn("WKN must contain exactly six alphanumeric characters", field="wkn")
    return normalized


def normalize_ticker(value: str) -> str:
    normalized = value.strip().upper()
    if not normalized:
        raise ValueError("Ticker must not be blank")
    return normalized


def normalize_code(value: str) -> str:
    normalized = value.strip().upper()
    if not normalized:
        raise ValueError("Code must not be blank")
    return normalized


def _has_valid_isin_checksum(isin: str) -> bool:
    expanded = "".join(str(ord(char) - 55) if char.isalpha() else char for char in isin)
    total = 0
    for index, char in enumerate(reversed(expanded)):
        digit = int(char)
        if index % 2 == 1:
            digit *= 2
        total += digit // 10 + digit % 10
    return total % 10 == 0
