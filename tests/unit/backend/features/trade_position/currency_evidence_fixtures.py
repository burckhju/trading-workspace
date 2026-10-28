"""Synthetic source records with explicit historical validity and exact identities."""

from datetime import UTC, datetime
from uuid import UUID

from app.features.trade_position.domain.currency_evidence import (
    CurrencyEvidence,
    CurrencyListingEvidence,
)
from app.features.trade_position.domain.models import Trade

RECORDED = datetime(2031, 1, 1, 12, tzinfo=UTC)
XETRA = UUID(int=7001)
FRANKFURT = UUID(int=7002)


def listing(venue: UUID = XETRA, code: str | None = "EUR") -> CurrencyListingEvidence:
    return CurrencyListingEvidence(trading_venue_id=venue, currency_code=code)


def historical(
    trade: Trade,
    number: int = 8001,
    *,
    codes: tuple[CurrencyListingEvidence, ...] | None = None,
    complete: bool = True,
    start: datetime | None = None,
    end: datetime | None = None,
) -> CurrencyEvidence:
    return CurrencyEvidence(
        id=UUID(int=number),
        workspace_id=trade.workspace_id,
        product_id=trade.product_id,
        kind="HISTORICAL_LISTINGS",
        source_reference="Synthetic dated exchange listing archive, source version 1",
        recorded_at=RECORDED,
        recorded_by=UUID(int=4),
        supersedes_evidence_id=None,
        request_id=UUID(int=number + 10000),
        request_fingerprint="a" * 64,
        valid_from=start or datetime(2026, 1, 1, tzinfo=UTC),
        valid_to=end or datetime(2027, 1, 1, tzinfo=UTC),
        listings=codes if codes is not None else (listing(), listing(FRANKFURT)),
        complete_listing_set=complete,
    )


def document(
    trade: Trade,
    execution_id: UUID,
    number: int = 9001,
    *,
    code: str | None = "EUR",
    venue: UUID | None = None,
) -> CurrencyEvidence:
    return CurrencyEvidence(
        id=UUID(int=number),
        workspace_id=trade.workspace_id,
        product_id=trade.product_id,
        kind="EXECUTION_DOCUMENT",
        source_reference=f"Synthetic execution statement {number}, verified source version 1",
        recorded_at=RECORDED,
        recorded_by=UUID(int=4),
        supersedes_evidence_id=None,
        request_id=UUID(int=number + 10000),
        request_fingerprint="b" * 64,
        trade_id=trade.id,
        execution_id=execution_id,
        currency_code=code,
        trading_venue_id=venue,
    )
