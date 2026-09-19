"""Read model for controlled position quote-source backfill."""

from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market_data.persistence.models import PositionQuoteSourceSelectionModel
from app.features.product.persistence.models import WarrantListingModel, WarrantModel
from app.features.product_selection.persistence.models import ProductEvaluationModel
from app.features.trade_position.persistence.models import PositionModel, TradeModel


async def open_position_rows(session: AsyncSession, workspace_id: UUID):
    return (
        await session.execute(
            select(
                PositionModel,
                TradeModel,
                WarrantModel,
                ProductEvaluationModel,
                WarrantListingModel,
                PositionQuoteSourceSelectionModel,
            )
            .join(TradeModel, TradeModel.id == PositionModel.trade_id)
            .join(WarrantModel, WarrantModel.id == PositionModel.product_id)
            .outerjoin(
                ProductEvaluationModel,
                ProductEvaluationModel.id == TradeModel.product_evaluation_id,
            )
            .outerjoin(
                WarrantListingModel,
                WarrantListingModel.id == ProductEvaluationModel.warrant_listing_id,
            )
            .outerjoin(
                PositionQuoteSourceSelectionModel,
                and_(
                    PositionQuoteSourceSelectionModel.workspace_id == workspace_id,
                    PositionQuoteSourceSelectionModel.position_id == PositionModel.id,
                    PositionQuoteSourceSelectionModel.superseded_at.is_(None),
                ),
            )
            .where(
                TradeModel.workspace_id == workspace_id,
                TradeModel.cancelled_at.is_(None),
                TradeModel.product_id == PositionModel.product_id,
                PositionModel.open_quantity > 0,
                PositionModel.closed_at.is_(None),
            )
            .order_by(WarrantModel.isin, PositionModel.id)
        )
    ).all()
