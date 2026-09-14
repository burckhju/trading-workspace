"""Explicit user meaning of a management price; never inferred from its size."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class PriceBasis(StrEnum):
    UNDERLYING = "UNDERLYING"
    WARRANT = "WARRANT"


@dataclass(frozen=True, slots=True)
class PriceBinding:
    basis: PriceBasis
    instrument_id: UUID
    currency: str

    def __post_init__(self) -> None:
        if (
            len(self.currency) != 3
            or not self.currency.isascii()
            or not self.currency.isalpha()
            or self.currency != self.currency.upper()
        ):
            raise ValueError("Price currency must be an uppercase three-letter code")

    @property
    def key(self) -> str:
        return f"{self.basis}:{self.instrument_id}:{self.currency}"

    def as_dict(self) -> dict[str, str]:
        return {
            "basis": self.basis.value,
            "instrument_id": str(self.instrument_id),
            "currency": self.currency,
        }

    @classmethod
    def from_dict(cls, value: dict[str, str] | None) -> "PriceBinding | None":
        return (
            None
            if value is None
            else cls(PriceBasis(value["basis"]), UUID(value["instrument_id"]), value["currency"])
        )
