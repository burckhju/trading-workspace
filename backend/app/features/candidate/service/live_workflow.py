"""Guided live-configuration readiness for one top-down candidate.

The workflow is read-only. It explains the exact missing prerequisite instead of
silently creating provider mappings, downloading data, or running analyses.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.features.analysis.domain.enums import AnalysisStatus
from app.features.analysis.persistence.models import (
    MarketAnalysisModel,
    MarketAnalysisRunModel,
)
from app.features.candidate.persistence.models import CandidateModel
from app.features.market.domain.top_down import BenchmarkRole
from app.features.market.persistence.models import ListingModel
from app.features.market.persistence.top_down_models import (
    MarketReferenceListingAssignmentModel,
    MarketReferenceModel,
    SectorModel,
    SectorReferenceAssignmentModel,
    UnderlyingBenchmarkAssignmentModel,
    UnderlyingSectorAssignmentModel,
)
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.persistence.models import (
    DailyPriceModel,
    ProviderInstrumentMappingModel,
)


@dataclass(frozen=True, slots=True)
class WorkflowStep:
    code: str
    label: str
    status: str
    detail: str
    action: str | None = None
    resource_id: UUID | None = None
    action_params: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class CandidateLiveWorkflow:
    candidate_id: UUID
    underlying_id: UUID
    as_of: datetime
    ready: bool
    can_evaluate: bool
    next_action: str | None
    steps: tuple[WorkflowStep, ...]


class CandidateLiveWorkflowService:
    """Explain whether a candidate can run the approved live top-down path."""

    MIN_DAILY_PRICES = 61

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def inspect(
        self, *, workspace_id: UUID, candidate_id: UUID, as_of: datetime | None = None
    ) -> CandidateLiveWorkflow:
        cutoff = (as_of or datetime.now(UTC)).astimezone(UTC)
        valid_on = cutoff.date()
        candidate = await self._session.scalar(
            select(CandidateModel).where(
                CandidateModel.workspace_id == workspace_id,
                CandidateModel.id == candidate_id,
            )
        )
        if candidate is None:
            raise ValueError("candidate not found")

        steps: list[WorkflowStep] = []

        benchmark_assignment = await self._one_active(
            UnderlyingBenchmarkAssignmentModel,
            workspace_id,
            valid_on,
            UnderlyingBenchmarkAssignmentModel.underlying_id == candidate.underlying_id,
            UnderlyingBenchmarkAssignmentModel.role == BenchmarkRole.BROAD_MARKET.value,
        )
        benchmark = None
        if benchmark_assignment is None:
            steps.append(
                WorkflowStep(
                    "BENCHMARK_ASSIGNMENT",
                    "Broad-market benchmark",
                    "BLOCKED",
                    "No active BROAD_MARKET benchmark assignment.",
                    "ASSIGN_BROAD_MARKET_BENCHMARK",
                    action_params={"underlying_id": str(candidate.underlying_id)},
                )
            )
        else:
            benchmark = await self._session.get(
                MarketReferenceModel, benchmark_assignment.market_reference_id
            )
            if (
                benchmark is None
                or benchmark.workspace_id != workspace_id
                or not benchmark.active
            ):
                steps.append(
                    WorkflowStep(
                        "BENCHMARK_ASSIGNMENT",
                        "Broad-market benchmark",
                        "BLOCKED",
                        "Assigned benchmark is missing or inactive.",
                        "ACTIVATE_OR_REASSIGN_BENCHMARK",
                        benchmark_assignment.market_reference_id,
                        {
                            "market_reference_id": str(
                                benchmark_assignment.market_reference_id
                            )
                        },
                    )
                )
                benchmark = None
            else:
                steps.append(
                    WorkflowStep(
                        "BENCHMARK_ASSIGNMENT",
                        "Broad-market benchmark",
                        "COMPLETE",
                        f"{benchmark.code} is assigned.",
                        resource_id=benchmark.id,
                    )
                )

        sector_assignment = await self._one_active(
            UnderlyingSectorAssignmentModel,
            workspace_id,
            valid_on,
            UnderlyingSectorAssignmentModel.underlying_id == candidate.underlying_id,
        )
        sector = None
        sector_reference = None
        if sector_assignment is None:
            steps.append(
                WorkflowStep(
                    "SECTOR_ASSIGNMENT",
                    "Sector assignment",
                    "BLOCKED",
                    "No active sector assignment.",
                    "ASSIGN_SECTOR",
                    action_params={"underlying_id": str(candidate.underlying_id)},
                )
            )
        else:
            sector = await self._session.get(SectorModel, sector_assignment.sector_id)
            if (
                sector is None
                or sector.workspace_id != workspace_id
                or not sector.active
            ):
                steps.append(
                    WorkflowStep(
                        "SECTOR_ASSIGNMENT",
                        "Sector assignment",
                        "BLOCKED",
                        "Assigned sector is missing or inactive.",
                        "ACTIVATE_OR_REASSIGN_SECTOR",
                        sector_assignment.sector_id,
                        {"sector_id": str(sector_assignment.sector_id)},
                    )
                )
                sector = None
            else:
                steps.append(
                    WorkflowStep(
                        "SECTOR_ASSIGNMENT",
                        "Sector assignment",
                        "COMPLETE",
                        f"{sector.code} is assigned.",
                        resource_id=sector.id,
                    )
                )
                sector_ref_assignment = await self._one_active(
                    SectorReferenceAssignmentModel,
                    workspace_id,
                    valid_on,
                    SectorReferenceAssignmentModel.sector_id == sector.id,
                )
                if sector_ref_assignment is None:
                    steps.append(
                        WorkflowStep(
                            "SECTOR_REFERENCE",
                            "Sector reference",
                            "BLOCKED",
                            "No active sector-reference assignment.",
                            "ASSIGN_SECTOR_REFERENCE",
                            sector.id,
                            {"sector_id": str(sector.id)},
                        )
                    )
                else:
                    sector_reference = await self._session.get(
                        MarketReferenceModel, sector_ref_assignment.market_reference_id
                    )
                    if (
                        sector_reference is None
                        or sector_reference.workspace_id != workspace_id
                        or not sector_reference.active
                    ):
                        steps.append(
                            WorkflowStep(
                                "SECTOR_REFERENCE",
                                "Sector reference",
                                "BLOCKED",
                                "Assigned sector reference is missing or inactive.",
                                "ACTIVATE_OR_REASSIGN_SECTOR_REFERENCE",
                                sector_ref_assignment.market_reference_id,
                                {
                                    "market_reference_id": str(
                                        sector_ref_assignment.market_reference_id
                                    ),
                                    "sector_id": str(sector.id),
                                },
                            )
                        )
                        sector_reference = None
                    else:
                        steps.append(
                            WorkflowStep(
                                "SECTOR_REFERENCE",
                                "Sector reference",
                                "COMPLETE",
                                f"{sector_reference.code} is assigned.",
                                resource_id=sector_reference.id,
                            )
                        )

        await self._append_reference_pipeline(
            steps, workspace_id, valid_on, cutoff, benchmark, "MARKET"
        )
        await self._append_reference_pipeline(
            steps, workspace_id, valid_on, cutoff, sector_reference, "SECTOR"
        )
        await self._append_underlying_pipeline(
            steps, workspace_id, cutoff, candidate.underlying_id
        )

        blocking = [step for step in steps if step.status == "BLOCKED"]
        next_action = next(
            (step.action for step in steps if step.status == "BLOCKED" and step.action),
            None,
        )
        ready = not blocking
        return CandidateLiveWorkflow(
            candidate.id,
            candidate.underlying_id,
            cutoff,
            ready,
            ready,
            next_action,
            tuple(steps),
        )

    async def _append_reference_pipeline(
        self,
        steps: list[WorkflowStep],
        workspace_id: UUID,
        valid_on: date,
        cutoff: datetime,
        reference: MarketReferenceModel | None,
        role: str,
    ) -> None:
        if reference is None:
            return
        prefix = role.upper()
        assignment = await self._one_active(
            MarketReferenceListingAssignmentModel,
            workspace_id,
            valid_on,
            MarketReferenceListingAssignmentModel.market_reference_id == reference.id,
        )
        if assignment is None:
            steps.append(
                WorkflowStep(
                    f"{prefix}_LISTING",
                    f"{role.title()} listing",
                    "BLOCKED",
                    f"{reference.code} has no active listing assignment.",
                    "ASSIGN_REFERENCE_LISTING",
                    reference.id,
                    {"market_reference_id": str(reference.id)},
                )
            )
            return
        steps.append(
            WorkflowStep(
                f"{prefix}_LISTING",
                f"{role.title()} listing",
                "COMPLETE",
                "Active listing assignment exists.",
                resource_id=assignment.listing_id,
            )
        )
        await self._append_listing_pipeline(
            steps, workspace_id, cutoff, assignment.listing_id, prefix
        )

    async def _append_underlying_pipeline(
        self,
        steps: list[WorkflowStep],
        workspace_id: UUID,
        cutoff: datetime,
        underlying_id: UUID,
    ) -> None:
        listing_id = await self._session.scalar(
            select(ListingModel.id)
            .where(
                ListingModel.workspace_id == workspace_id,
                ListingModel.underlying_id == underlying_id,
                ListingModel.is_primary.is_(True),
            )
            .limit(1)
        )
        if listing_id is None:
            steps.append(
                WorkflowStep(
                    "UNDERLYING_LISTING",
                    "Underlying listing",
                    "BLOCKED",
                    "Underlying has no primary listing.",
                    "CREATE_OR_SELECT_PRIMARY_LISTING",
                    underlying_id,
                    {"underlying_id": str(underlying_id)},
                )
            )
            return
        steps.append(
            WorkflowStep(
                "UNDERLYING_LISTING",
                "Underlying listing",
                "COMPLETE",
                "Primary listing exists.",
                resource_id=listing_id,
            )
        )
        await self._append_listing_pipeline(
            steps, workspace_id, cutoff, listing_id, "UNDERLYING"
        )

    async def _append_listing_pipeline(
        self,
        steps: list[WorkflowStep],
        workspace_id: UUID,
        cutoff: datetime,
        listing_id: UUID,
        prefix: str,
    ) -> None:
        listing = await self._session.get(ListingModel, listing_id)
        action_params = {"listing_id": str(listing_id)}
        if listing is not None:
            action_params["underlying_id"] = str(listing.underlying_id)

        mapping = await self._session.scalar(
            select(ProviderInstrumentMappingModel).where(
                ProviderInstrumentMappingModel.workspace_id == workspace_id,
                ProviderInstrumentMappingModel.listing_id == listing_id,
                ProviderInstrumentMappingModel.provider == MarketDataProvider.EODHD,
            )
        )
        if mapping is None:
            steps.append(
                WorkflowStep(
                    f"{prefix}_PROVIDER_MAPPING",
                    f"{prefix.title()} EODHD mapping",
                    "BLOCKED",
                    "No EODHD mapping exists.",
                    "CREATE_EODHD_MAPPING",
                    listing_id,
                    action_params,
                )
            )
            return
        if mapping.status is not MappingStatus.ACTIVE:
            steps.append(
                WorkflowStep(
                    f"{prefix}_PROVIDER_MAPPING",
                    f"{prefix.title()} EODHD mapping",
                    "BLOCKED",
                    f"EODHD mapping is {mapping.status.value}.",
                    "VALIDATE_EODHD_MAPPING",
                    mapping.id,
                    {**action_params, "mapping_id": str(mapping.id)},
                )
            )
            return
        steps.append(
            WorkflowStep(
                f"{prefix}_PROVIDER_MAPPING",
                f"{prefix.title()} EODHD mapping",
                "COMPLETE",
                f"Active mapping: {mapping.provider_symbol}.{mapping.provider_exchange_code}",
                resource_id=mapping.id,
            )
        )

        count, latest = (
            await self._session.execute(
                select(
                    func.count(DailyPriceModel.id),
                    func.max(DailyPriceModel.trading_date),
                ).where(
                    DailyPriceModel.workspace_id == workspace_id,
                    DailyPriceModel.listing_id == listing_id,
                    DailyPriceModel.trading_date <= cutoff.date(),
                )
            )
        ).one()
        count = int(count or 0)
        if count < self.MIN_DAILY_PRICES:
            steps.append(
                WorkflowStep(
                    f"{prefix}_PRICE_HISTORY",
                    f"{prefix.title()} price history",
                    "BLOCKED",
                    f"{count}/{self.MIN_DAILY_PRICES} required daily prices are available.",
                    "IMPORT_DAILY_PRICE_HISTORY",
                    listing_id,
                    {**action_params, "mapping_id": str(mapping.id)},
                )
            )
            return
        steps.append(
            WorkflowStep(
                f"{prefix}_PRICE_HISTORY",
                f"{prefix.title()} price history",
                "COMPLETE",
                f"{count} daily prices available; latest {latest}.",
                resource_id=listing_id,
            )
        )

        allowed = (
            AnalysisStatus.COMPLETED.value,
            AnalysisStatus.COMPLETED_WITH_WARNINGS.value,
        )
        analysis = (
            await self._session.execute(
                select(MarketAnalysisModel.id, MarketAnalysisRunModel.version)
                .join(
                    MarketAnalysisRunModel,
                    MarketAnalysisRunModel.analysis_id == MarketAnalysisModel.id,
                )
                .where(
                    MarketAnalysisModel.workspace_id == workspace_id,
                    MarketAnalysisModel.listing_id == listing_id,
                    MarketAnalysisRunModel.status.in_(allowed),
                    MarketAnalysisRunModel.analysis_time <= cutoff,
                )
                .order_by(
                    MarketAnalysisRunModel.analysis_time.desc(),
                    MarketAnalysisRunModel.version.desc(),
                )
                .limit(1)
            )
        ).first()
        if analysis is None:
            steps.append(
                WorkflowStep(
                    f"{prefix}_ANALYSIS",
                    f"{prefix.title()} FT-006 analysis",
                    "BLOCKED",
                    "No completed FT-006 analysis is available.",
                    "RUN_MARKET_ANALYSIS",
                    listing_id,
                    action_params,
                )
            )
            return
        steps.append(
            WorkflowStep(
                f"{prefix}_ANALYSIS",
                f"{prefix.title()} FT-006 analysis",
                "COMPLETE",
                f"Completed analysis {analysis[0]} v{analysis[1]} is available.",
                resource_id=analysis[0],
            )
        )

    async def _one_active(
        self,
        model: type[Any],
        workspace_id: UUID,
        valid_on: date,
        *predicates: ColumnElement[bool],
    ) -> Any | None:
        rows = (
            await self._session.scalars(
                select(model)
                .where(
                    model.workspace_id == workspace_id,
                    model.valid_from <= valid_on,
                    or_(model.valid_to.is_(None), model.valid_to >= valid_on),
                    *predicates,
                )
                .order_by(model.valid_from.desc(), model.id)
            )
        ).all()
        if len(rows) != 1:
            return None
        row = rows[0]
        if getattr(row, "quality_status", None) == "INSUFFICIENT":
            return None
        return row
