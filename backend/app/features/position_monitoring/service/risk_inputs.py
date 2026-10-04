"""Compose public owner readers; all inputs come from persisted data, not providers."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.analysis.domain.product_comparison import SynchronizedPricePair
from app.features.market.service.risk_reference import RiskListingReader, RiskListingReference
from app.features.market_data.domain.models import DailyPrice
from app.features.market_data.domain.risk_evidence import SavedQuoteEvidence
from app.features.market_data.service.risk_read import RiskMarketDataReader
from app.features.product.service.risk_reference import RiskProductReader, RiskProductReference
from app.features.trade_position.service.open_position_reader import OpenPositionReference


@dataclass(frozen=True, slots=True)
class RiskInputs:
    position: OpenPositionReference
    product: RiskProductReference | None
    listing: RiskListingReference | None
    prices: tuple[DailyPrice, ...]
    quote: SavedQuoteEvidence
    synchronized_pairs: tuple[SynchronizedPricePair, ...] = ()
    comparison_limits: tuple[str, ...] = (
        "PRODUCT_HISTORY_NOT_AVAILABLE",
        "EOD_SESSION_CLOSE_INSTANT_UNVERIFIED",
    )


class RiskInputReader(Protocol):
    async def read(self, position: OpenPositionReference, as_of: datetime) -> RiskInputs: ...


class PersistedRiskInputReader:
    def __init__(self, session: AsyncSession) -> None:
        self._products = RiskProductReader(session)
        self._listings = RiskListingReader(session)
        self._market_data = RiskMarketDataReader(session)

    async def read(self, position: OpenPositionReference, as_of: datetime) -> RiskInputs:
        product = await self._products.read(
            workspace_id=position.workspace_id, warrant_id=position.warrant_id, as_of=as_of
        )
        listing = (
            await self._listings.read(
                workspace_id=position.workspace_id, underlying_id=product.underlying_id
            )
            if product
            else None
        )
        prices = (
            await self._market_data.list_daily_prices(
                position.workspace_id,
                listing.listing_id,
                as_of.date() - timedelta(days=180),
                as_of.date() - timedelta(days=1),
            )
            if listing
            else ()
        )
        quote = await self._market_data.saved_quote(
            workspace_id=position.workspace_id, position_id=position.position_id, as_of=as_of
        )
        return RiskInputs(position, product, listing, prices, quote)
