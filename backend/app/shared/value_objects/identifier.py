"""Immutable UUID-based identifier value object."""

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True, order=True)
class Identifier:
    """Represent a stable, non-empty UUID identifier."""

    value: UUID

    @classmethod
    def new(cls) -> "Identifier":
        """Create a new random identifier."""

        return cls(uuid4())

    @classmethod
    def parse(cls, value: str | UUID) -> "Identifier":
        """Create an identifier from its canonical UUID representation."""

        if isinstance(value, UUID):
            return cls(value)
        return cls(UUID(value))

    def __str__(self) -> str:
        """Return the canonical lower-case UUID string."""

        return str(self.value)
