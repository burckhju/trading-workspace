"""Public, pure identifier-validation contract for consumers of market reference data."""

import re

from app.features.market.domain.errors import InvalidIsin
from app.features.market.domain.normalization import normalize_isin


def is_canonical_isin(value: str | None) -> bool:
    """Require ISO shape and the existing authoritative checksum, without repairing data."""
    if value is None or re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", value) is None:
        return False
    try:
        return normalize_isin(value) == value
    except InvalidIsin:
        return False
