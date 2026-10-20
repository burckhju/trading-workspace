"""Public, read-only product identity value; no price or eligibility semantics."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class WarrantIdentity:
    warrant_id: UUID
    display_name: str
    isin: str | None
    wkn: str | None
