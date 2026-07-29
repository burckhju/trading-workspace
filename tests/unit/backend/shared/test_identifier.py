from uuid import UUID

import pytest

from app.shared.value_objects import Identifier


def test_identifier_new_creates_valid_unique_values() -> None:
    first = Identifier.new()
    second = Identifier.new()

    assert isinstance(first.value, UUID)
    assert first != second


def test_identifier_parse_accepts_uuid_and_canonical_string() -> None:
    raw = UUID("f8d2959d-65c8-42d8-9064-801d48521fc6")

    assert Identifier.parse(raw) == Identifier.parse(str(raw))
    assert str(Identifier.parse(raw)) == str(raw)


def test_identifier_parse_rejects_invalid_uuid() -> None:
    with pytest.raises(ValueError):
        Identifier.parse("not-a-uuid")
