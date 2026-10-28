"""Reviewed source facts; distinct from declarations about an execution itself.

Historical intervals are explicit half-open source claims. Recording time,
current product listings and a market quote never manufacture such an interval.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

CurrencyEvidenceKind = Literal["EXECUTION_DOCUMENT", "HISTORICAL_LISTINGS"]


def _currency(value: str | None) -> str | None:
    if value is None:
        return None
    code = value.strip().upper()
    if len(code) != 3 or not code.isascii() or not code.isalpha():
        raise ValueError("Währung muss ein dreistelliger Währungscode sein.")
    return code


@dataclass(frozen=True, slots=True)
class CurrencyListingEvidence:
    trading_venue_id: UUID
    currency_code: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "currency_code", _currency(self.currency_code))


@dataclass(frozen=True, slots=True)
class CurrencyEvidence:
    id: UUID
    workspace_id: UUID
    product_id: UUID
    kind: CurrencyEvidenceKind
    source_reference: str
    recorded_at: datetime
    recorded_by: UUID
    supersedes_evidence_id: UUID | None
    request_id: UUID
    request_fingerprint: str
    revoked: bool = False
    trade_id: UUID | None = None
    execution_id: UUID | None = None
    currency_code: str | None = None
    trading_venue_id: UUID | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    listings: tuple[CurrencyListingEvidence, ...] = ()
    complete_listing_set: bool = False
    verification: Literal["USER_VERIFIED_SOURCE"] = "USER_VERIFIED_SOURCE"

    def __post_init__(self) -> None:
        reference = self.source_reference.strip()
        if not 3 <= len(reference) <= 1000:
            raise ValueError("Quellenreferenz muss 3 bis 1000 Zeichen enthalten.")
        object.__setattr__(self, "source_reference", reference)
        object.__setattr__(self, "currency_code", _currency(self.currency_code))
        if self.verification != "USER_VERIFIED_SOURCE":
            raise ValueError("Die Quelle muss ausdrücklich geprüft sein.")
        if self.recorded_at.utcoffset() is None:
            raise ValueError("Erfassungszeit benötigt eine Zeitzone.")
        object.__setattr__(self, "recorded_at", self.recorded_at.astimezone(UTC))
        if self.supersedes_evidence_id == self.id:
            raise ValueError("Ein Nachweis darf sich nicht selbst ersetzen.")
        if self.kind == "EXECUTION_DOCUMENT":
            if self.trade_id is None or self.execution_id is None:
                raise ValueError("Ausführungsbeleg benötigt den exakten Trade und die Buchung.")
            if self.currency_code is None and self.trading_venue_id is None:
                raise ValueError("Ausführungsbeleg benötigt Währung oder belegten Handelsplatz.")
            if self.valid_from or self.valid_to or self.listings or self.complete_listing_set:
                raise ValueError("Ausführungsbeleg darf keine Notierungszeiträume behaupten.")
        elif self.kind == "HISTORICAL_LISTINGS":
            if any(
                value is not None
                for value in (
                    self.trade_id,
                    self.execution_id,
                    self.currency_code,
                    self.trading_venue_id,
                )
            ):
                raise ValueError("Historische Notierungen sind keine Ausführungsbestätigung.")
            if self.valid_from is None or self.valid_to is None:
                raise ValueError(
                    "Historische Quelle benötigt einen begrenzten Gültigkeitszeitraum."
                )
            if self.valid_from.utcoffset() is None or self.valid_to.utcoffset() is None:
                raise ValueError("Gültigkeitsgrenzen benötigen eine Zeitzone.")
            if self.valid_from >= self.valid_to:
                raise ValueError("Gültig bis muss nach Gültig ab liegen.")
            object.__setattr__(self, "valid_from", self.valid_from.astimezone(UTC))
            object.__setattr__(self, "valid_to", self.valid_to.astimezone(UTC))
            if not 1 <= len(self.listings) <= 100:
                raise ValueError("Historische Quelle benötigt 1 bis 100 Handelsplätze.")
            if len({item.trading_venue_id for item in self.listings}) != len(self.listings):
                raise ValueError("Ein Handelsplatz darf je Quelle nur einmal vorkommen.")
            object.__setattr__(
                self,
                "listings",
                tuple(sorted(self.listings, key=lambda item: item.trading_venue_id)),
            )
        else:
            raise ValueError("Unbekannte Art des Währungsnachweises.")


def evidence_fingerprint(evidence: CurrencyEvidence) -> str:
    """Canonical command facts; retries ignore server-assigned ID and recording time."""
    payload = {
        "workspace_id": str(evidence.workspace_id),
        "product_id": str(evidence.product_id),
        "kind": evidence.kind,
        "source_reference": evidence.source_reference,
        "supersedes_evidence_id": (
            str(evidence.supersedes_evidence_id) if evidence.supersedes_evidence_id else None
        ),
        "revoked": evidence.revoked,
        "trade_id": str(evidence.trade_id) if evidence.trade_id else None,
        "execution_id": str(evidence.execution_id) if evidence.execution_id else None,
        "currency_code": evidence.currency_code,
        "trading_venue_id": (str(evidence.trading_venue_id) if evidence.trading_venue_id else None),
        "valid_from": evidence.valid_from.isoformat() if evidence.valid_from else None,
        "valid_to": evidence.valid_to.isoformat() if evidence.valid_to else None,
        "listings": [
            {
                "trading_venue_id": str(item.trading_venue_id),
                "currency_code": item.currency_code,
            }
            for item in evidence.listings
        ],
        "complete_listing_set": evidence.complete_listing_set,
        "verification": evidence.verification,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


class CurrencyEvidenceLimitExceeded(ValueError):
    """Never resolve from an incomplete, silently truncated source history."""
