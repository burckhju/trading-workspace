from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import select

from app.database import DatabaseManager
from app.features.market_data.domain.enums import QualityStatus
from app.features.market_data.service.contracts import WarrantListingQuoteProvider
from app.features.market_data.service.types import WarrantQuoteRequest
from app.features.position_monitoring.service.quote_sources import (
    MultiSourceWarrantQuoteResolver,
    NamedWarrantQuoteSource,
    QuoteSourceAttempt,
    QuoteSourceAttemptStatus,
)
from app.features.product.domain.models import WarrantLifecycle
from app.features.product.persistence.models import WarrantListingModel
from app.features.product_selection.persistence.models import ProductEvaluationModel
from app.features.trade_position.persistence.models import PositionModel, TradeModel

DEFAULT_MAX_PRODUCT_QUOTE_AGE_SECONDS = 3600


class ProductValuationStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    STALE = "STALE"
    MISSING = "MISSING"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class ProductPositionValuation:
    trade_id: UUID
    position_id: UUID
    status: ProductValuationStatus
    reason: str
    warrant_listing_id: UUID | None = None
    symbol: str | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    currency: str | None = None
    quote_observed_at: datetime | None = None
    quote_age_seconds: int | None = None
    max_quote_age_seconds: int | None = None
    market_value: Decimal | None = None
    unrealized_gross_pnl: Decimal | None = None
    selected_source: str | None = None
    source_attempts: tuple[QuoteSourceAttempt, ...] = ()


