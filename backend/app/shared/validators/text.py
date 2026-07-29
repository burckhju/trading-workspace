"""Reusable validation for required text values."""


def normalize_non_empty_text(value: str, *, field_name: str = "value") -> str:
    """Trim required text and reject empty or whitespace-only values."""

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized
