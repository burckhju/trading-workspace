"""Explicit currency provenance owned by the exact immutable execution."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

CurrencyResolutionSource = Literal[
    "USER_CONFIRMED",
    "PRIOR_BUYS",
    "REPLACED_EXECUTION",
    "EXECUTION_DOCUMENT",
    "HISTORICAL_LISTING",
    "HISTORICAL_LISTINGS",
    "UNKNOWN",
    "MIXED",
    "CONFLICT",
]
RESOLVER_VERSION = "execution-currency-v3"


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


@dataclass(frozen=True, slots=True)
class CurrencyEvidenceReference:
    """The immutable reviewed source revision actually considered by the resolver."""

    id: UUID
    kind: Literal["EXECUTION_DOCUMENT", "HISTORICAL_LISTINGS"]
    source_reference: str
    recorded_at: datetime
    valid_from: datetime | None
    valid_to: datetime | None
    source_fingerprint: str
    verification: Literal["USER_VERIFIED_SOURCE"] = "USER_VERIFIED_SOURCE"


@dataclass(frozen=True, slots=True)
class ExecutionCurrencyResolution:
    """Read-only derivation; never an invented confirmation of an execution."""

    currency_code: str | None = None
    source: CurrencyResolutionSource = "UNKNOWN"
    source_execution_ids: tuple[UUID, ...] = ()
    confirmation_ids: tuple[UUID, ...] = ()
    evidence_ids: tuple[UUID, ...] = ()
    evidence: tuple[CurrencyEvidenceReference, ...] = ()
    reason: str | None = None
    resolver_version: str = RESOLVER_VERSION

    @property
    def provenance_links(self) -> int:
        return len(self.source_execution_ids) + len(self.confirmation_ids) + len(self.evidence_ids)
