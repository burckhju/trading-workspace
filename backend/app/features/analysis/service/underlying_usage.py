"""Usage adapter exposing immutable market analyses to FT-001 underlying guards."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.analysis.persistence.models import MarketAnalysisModel
from app.features.market.service.types import UsageReference


class MarketAnalysisUnderlyingUsageRepository:
    """Report market-analysis ownership as a blocking underlying usage."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_underlying(
        self, workspace_id: UUID, underlying_id: UUID
    ) -> Sequence[UsageReference]:
        result = await self._session.scalars(
            select(MarketAnalysisModel.id).where(
                MarketAnalysisModel.workspace_id == workspace_id,
                MarketAnalysisModel.underlying_id == underlying_id,
            )
        )
        return tuple(
            UsageReference(reference_type="MARKET_ANALYSIS", object_id=analysis_id)
            for analysis_id in result.all()
        )
