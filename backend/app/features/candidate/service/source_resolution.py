"""Semantic resolution of top-down analysis sources.

The resolver follows historized reference assignments instead of trusting source
IDs supplied by a client.  It deliberately reuses the existing MarketAnalysis
persistence model: market and sector references are bridged to ordinary listings,
so provider-specific symbol handling remains in the market-data layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.features.analysis.domain.enums import AnalysisStatus
from app.features.analysis.persistence.models import (
    MarketAnalysisModel,
    MarketAnalysisRunModel,
)
from app.features.candidate.service.orchestration import StoredAnalysisReference
from app.features.market.domain.top_down import BenchmarkRole
from app.features.market.persistence.top_down_models import (
    MarketReferenceListingAssignmentModel,
    MarketReferenceModel,
    SectorReferenceAssignmentModel,
    UnderlyingBenchmarkAssignmentModel,
    UnderlyingSectorAssignmentModel,
)


@dataclass(frozen=True, slots=True)
class ResolvedTopDownSources:
    market: StoredAnalysisReference
    sector: StoredAnalysisReference
    underlying: StoredAnalysisReference
    primary_benchmark_id: UUID
    sector_id: UUID
    sector_reference_id: UUID
    as_of: datetime


class SemanticTopDownSourceResolver:
    """Resolve the approved LONG V1 source chain for one candidate underlying."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def resolve(
        self,
        *,
        workspace_id: UUID,
        underlying_id: UUID,
        as_of: datetime | None = None,
    ) -> ResolvedTopDownSources:
        cutoff = (as_of or datetime.now(UTC)).astimezone(UTC)
        valid_on = cutoff.date()

        benchmark_assignment = await self._one_valid(
            UnderlyingBenchmarkAssignmentModel,
            workspace_id=workspace_id,
            valid_on=valid_on,
            extra=(
                UnderlyingBenchmarkAssignmentModel.underlying_id == underlying_id,
                UnderlyingBenchmarkAssignmentModel.role == BenchmarkRole.BROAD_MARKET.value,
            ),
            label="BROAD_MARKET benchmark assignment",
        )
        benchmark = await self._session.scalar(
            select(MarketReferenceModel).where(
                MarketReferenceModel.id == benchmark_assignment.market_reference_id,
                MarketReferenceModel.workspace_id == workspace_id,
                MarketReferenceModel.active.is_(True),
            )
        )
        if benchmark is None:
            raise ValueError("assigned broad-market reference is missing or inactive")

        sector_assignment = await self._one_valid(
            UnderlyingSectorAssignmentModel,
            workspace_id=workspace_id,
            valid_on=valid_on,
            extra=(UnderlyingSectorAssignmentModel.underlying_id == underlying_id,),
            label="sector assignment",
        )
        sector_reference_assignment = await self._one_valid(
            SectorReferenceAssignmentModel,
            workspace_id=workspace_id,
            valid_on=valid_on,
            extra=(SectorReferenceAssignmentModel.sector_id == sector_assignment.sector_id,),
            label="sector reference assignment",
        )
        sector_reference = await self._session.scalar(
            select(MarketReferenceModel).where(
                MarketReferenceModel.id == sector_reference_assignment.market_reference_id,
                MarketReferenceModel.workspace_id == workspace_id,
                MarketReferenceModel.active.is_(True),
            )
        )
        if sector_reference is None:
            raise ValueError("assigned sector market reference is missing or inactive")

        benchmark_listing = await self._listing_for_reference(
            workspace_id, benchmark.id, valid_on, "broad-market"
        )
        sector_listing = await self._listing_for_reference(
            workspace_id, sector_reference.id, valid_on, "sector"
        )

        return ResolvedTopDownSources(
            market=await self._latest_completed_for_listing(
                workspace_id, benchmark_listing, cutoff, "broad-market"
            ),
            sector=await self._latest_completed_for_listing(
                workspace_id, sector_listing, cutoff, "sector"
            ),
            underlying=await self._latest_completed_for_underlying(
                workspace_id, underlying_id, cutoff
            ),
            primary_benchmark_id=benchmark.id,
            sector_id=sector_assignment.sector_id,
            sector_reference_id=sector_reference.id,
            as_of=cutoff,
        )

    async def _listing_for_reference(
        self, workspace_id: UUID, reference_id: UUID, valid_on: date, label: str
    ) -> UUID:
        assignment = await self._one_valid(
            MarketReferenceListingAssignmentModel,
            workspace_id=workspace_id,
            valid_on=valid_on,
            extra=(MarketReferenceListingAssignmentModel.market_reference_id == reference_id,),
            label=f"{label} listing assignment",
        )
        return UUID(str(assignment.listing_id))

    async def _one_valid(
        self,
        model: type[Any],
        *,
        workspace_id: UUID,
        valid_on: date,
        extra: tuple[ColumnElement[bool], ...],
        label: str,
    ) -> Any:
        rows = (
            await self._session.scalars(
                select(model)
                .where(
                    model.workspace_id == workspace_id,
                    model.valid_from <= valid_on,
                    or_(model.valid_to.is_(None), model.valid_to >= valid_on),
                    *extra,
                )
                .order_by(model.valid_from.desc(), model.id)
            )
        ).all()
        if not rows:
            raise ValueError(f"no valid {label} found for evaluation date")
        if len(rows) > 1:
            raise ValueError(f"multiple overlapping {label}s found for evaluation date")
        row = rows[0]
        if getattr(row, "quality_status", None) == "INSUFFICIENT":
            raise ValueError(f"{label} quality is INSUFFICIENT")
        return row

    async def _latest_completed_for_listing(
        self, workspace_id: UUID, listing_id: UUID, cutoff: datetime, label: str
    ) -> StoredAnalysisReference:
        row = await self._latest_completed(
            workspace_id=workspace_id,
            cutoff=cutoff,
            predicate=MarketAnalysisModel.listing_id == listing_id,
        )
        if row is None:
            raise ValueError(f"no completed {label} analysis available as of evaluation time")
        analysis, run = row
        return StoredAnalysisReference(analysis.id, run.version)

    async def _latest_completed_for_underlying(
        self, workspace_id: UUID, underlying_id: UUID, cutoff: datetime
    ) -> StoredAnalysisReference:
        row = await self._latest_completed(
            workspace_id=workspace_id,
            cutoff=cutoff,
            predicate=MarketAnalysisModel.underlying_id == underlying_id,
        )
        if row is None:
            raise ValueError("no completed underlying analysis available as of evaluation time")
        analysis, run = row
        return StoredAnalysisReference(analysis.id, run.version)

    async def _latest_completed(
        self,
        *,
        workspace_id: UUID,
        cutoff: datetime,
        predicate: ColumnElement[bool],
    ) -> tuple[MarketAnalysisModel, MarketAnalysisRunModel] | None:
        allowed = (
            AnalysisStatus.COMPLETED.value,
            AnalysisStatus.COMPLETED_WITH_WARNINGS.value,
        )
        result = await self._session.execute(
            select(MarketAnalysisModel, MarketAnalysisRunModel)
            .join(
                MarketAnalysisRunModel,
                MarketAnalysisRunModel.analysis_id == MarketAnalysisModel.id,
            )
            .where(
                MarketAnalysisModel.workspace_id == workspace_id,
                predicate,
                MarketAnalysisRunModel.status.in_(allowed),
                MarketAnalysisRunModel.analysis_time <= cutoff,
            )
            .order_by(
                MarketAnalysisRunModel.analysis_time.desc(),
                MarketAnalysisRunModel.version.desc(),
                MarketAnalysisModel.id,
            )
            .limit(1)
        )
        row = result.first()
        if row is None:
            return None
        return row[0], row[1]
