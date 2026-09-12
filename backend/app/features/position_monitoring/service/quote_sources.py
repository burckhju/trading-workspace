"""Provider-neutral fallback resolution for held-product quote monitoring."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from app.features.market_data.domain.enums import QualityStatus
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.service.contracts import WarrantListingQuoteProvider
from app.features.market_data.service.errors import (
    MarketDataConfigurationError,
    MarketDataNotFoundError,
)
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
    reference_price: Decimal | None = None
    reference_price_type: str | None = None
    currency: str | None = None


@dataclass(frozen=True, slots=True)
class MultiSourceWarrantQuoteResolution:
    """Selected usable quote plus the complete ordered source-attempt trace."""

    result: MarketDataResult[WarrantQuoteSnapshot | None] | None
    selected_source: str | None
    attempts: tuple[QuoteSourceAttempt, ...]
    rejected_result: MarketDataResult[WarrantQuoteSnapshot | None] | None = None
    rejected_source: str | None = None


class MultiSourceWarrantQuoteResolver:
    """Prefer a current bid; retain older bids and typed reference prices for analysis."""

    def __init__(self, sources: tuple[NamedWarrantQuoteSource, ...]) -> None:
        self._sources = sources

    async def resolve(self, request: WarrantQuoteRequest) -> MultiSourceWarrantQuoteResolution:
        attempts: list[QuoteSourceAttempt] = []
        best: MarketDataResult[WarrantQuoteSnapshot | None] | None = None
        best_source = None
        best_priority = 99
        rejected = None
        rejected_source = None
        for source in self._sources:
            # A runtime placeholder without an adapter is configuration metadata,
            # not a provider attempt. Keep diagnostics limited to calls that ran.
            if source.provider is None:
                continue

            try:
                result = await source.provider.get_warrant_listing_quote(request)
            except MarketDataNotFoundError:
                # The listing is not configured/mapped for this provider. This is
                # routing metadata, not a failed provider quote attempt.
                continue
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
                        status=(
                            QuoteSourceAttemptStatus.INSUFFICIENT
                            if result.quality_status is not QualityStatus.VALID
                            else QuoteSourceAttemptStatus.MISSING
                        ),
                        reason=result.reason_code or "NO_QUOTE_RETURNED",
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
            if result.quality_status is not QualityStatus.VALID or (
                quote.bid is None and quote.reference_price is None
            ):
                attempts.append(
                    QuoteSourceAttempt(
                        source=source.name,
                        status=QuoteSourceAttemptStatus.INSUFFICIENT,
                        reason=(
                            result.reason_code
                            or (
                                f"QUALITY_{result.quality_status.value}"
                                if result.quality_status is not QualityStatus.VALID
                                else "BID_MISSING"
                            )
                        ),
                        delayed=source.delayed,
                        warrant_listing_id=request.warrant_listing_id,
                        observed_at=quote.observed_at,
                        bid_available=quote.bid is not None,
                        ask_available=quote.ask is not None,
                    )
                )
                continue

            assessed_at = quote.assessed_at or result.retrieved_at
            invalid_reason = None
            if (
                quote.observed_at is not None and quote.observed_at > result.retrieved_at
            ) or assessed_at < result.retrieved_at:
                invalid_reason = "WARRANT_QUOTE_TIME_INCONSISTENT"
            if request.expected_currency and quote.currency != request.expected_currency:
                invalid_reason = "WARRANT_QUOTE_CURRENCY_MISMATCH"
            if invalid_reason:
                if rejected is None:
                    rejected, rejected_source = result, source.name
                attempts.append(
                    QuoteSourceAttempt(
                        source=source.name,
                        status=QuoteSourceAttemptStatus.ERROR,
                        reason=invalid_reason,
                        delayed=source.delayed,
                        warrant_listing_id=request.warrant_listing_id,
                        observed_at=quote.observed_at,
                    )
                )
                continue

            attempts.append(
                QuoteSourceAttempt(
                    source=source.name,
                    status=QuoteSourceAttemptStatus.AVAILABLE,
                    reason=(
                        result.reason_code or "VALID_BID_AVAILABLE"
                        if quote.bid is not None
                        else "REFERENCE_PRICE_AVAILABLE_FOR_ANALYSIS"
                    ),
                    delayed=source.delayed,
                    warrant_listing_id=request.warrant_listing_id,
                    observed_at=quote.observed_at,
                    bid_available=quote.bid is not None,
                    ask_available=quote.ask is not None,
                    reference_price=quote.reference_price,
                    reference_price_type=quote.reference_price_type,
                    currency=quote.currency,
                )
            )
            priority = quote_priority(quote, assessed_at, request.max_quote_age_seconds)
            if priority < best_priority:
                best, best_source, best_priority = result, source.name, priority
            if priority == 0:
                break

        return MultiSourceWarrantQuoteResolution(
            result=best,
            selected_source=best_source,
            attempts=tuple(attempts),
            rejected_result=rejected,
            rejected_source=rejected_source,
        )


def quote_priority(
    quote: WarrantQuoteSnapshot, assessed_at: datetime, max_age_seconds: int = 3600
) -> int:
    """Selection priority is not a verdict about the user's analysis decision."""
    if quote.bid is not None:
        if quote.max_quote_age_seconds is not None:
            max_age_seconds = min(max_age_seconds, quote.max_quote_age_seconds)
        if (
            quote.observed_at is not None
            and (assessed_at - quote.observed_at).total_seconds() <= max_age_seconds
        ):
            return 0
        return 1
    return 2 if quote.observed_at is not None else 3
