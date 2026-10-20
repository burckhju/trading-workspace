"""Public primary-listing identity for risk analysis; never creates a listing."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market.persistence.enums import LifecycleStatus
from app.features.market.persistence.models import ListingModel


@dataclass(frozen=True, slots=True)
class RiskListingReference:
    listing_id: UUID
    currency: str
    symbol: str


class RiskListingReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def read(self, *, workspace_id: UUID, underlying_id: UUID) -> RiskListingReference | None:
        rows = (
            await self._session.scalars(
                select(ListingModel).where(
                    ListingModel.workspace_id == workspace_id,
                    ListingModel.underlying_id == underlying_id,
                    ListingModel.is_primary.is_(True),
                    ListingModel.lifecycle_status == LifecycleStatus.ACTIVE,
                )
            )
        ).all()
        if len(rows) != 1:
            return None
        return RiskListingReference(rows[0].id, rows[0].currency_code, rows[0].ticker)
