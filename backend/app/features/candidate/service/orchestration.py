"""Server-side top-down candidate evaluation orchestration.

This module resolves persisted analysis runs, derives all top-down inputs from
stored immutable analysis data, and returns a provenance-complete candidate
input. Clients never supply classifications or model metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.analysis.domain.enums import (
    AnalysisQualityStatus,
    AnalysisStatus,
    CriterionClassification,
)
from app.features.analysis.domain.top_down import (
    RelativeStrengthResult,
    TradingDirection,
    calculate_market_context,
    calculate_relative_strength,
)
from app.features.analysis.persistence.models import (
    MarketAnalysisCriterionModel,
    MarketAnalysisModel,
    MarketAnalysisRunModel,
    MarketAnalysisSnapshotRowModel,
)
from app.features.analysis.persistence.repositories import SqlAlchemyAnalysisRepository
from app.features.candidate.domain.models import (
    AnalysisReference,
    CandidateEvaluationInput,
)


@dataclass(frozen=True, slots=True)
class StoredAnalysisReference:
    analysis_id: UUID
    version: int

    def __post_init__(self) -> None:
        if self.version <= 0:
            raise ValueError("analysis reference version must be positive")


@dataclass(frozen=True, slots=True)
class ResolvedCandidateEvaluation:
    value: CandidateEvaluationInput
    sources: dict[str, AnalysisReference]


@dataclass(frozen=True, slots=True)
class _ResolvedAnalysis:
    analysis: MarketAnalysisModel
    run: MarketAnalysisRunModel
    criteria: dict[str, MarketAnalysisCriterionModel]
    snapshot: tuple[MarketAnalysisSnapshotRowModel, ...]


class TopDownEvaluationOrchestrator:
    """Build Candidate Model 1.0 inputs exclusively from persisted analyses."""

    def __init__(self, session: AsyncSession) -> None:
        self._repository = SqlAlchemyAnalysisRepository(session)

    async def resolve(
        self,
        *,
        workspace_id: UUID,
        candidate_underlying_id: UUID,
        market: StoredAnalysisReference,
        sector: StoredAnalysisReference,
        underlying: StoredAnalysisReference,
        direction: TradingDirection = TradingDirection.LONG,
    ) -> ResolvedCandidateEvaluation:
        if direction is not TradingDirection.LONG:
            raise ValueError("TOP_DOWN_CANDIDATE 1.0 supports LONG evaluations only")

        market_analysis = await self._load(workspace_id, market)
        sector_analysis = await self._load(workspace_id, sector)
        underlying_analysis = await self._load(workspace_id, underlying)

        if underlying_analysis.analysis.underlying_id != candidate_underlying_id:
            raise ValueError(
                "underlying analysis does not belong to candidate underlying"
            )

        market_context = calculate_market_context(
            direction=direction,
            long_trend=self._classification(market_analysis, "LONG_TREND"),
            medium_trend=self._classification(market_analysis, "MEDIUM_TREND"),
            short_trend=self._classification(market_analysis, "SHORT_TREND"),
            quality_status=self._quality(market_analysis.run),
        )

        sector_rs = self._relative_strength(sector_analysis, market_analysis)
        underlying_rs = self._relative_strength(underlying_analysis, sector_analysis)

        momentum = self._momentum(underlying_analysis)
        volatility = self._numeric(underlying_analysis, "VOLATILITY")
        range_position = self._numeric(underlying_analysis, "RANGE_POSITION")

        value = CandidateEvaluationInput(
            direction=direction,
            market_context=market_context.classification,
            market_quality=market_context.quality_status,
            sector_trend=self._classification(sector_analysis, "LONG_TREND"),
            sector_relative_strength=sector_rs.classification,
            sector_quality=self._worst_quality(
                self._quality(sector_analysis.run), sector_rs.quality_status
            ),
            underlying_long_trend=self._classification(
                underlying_analysis, "LONG_TREND"
            ),
            underlying_medium_trend=self._classification(
                underlying_analysis, "MEDIUM_TREND"
            ),
            underlying_short_trend=self._classification(
                underlying_analysis, "SHORT_TREND"
            ),
            underlying_relative_strength=underlying_rs.classification,
            underlying_quality=self._worst_quality(
                self._quality(underlying_analysis.run), underlying_rs.quality_status
            ),
            momentum=momentum,
            volatility=volatility,
            range_position=range_position,
        )
        sources = {
            "MARKET": self._source(market_analysis),
            "SECTOR": self._source(sector_analysis),
            "UNDERLYING": self._source(underlying_analysis),
        }
        return ResolvedCandidateEvaluation(value=value, sources=sources)

    async def _load(
        self, workspace_id: UUID, reference: StoredAnalysisReference
    ) -> _ResolvedAnalysis:
        analysis = await self._repository.get_analysis(
            workspace_id, reference.analysis_id
        )
        if analysis is None:
            raise ValueError("analysis source not found in workspace")
        run = await self._repository.get_run(reference.analysis_id, reference.version)
        if run is None:
            raise ValueError("analysis source version not found")
        allowed = {
            AnalysisStatus.COMPLETED.value,
            AnalysisStatus.COMPLETED_WITH_WARNINGS.value,
        }
        if run.status not in allowed:
            raise ValueError("analysis source must be completed")
        criteria = {
            item.code: item for item in await self._repository.list_criteria(run.id)
        }
        snapshot = await self._repository.list_snapshot(run.id)
        return _ResolvedAnalysis(analysis, run, criteria, snapshot)

    @staticmethod
    def _classification(
        source: _ResolvedAnalysis, code: str
    ) -> CriterionClassification:
        criterion = source.criteria.get(code)
        if criterion is None:
            return CriterionClassification.NOT_EVALUABLE
        return CriterionClassification(criterion.classification)

    @staticmethod
    def _numeric(source: _ResolvedAnalysis, code: str) -> Decimal | None:
        criterion = source.criteria.get(code)
        return None if criterion is None else criterion.value

    @classmethod
    def _momentum(cls, source: _ResolvedAnalysis) -> CriterionClassification | None:
        candidates: list[tuple[int, MarketAnalysisCriterionModel]] = []
        for code, item in source.criteria.items():
            if not code.startswith("MOMENTUM_"):
                continue
            try:
                window = int(code.removeprefix("MOMENTUM_"))
            except ValueError:
                continue
            candidates.append((window, item))
        if not candidates:
            return None
        _, criterion = max(candidates, key=lambda item: item[0])
        return CriterionClassification(criterion.classification)

    @staticmethod
    def _price_map(source: _ResolvedAnalysis) -> dict[date, Decimal]:
        output: dict[date, Decimal] = {}
        for row in source.snapshot:
            price = row.adjusted_close if row.adjusted_close is not None else row.close
            output[row.trading_date] = price
        return output

    @classmethod
    def _relative_strength(
        cls, subject: _ResolvedAnalysis, reference: _ResolvedAnalysis
    ) -> RelativeStrengthResult:
        subject_prices = cls._price_map(subject)
        reference_prices = cls._price_map(reference)
        dates = sorted(set(subject_prices).intersection(reference_prices))
        return calculate_relative_strength(
            tuple(subject_prices[item] for item in dates),
            tuple(reference_prices[item] for item in dates),
        )

    @staticmethod
    def _quality(run: MarketAnalysisRunModel) -> AnalysisQualityStatus:
        return AnalysisQualityStatus(run.quality_status)

    @staticmethod
    def _worst_quality(
        left: AnalysisQualityStatus, right: AnalysisQualityStatus
    ) -> AnalysisQualityStatus:
        order = {
            AnalysisQualityStatus.GOOD: 0,
            AnalysisQualityStatus.LIMITED: 1,
            AnalysisQualityStatus.INSUFFICIENT: 2,
        }
        return left if order[left] >= order[right] else right

    @staticmethod
    def _source(source: _ResolvedAnalysis) -> AnalysisReference:
        return AnalysisReference(
            analysis_id=source.analysis.id,
            version=source.run.version,
            model_id=source.run.model_id,
            model_version=source.run.model_version,
        )
