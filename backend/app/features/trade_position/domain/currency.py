"""Explicit currency provenance owned by the exact immutable execution."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ExecutionCurrencySource(StrEnum):
    USER_CONFIRMED = "USER_CONFIRMED"


@dataclass(frozen=True, slots=True)
class ExecutionCurrencyDeclaration:
    currency_code: str
    source: ExecutionCurrencySource
    note: str | None = None

    def __post_init__(self) -> None:
        code = self.currency_code.strip().upper()
        if len(code) != 3 or not code.isascii() or not code.isalpha():
            raise ValueError("currency_code must be a three-letter currency code")
        if self.source != ExecutionCurrencySource.USER_CONFIRMED:
            raise ValueError("execution currency requires explicit USER_CONFIRMED provenance")
        note = self.note.strip() if self.note is not None else None
        if note is not None and (not note or len(note) > 1000):
            raise ValueError("currency confirmation note must contain 1 to 1000 characters")
        object.__setattr__(self, "currency_code", code)
        object.__setattr__(self, "source", ExecutionCurrencySource(self.source))
        object.__setattr__(self, "note", note)

    def payload(self) -> dict[str, str | None]:
        return {"currency_code": self.currency_code, "source": self.source.value, "note": self.note}


@dataclass(frozen=True, slots=True)
class ExecutionCurrencyConfirmation:
    id: UUID
    workspace_id: UUID
    trade_id: UUID
    execution_id: UUID
    currency_code: str
    source: ExecutionCurrencySource
    note: str | None
    confirmed_at: datetime
    confirmed_by: UUID
    supersedes_confirmation_id: UUID | None
    request_id: UUID
    request_fingerprint: str
