"""Provider-neutral fallback resolution for held-product quote monitoring."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.features.market_data.domain.enums import QualityStatus
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.service.contracts import WarrantListingQuoteProvider
from app.features.market_data.service.errors import MarketDataConfigurationError
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest


class QuoteSourceAttemptStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    MISSING = "MISSING"
    INSUFFICIENT = "INSUFFICIENT"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class NamedWarrantQuoteSource:
    """One ordered quote source behind the shared warrant quote boundary."""

    name: str
    provider: WarrantListingQuoteProvider | None
    delayed: bool = False
    unavailable_reason: str | None = None


@dataclass(frozen=True, slots=True)
class QuoteSourceAttempt:
    """Observable outcome of one source attempt without becoming trading state."""

    source: str
    status: QuoteSourceAttemptStatus
    reason: str
    delayed: bool
    warrant_listing_id: UUID | None = None
    observed_at: datetime | None = None
    bid_available: bool = False
    ask_available: bool = False


@dataclass(frozen=True, slots=True)
class MultiSourceWarrantQuoteResolution:
    """Selected usable quote plus the complete ordered source-attempt trace."""

    result: MarketDataResult[WarrantQuoteSnapshot | None] | None
    selected_source: str | None
    attempts: tuple[QuoteSourceAttempt, ...]


class MultiSourceWarrantQuoteResolver:
    """Try independent quote sources until an exact, valid BID quote is available."""

    def __init__(self, sources: tuple[NamedWarrantQuoteSource, ...]) -> None:
        self._sources = sources

    async def resolve(self, request: WarrantQuoteRequest) -> MultiSourceWarrantQuoteResolution:
        attempts: list[QuoteSourceAttempt] = []
        for source in self._sources:
            # A runtime placeholder without an adapter is configuration metadata,
            # not a provider attempt. Keep diagnostics limited to calls that ran.
            if source.provider is None:
                continue

            try:
                result = await source.provider.get_warrant_listing_quote(request)
            except MarketDataConfigurationError as exc:
                attempts.append(
                    QuoteSourceAttempt(
                        source=source.name,
                        status=QuoteSourceAttemptStatus.UNAVAILABLE,
                        reason=str(exc),
                        delayed=source.delayed,
                        warrant_listing_id=request.warrant_listing_id,
                    )
                )
                continue
            except Exception as exc:  # provider isolation is intentional at this read boundary
                attempts.append(
                    QuoteSourceAttempt(
                        source=source.name,
                        status=QuoteSourceAttemptStatus.ERROR,
                        reason=type(exc).__name__,
                        delayed=source.delayed,
                        warrant_listing_id=request.warrant_listing_id,
                    )
                )
                continue

            if result is None:
                attempts.append(
                    QuoteSourceAttempt(
                        source=source.name,
                        status=QuoteSourceAttemptStatus.MISSING,
                        reason="NO_QUOTE_RETURNED",
                        delayed=source.delayed,
                        warrant_listing_id=request.warrant_listing_id,
                    )
                )
                continue

            quote = result.data
            if quote is None:
                attempts.append(
                    QuoteSourceAttempt(
                        source=source.name,
                        status=QuoteSourceAttemptStatus.MISSING,
                        reason="NO_QUOTE_RETURNED",
                        delayed=source.delayed,
                        warrant_listing_id=request.warrant_listing_id,
                    )
                )
                continue
            if quote.warrant_listing_id != request.warrant_listing_id:
                attempts.append(
                    QuoteSourceAttempt(
                        source=source.name,
                        status=QuoteSourceAttemptStatus.ERROR,
                        reason="WARRANT_LISTING_MISMATCH",
                        delayed=source.delayed,
                        warrant_listing_id=request.warrant_listing_id,
                        observed_at=quote.observed_at,
                        bid_available=quote.bid is not None,
                        ask_available=quote.ask is not None,
                    )
                )
                continue
            if result.quality_status is not QualityStatus.VALID or quote.bid is None:
                attempts.append(
                    QuoteSourceAttempt(
                        source=source.name,
                        status=QuoteSourceAttemptStatus.INSUFFICIENT,
                        reason=(
                            f"QUALITY_{result.quality_status.value}"
                            if result.quality_status is not QualityStatus.VALID
                            else "BID_MISSING"
                        ),
                        delayed=source.delayed,
                        warrant_listing_id=request.warrant_listing_id,
                        observed_at=quote.observed_at,
                        bid_available=quote.bid is not None,
                        ask_available=quote.ask is not None,
                    )
                )
                continue

            attempts.append(
                QuoteSourceAttempt(
                    source=source.name,
                    status=QuoteSourceAttemptStatus.AVAILABLE,
                    reason="VALID_BID_AVAILABLE",
                    delayed=source.delayed,
                    warrant_listing_id=request.warrant_listing_id,
                    observed_at=quote.observed_at,
                    bid_available=True,
                    ask_available=quote.ask is not None,
                )
            )
            return MultiSourceWarrantQuoteResolution(
                result=result,
                selected_source=source.name,
                attempts=tuple(attempts),
            )

        return MultiSourceWarrantQuoteResolution(
            result=None,
            selected_source=None,
            attempts=tuple(attempts),
        )
