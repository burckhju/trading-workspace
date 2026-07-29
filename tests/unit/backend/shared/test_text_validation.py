import pytest

from app.shared.validators import normalize_non_empty_text


def test_normalize_non_empty_text_trims_surrounding_whitespace() -> None:
    assert normalize_non_empty_text("  Trading Workspace  ") == "Trading Workspace"


def test_normalize_non_empty_text_rejects_whitespace_only_value() -> None:
    with pytest.raises(ValueError, match="name must not be empty"):
        normalize_non_empty_text(" \t\n", field_name="name")
