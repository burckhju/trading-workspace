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
from app.features.trade_position.persistence.models import PositionModel, TradeModel


@dataclass(frozen=True, slots=True)
class RefreshInstrument:
    id: UUID
    name: str
    isin: str | None
    issuer: str | None = None
    listing_id: UUID | None = None
    held: bool = False


async def read_catalog(
    database: DatabaseManager,
    workspace_id: UUID,
) -> tuple[list[RefreshInstrument], list[RefreshInstrument]]:
    # Membership avoids duplicated jobs when several open trades hold the same product.
    held_products = (
        select(PositionModel.product_id)
        .join(TradeModel, TradeModel.id == PositionModel.trade_id)
        .where(
            TradeModel.workspace_id == workspace_id,
            TradeModel.cancelled_at.is_(None),
            TradeModel.product_id == PositionModel.product_id,
            PositionModel.open_quantity > 0,
            PositionModel.closed_at.is_(None),
        )
    )
    held_warrant = WarrantModel.id.in_(held_products)
    held_underlying = UnderlyingModel.id.in_(
        select(WarrantModel.underlying_id).where(
            WarrantModel.workspace_id == workspace_id,
            WarrantModel.id.in_(held_products),
        )
    )
    async with database.session_context() as session:
        warrants = (
            await session.execute(
                select(WarrantModel, IssuerModel, held_warrant)
                .join(IssuerModel, IssuerModel.id == WarrantModel.issuer_id)
                .where(
                    WarrantModel.workspace_id == workspace_id,
                    WarrantModel.lifecycle_status == WarrantLifecycle.ACTIVE,
                    IssuerModel.is_active.is_(True),
                )
                .order_by(held_warrant.desc(), WarrantModel.id)
            )
        ).all()
        underlyings = (
            await session.execute(
                select(UnderlyingModel, ListingModel, held_underlying)
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
                .order_by(held_underlying.desc(), UnderlyingModel.id, ListingModel.id)
            )
        ).all()
        return (
            [
                RefreshInstrument(w.id, w.display_name, w.isin, issuer.legal_name, held=held)
                for w, issuer, held in warrants
            ],
            [
                RefreshInstrument(
                    u.id, u.name, u.isin, listing_id=listing.id if listing else None, held=held
                )
                for u, listing, held in underlyings
            ],
        )
