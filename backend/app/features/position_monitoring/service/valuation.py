from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import select

from app.database import DatabaseManager
from app.features.market_data.domain.enums import MarketDataCapability, QualityStatus
from app.features.market_data.service.contracts import WarrantListingQuoteProvider
from app.features.market_data.service.types import WarrantQuoteRequest
from app.features.product.persistence.models import WarrantListingModel
from app.features.product_selection.persistence.models import ProductEvaluationModel
from app.features.trade_position.persistence.models import PositionModel, TradeModel


class PositionValuationStatus(StrEnum):
    OK = "OK"
    MISSING = "MISSING"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class PositionValuation:
    trade_id: UUID
    position_id: UUID
    status: PositionValuationStatus
    reason: str
    warrant_listing_id: UUID | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    currency: str | None = None
    observed_at: datetime | None = None
    mark_price: Decimal | None = None
    mark_price_type: str | None = None
    market_value: Decimal | None = None
    unrealized_gross_pnl: Decimal | None = None


class PositionValuationService:
    """Value an open LONG position from the exact selected WarrantListing quote."""

    def __init__(
        self,
        *,
        database: DatabaseManager,
        market_data: WarrantListingQuoteProvider | None,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._database = database
        self._market_data = market_data
        self._now = now

    async def for_trade(self, trade_id: UUID) -> PositionValuation | None:
        async with self._database.session_context() as session:
            row = (
                await session.execute(
                    select(PositionModel, TradeModel)
                    .join(TradeModel, TradeModel.id == PositionModel.trade_id)
                    .where(
                        TradeModel.id == trade_id,
                        PositionModel.open_quantity > 0,
                        PositionModel.closed_at.is_(None),
                    )
                )
            ).first()
            if row is None:
                return None
            position, trade = row

            if trade.product_evaluation_id is None:
                return PositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    status=PositionValuationStatus.UNAVAILABLE,
                    reason="NO_HISTORICAL_WARRANT_LISTING_PROVENANCE",
                )

            evaluation = await session.scalar(
                select(ProductEvaluationModel).where(
                    ProductEvaluationModel.id == trade.product_evaluation_id,
                    ProductEvaluationModel.warrant_id == trade.product_id,
                )
            )
            if evaluation is None:
                return PositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    status=PositionValuationStatus.ERROR,
                    reason="PRODUCT_EVALUATION_PROVENANCE_INVALID",
                )

            listing = await session.scalar(
                select(WarrantListingModel).where(
                    WarrantListingModel.id == evaluation.warrant_listing_id,
                    WarrantListingModel.warrant_id == trade.product_id,
                )
            )
            if listing is None:
                return PositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    status=PositionValuationStatus.ERROR,
                    reason="WARRANT_LISTING_PROVENANCE_INVALID",
                    warrant_listing_id=evaluation.warrant_listing_id,
                )

            if self._market_data is None:
                return PositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    status=PositionValuationStatus.ERROR,
                    reason="WARRANT_QUOTE_PROVIDER_UNAVAILABLE",
                    warrant_listing_id=listing.id,
                )

            try:
                result = await self._market_data.get_warrant_listing_quote(
                    WarrantQuoteRequest(
                        workspace_id=trade.workspace_id,
                        warrant_listing_id=listing.id,
                        correlation_id=uuid4(),
                        as_of=self._now(),
                    )
                )
            except Exception:
                return PositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    status=PositionValuationStatus.ERROR,
                    reason="WARRANT_QUOTE_REQUEST_FAILED",
                    warrant_listing_id=listing.id,
                )

            if result.capability is not MarketDataCapability.WARRANT_LISTING_QUOTE:
                return PositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    status=PositionValuationStatus.ERROR,
                    reason="WARRANT_QUOTE_CAPABILITY_MISMATCH",
                    warrant_listing_id=listing.id,
                )

            quote = result.data
            if quote is None:
                return PositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    status=PositionValuationStatus.MISSING,
                    reason="NO_WARRANT_LISTING_QUOTE",
                    warrant_listing_id=listing.id,
                )
            if quote.warrant_listing_id != listing.id:
                return PositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    status=PositionValuationStatus.ERROR,
                    reason="WARRANT_QUOTE_LISTING_MISMATCH",
                    warrant_listing_id=listing.id,
                )
            if result.quality_status is not QualityStatus.VALID:
                return PositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    status=PositionValuationStatus.ERROR,
                    reason=f"WARRANT_QUOTE_QUALITY_{result.quality_status.value}",
                    warrant_listing_id=listing.id,
                    bid=quote.bid,
                    ask=quote.ask,
                    currency=quote.currency,
                    observed_at=quote.observed_at,
                )
            if quote.currency != listing.quotation_currency_code:
                return PositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    status=PositionValuationStatus.ERROR,
                    reason="WARRANT_QUOTE_CURRENCY_MISMATCH",
                    warrant_listing_id=listing.id,
                    bid=quote.bid,
                    ask=quote.ask,
                    currency=quote.currency,
                    observed_at=quote.observed_at,
                )
            if quote.bid is None:
                return PositionValuation(
                    trade_id=trade_id,
                    position_id=position.id,
                    status=PositionValuationStatus.MISSING,
                    reason="WARRANT_BID_MISSING",
                    warrant_listing_id=listing.id,
                    ask=quote.ask,
                    currency=quote.currency,
                    observed_at=quote.observed_at,
                )

            market_value = Decimal(position.open_quantity) * quote.bid
            unrealized_gross_pnl = market_value - position.cost_basis
            return PositionValuation(
                trade_id=trade_id,
                position_id=position.id,
                status=PositionValuationStatus.OK,
                reason="LONG_POSITION_MARKED_AT_BID",
                warrant_listing_id=listing.id,
                bid=quote.bid,
                ask=quote.ask,
                currency=quote.currency,
                observed_at=quote.observed_at,
                mark_price=quote.bid,
                mark_price_type="BID",
                market_value=market_value,
                unrealized_gross_pnl=unrealized_gross_pnl,
            )
