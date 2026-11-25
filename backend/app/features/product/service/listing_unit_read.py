"""A server-timed, read-only diagnostic for one existing product listing."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.features.market.persistence.models import TradingVenueModel
from app.features.product.domain.listing_unit_evidence import ListingUnitRead, ListingUnitRoute
from app.features.product.persistence.models import WarrantListingModel
from app.features.product.service.listing_unit_evidence import (
    ListingUnitEvidenceReader,
    listing_unit_error,
)
from app.features.product.service.price_scale_evidence import require_warrant


class ListingUnitEvidenceReadService:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def read(
        self, *, workspace_id: UUID, warrant_id: UUID, listing_id: UUID
    ) -> ListingUnitRead:
        async with AsyncSession(self._engine, expire_on_commit=False, autoflush=False) as session:
            try:
                await session.execute(
                    text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                )
                await session.execute(text("SET LOCAL statement_timeout = '10000ms'"))
                known_at = datetime.now(UTC)
                await require_warrant(session, workspace_id=workspace_id, warrant_id=warrant_id)
                listing = await session.get(WarrantListingModel, listing_id)
                if (
                    listing is None
                    or listing.workspace_id != workspace_id
                    or listing.warrant_id != warrant_id
                ):
                    raise listing_unit_error("LISTING_UNIT_LISTING_NOT_FOUND", 404)
                venue = await session.get(TradingVenueModel, listing.trading_venue_id)
                if venue is None or not venue.mic:
                    raise listing_unit_error("LISTING_UNIT_ROUTE_UNSUPPORTED")
                # Diagnostic of this listing, not a selection for any position.
                route = ListingUnitRoute(
                    listing_id=listing.id,
                    provider="GETTEX_DELAYED",
                    venue_mic=venue.mic,
                    currency=listing.quotation_currency_code,
                )
                return await ListingUnitEvidenceReader(session).current(
                    workspace_id=workspace_id,
                    warrant_id=warrant_id,
                    route=route,
                    known_at=known_at,
                    event_at=known_at,
                )
            except (DBAPIError, ValueError) as error:
                raise listing_unit_error("LISTING_UNIT_READ_UNAVAILABLE", 503) from error
            finally:
                await session.rollback()
