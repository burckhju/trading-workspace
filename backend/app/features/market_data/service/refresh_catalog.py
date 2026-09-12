"""Read active workspace instruments without inferring product identity from symbols."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select

from app.database import DatabaseManager
from app.features.market.domain.enums import LifecycleStatus
from app.features.market.persistence.models import (
    CurrencyModel,
    IssuerModel,
    ListingModel,
    TradingVenueModel,
    UnderlyingModel,
)
from app.features.product.domain.models import WarrantLifecycle
from app.features.product.persistence.models import WarrantModel


@dataclass(frozen=True, slots=True)
class RefreshInstrument:
    id: UUID
    name: str
    isin: str | None
    issuer: str | None = None
    listing_id: UUID | None = None


async def read_catalog(
    database: DatabaseManager,
    workspace_id: UUID,
) -> tuple[list[RefreshInstrument], list[RefreshInstrument]]:
    async with database.session_context() as session:
        warrants = (
            await session.execute(
                select(WarrantModel, IssuerModel)
                .join(IssuerModel, IssuerModel.id == WarrantModel.issuer_id)
                .where(
                    WarrantModel.workspace_id == workspace_id,
                    WarrantModel.lifecycle_status == WarrantLifecycle.ACTIVE,
                    IssuerModel.is_active.is_(True),
                )
                .order_by(WarrantModel.id)
            )
        ).all()
        underlyings = (
            await session.execute(
                select(UnderlyingModel, ListingModel)
                .outerjoin(
                    ListingModel,
                    (ListingModel.underlying_id == UnderlyingModel.id)
                    & (ListingModel.workspace_id == workspace_id)
                    & (ListingModel.lifecycle_status == LifecycleStatus.ACTIVE)
                    & (
                        ListingModel.trading_venue_id.in_(
                            select(TradingVenueModel.id).where(
                                TradingVenueModel.is_active.is_(True)
                            )
                        )
                    )
                    & (
                        ListingModel.currency_code.in_(
                            select(CurrencyModel.code).where(CurrencyModel.is_active.is_(True))
                        )
                    ),
                )
                .where(
                    UnderlyingModel.workspace_id == workspace_id,
                    UnderlyingModel.lifecycle_status == LifecycleStatus.ACTIVE,
                )
                .order_by(UnderlyingModel.id, ListingModel.id)
            )
        ).all()
        return (
            [
                RefreshInstrument(w.id, w.display_name, w.isin, issuer.legal_name)
                for w, issuer in warrants
            ],
            [
                RefreshInstrument(u.id, u.name, u.isin, listing_id=listing.id if listing else None)
                for u, listing in underlyings
            ],
        )
