"""Cross-feature usage adapter for FT-001 underlying delete guards."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.analysis.persistence.models import MarketAnalysisModel
from app.features.candidate.persistence.models import CandidateModel
from app.features.market.service.types import UsageReference
from app.features.product.persistence.models import WarrantModel


class ReleasedUnderlyingUsageRepository:
    """Report released direct FK consumers that block physical underlying deletion."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_underlying(
        self, workspace_id: UUID, underlying_id: UUID
    ) -> Sequence[UsageReference]:
        references: list[UsageReference] = []
        for reference_type, model in (
            ("MARKET_ANALYSIS", MarketAnalysisModel),
            ("WARRANT", WarrantModel),
            ("CANDIDATE", CandidateModel),
        ):
            result = await self._session.scalars(
                select(model.id).where(
                    model.workspace_id == workspace_id,
                    model.underlying_id == underlying_id,
                )
            )
            references.extend(
                UsageReference(reference_type=reference_type, object_id=object_id)
                for object_id in result.all()
            )
        return tuple(references)
