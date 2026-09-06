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
from app.features.product.persistence.models import WarrantListingModel
from app.features.product_selection.persistence.models import ProductEvaluationModel
from app.features.trade_position.persistence.models import PositionModel, TradeModel


class ProductValuationStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
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
    ) -> None:
        self._database = database
        self._quote_resolver = quote_resolver
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

            resolution = await self._quote_resolver.resolve(
                WarrantQuoteRequest(
                    workspace_id=trade.workspace_id,
                    warrant_listing_id=listing.id,
                    correlation_id=uuid4(),
                    as_of=datetime.now(UTC),
                )
            )
            result = resolution.result
            if result is None:
                statuses = {attempt.status for attempt in resolution.attempts}
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
                    source_attempts=resolution.attempts,
                )

            quote = result.data
            assert quote is not None
            if quote.warrant_listing_id != listing.id:
                return ProductPositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    warrant_listing_id=listing.id,
                    symbol=listing.symbol,
                    status=ProductValuationStatus.ERROR,
                    reason="WARRANT_QUOTE_LISTING_MISMATCH",
                    selected_source=resolution.selected_source,
                    source_attempts=resolution.attempts,
                )
            if quote.currency != listing.quotation_currency_code:
                return ProductPositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    warrant_listing_id=listing.id,
                    symbol=listing.symbol,
                    status=ProductValuationStatus.ERROR,
                    reason="WARRANT_QUOTE_CURRENCY_MISMATCH",
                    bid=quote.bid,
                    ask=quote.ask,
                    currency=quote.currency,
                    quote_observed_at=quote.observed_at,
                    selected_source=resolution.selected_source,
                    source_attempts=resolution.attempts,
                )
            if result.quality_status is not QualityStatus.VALID or quote.bid is None:
                return ProductPositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    warrant_listing_id=listing.id,
                    symbol=listing.symbol,
                    status=ProductValuationStatus.ERROR,
                    reason="SELECTED_WARRANT_QUOTE_INVALID",
                    bid=quote.bid,
                    ask=quote.ask,
                    currency=quote.currency,
                    quote_observed_at=quote.observed_at,
                    selected_source=resolution.selected_source,
                    source_attempts=resolution.attempts,
                )

            market_value = quote.bid * Decimal(position.open_quantity)
            return ProductPositionValuation(
                trade_id=trade_id,
                position_id=position.id,
                warrant_listing_id=listing.id,
                symbol=listing.symbol,
                status=ProductValuationStatus.AVAILABLE,
                reason="WARRANT_BID_AVAILABLE",
                bid=quote.bid,
                ask=quote.ask,
                currency=quote.currency,
                quote_observed_at=quote.observed_at,
                market_value=market_value,
                unrealized_gross_pnl=market_value - position.cost_basis,
                selected_source=resolution.selected_source,
                source_attempts=resolution.attempts,
            )