class ProductPositionValuationService:
    """Read current held-product valuation without changing trading or alert state."""

    def __init__(
        self,
        *,
        database: DatabaseManager,
        quote_provider: WarrantListingQuoteProvider | None = None,
        quote_resolver: MultiSourceWarrantQuoteResolver | None = None,
        max_quote_age_seconds: int = DEFAULT_MAX_PRODUCT_QUOTE_AGE_SECONDS,
    ) -> None:
        if max_quote_age_seconds < 0:
            raise ValueError("max_quote_age_seconds must not be negative")
        self._database = database
        self._legacy_single_source = quote_resolver is None and quote_provider is not None
        self._quote_resolver = quote_resolver
        self._max_quote_age_seconds = max_quote_age_seconds
        if self._quote_resolver is None and quote_provider is not None:
            self._quote_resolver = MultiSourceWarrantQuoteResolver(
                (NamedWarrantQuoteSource("PRIMARY", quote_provider),)
            )

    async def for_trade(self, trade_id: UUID) -> ProductPositionValuation | None:
        async with self._database.session_context() as session:
            row = (
                await session.execute(
                    select(TradeModel, PositionModel)
                    .join(PositionModel, PositionModel.trade_id == TradeModel.id)
                    .where(
                        TradeModel.id == trade_id,
                        PositionModel.open_quantity > 0,
                        PositionModel.closed_at.is_(None),
                    )
                )
            ).one_or_none()
            if row is None:
                return None
            trade, position = row

            if trade.product_evaluation_id is None:
                return ProductPositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    status=ProductValuationStatus.UNAVAILABLE,
                    reason="WARRANT_LISTING_PROVENANCE_UNAVAILABLE",
                )

            evaluation = await session.scalar(
                select(ProductEvaluationModel).where(
                    ProductEvaluationModel.id == trade.product_evaluation_id
                )
            )
            if evaluation is None:
                return ProductPositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    status=ProductValuationStatus.ERROR,
                    reason="PRODUCT_EVALUATION_NOT_FOUND",
                )

            listing = await session.scalar(
                select(WarrantListingModel).where(
                    WarrantListingModel.id == evaluation.warrant_listing_id
                )
            )
            if listing is None:
                return ProductPositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    status=ProductValuationStatus.ERROR,
                    reason="WARRANT_LISTING_NOT_FOUND",
                    warrant_listing_id=evaluation.warrant_listing_id,
                )

            if self._quote_resolver is None:
                return ProductPositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    warrant_listing_id=listing.id,
                    symbol=listing.symbol,
                    status=ProductValuationStatus.UNAVAILABLE,
                    reason="WARRANT_QUOTE_PROVIDER_UNAVAILABLE",
                )

            candidate_listings = [listing]
            warrant_id = getattr(listing, "warrant_id", None)
            if warrant_id is not None:
                rows = await session.scalars(
                    select(WarrantListingModel)
                    .where(
                        WarrantListingModel.workspace_id == trade.workspace_id,
                        WarrantListingModel.warrant_id == warrant_id,
                        WarrantListingModel.lifecycle_status == WarrantLifecycle.ACTIVE,
                    )
                    .order_by(WarrantListingModel.symbol)
                )
                siblings = list(rows)
                candidate_listings = [listing] + [
                    candidate for candidate in siblings if candidate.id != listing.id
                ]

            all_attempts: list[QuoteSourceAttempt] = []
            selected_listing = None
            selected_result = None
            selected_source = None
            for candidate in candidate_listings:
                resolution = await self._quote_resolver.resolve(
                    WarrantQuoteRequest(
                        workspace_id=trade.workspace_id,
                        warrant_listing_id=candidate.id,
                        correlation_id=uuid4(),
                        as_of=datetime.now(UTC),
                    )
                )
                all_attempts.extend(resolution.attempts)
                if resolution.result is not None:
                    selected_listing = candidate
                    selected_result = resolution.result
                    selected_source = resolution.selected_source
                    break

            attempts = tuple(all_attempts)
            if selected_result is None or selected_listing is None:
                if self._legacy_single_source and len(candidate_listings) == 1 and len(attempts) == 1:
                    attempt = attempts[0]
                    if attempt.status is QuoteSourceAttemptStatus.MISSING:
                        status = ProductValuationStatus.MISSING
                        reason = "WARRANT_QUOTE_MISSING"
                    elif attempt.status is QuoteSourceAttemptStatus.INSUFFICIENT:
                        if attempt.reason == "BID_MISSING":
                            status = ProductValuationStatus.MISSING
                            reason = "WARRANT_BID_MISSING"
                        else:
                            status = ProductValuationStatus.ERROR
                            reason = f"WARRANT_QUOTE_{attempt.reason}"
                    elif attempt.status is QuoteSourceAttemptStatus.UNAVAILABLE:
                        status = ProductValuationStatus.UNAVAILABLE
                        reason = "WARRANT_QUOTE_CAPABILITY_NOT_CONFIGURED"
                    else:
                        status = ProductValuationStatus.ERROR
                        reason = (
                            "WARRANT_QUOTE_LISTING_MISMATCH"
                            if attempt.reason == "WARRANT_LISTING_MISMATCH"
                            else "WARRANT_QUOTE_REQUEST_FAILED"
                        )
                    return ProductPositionValuation(
                        trade_id=trade_id,
                        position_id=position.id,
                        warrant_listing_id=listing.id,
                        symbol=listing.symbol,
                        status=status,
                        reason=reason,
                        source_attempts=attempts,
                    )

                statuses = {attempt.status for attempt in attempts}
                if statuses & {
                    QuoteSourceAttemptStatus.MISSING,
                    QuoteSourceAttemptStatus.INSUFFICIENT,
                }:
                    status = ProductValuationStatus.MISSING
                elif statuses == {QuoteSourceAttemptStatus.ERROR}:
                    status = ProductValuationStatus.ERROR
                else:
                    status = ProductValuationStatus.UNAVAILABLE
                return ProductPositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    warrant_listing_id=listing.id,
                    symbol=listing.symbol,
                    status=status,
                    reason="NO_USABLE_WARRANT_QUOTE",
                    source_attempts=attempts,
                )

            quote = selected_result.data
            assert quote is not None
            if quote.warrant_listing_id != selected_listing.id:
                return ProductPositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    warrant_listing_id=selected_listing.id,
                    symbol=selected_listing.symbol,
                    status=ProductValuationStatus.ERROR,
                    reason="WARRANT_QUOTE_LISTING_MISMATCH",
                    selected_source=selected_source,
                    source_attempts=attempts,
                )
            if quote.currency != selected_listing.quotation_currency_code:
                return ProductPositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    warrant_listing_id=selected_listing.id,
                    symbol=selected_listing.symbol,
                    status=ProductValuationStatus.ERROR,
                    reason="WARRANT_QUOTE_CURRENCY_MISMATCH",
                    bid=quote.bid,
                    ask=quote.ask,
                    currency=quote.currency,
                    quote_observed_at=quote.observed_at,
                    selected_source=selected_source,
                    source_attempts=attempts,
                )
            if selected_result.quality_status is not QualityStatus.VALID or quote.bid is None:
                return ProductPositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    warrant_listing_id=selected_listing.id,
                    symbol=selected_listing.symbol,
                    status=ProductValuationStatus.ERROR,
                    reason="SELECTED_WARRANT_QUOTE_INVALID",
                    bid=quote.bid,
                    ask=quote.ask,
                    currency=quote.currency,
                    quote_observed_at=quote.observed_at,
                    selected_source=selected_source,
                    source_attempts=attempts,
                )

            quote_age_seconds = int(
                (selected_result.retrieved_at - quote.observed_at).total_seconds()
            )
            if quote_age_seconds < 0:
                return ProductPositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    warrant_listing_id=selected_listing.id,
                    symbol=selected_listing.symbol,
                    status=ProductValuationStatus.ERROR,
                    reason="WARRANT_QUOTE_TIME_INCONSISTENT",
                    bid=quote.bid,
                    ask=quote.ask,
                    currency=quote.currency,
                    quote_observed_at=quote.observed_at,
                    quote_age_seconds=quote_age_seconds,
                    max_quote_age_seconds=self._max_quote_age_seconds,
                    selected_source=selected_source,
                    source_attempts=attempts,
                )
            if quote_age_seconds > self._max_quote_age_seconds:
                return ProductPositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    warrant_listing_id=selected_listing.id,
                    symbol=selected_listing.symbol,
                    status=ProductValuationStatus.STALE,
                    reason="WARRANT_QUOTE_STALE",
                    bid=quote.bid,
                    ask=quote.ask,
                    currency=quote.currency,
                    quote_observed_at=quote.observed_at,
                    quote_age_seconds=quote_age_seconds,
                    max_quote_age_seconds=self._max_quote_age_seconds,
                    selected_source=selected_source,
                    source_attempts=attempts,
                )

            market_value = quote.bid * Decimal(position.open_quantity)
            return ProductPositionValuation(
                trade_id=trade_id,
                position_id=position.id,
                warrant_listing_id=selected_listing.id,
                symbol=selected_listing.symbol,
                status=ProductValuationStatus.AVAILABLE,
                reason=(
                    "WARRANT_BID_AVAILABLE"
                    if selected_listing.id == listing.id
                    else "WARRANT_BID_AVAILABLE_ON_ALTERNATE_LISTING"
                ),
                bid=quote.bid,
                ask=quote.ask,
                currency=quote.currency,
                quote_observed_at=quote.observed_at,
                quote_age_seconds=quote_age_seconds,
                max_quote_age_seconds=self._max_quote_age_seconds,
                market_value=market_value,
                unrealized_gross_pnl=market_value - position.cost_basis,
                selected_source=selected_source,
                source_attempts=attempts,
            )
