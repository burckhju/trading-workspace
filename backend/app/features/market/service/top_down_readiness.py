"""Readiness evaluation for semantic market references using neutral market-data identity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.analysis.domain.enums import AnalysisStatus
from app.features.analysis.persistence.models import MarketAnalysisModel, MarketAnalysisRunModel
from app.features.market.persistence.top_down_models import MarketReferenceModel
from app.features.market.service.top_down_administration import TopDownReferenceAdministrationService
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.persistence.instruments import MarketDataInstrumentModel
from app.features.market_data.persistence.models import DailyPriceModel, ProviderInstrumentMappingModel


@dataclass(frozen=True, slots=True)
class TopDownReferenceInstrumentReadiness:
    reference_id: UUID
    reference_code: str
    reference_type: str
    market_data_instrument_id: UUID | None
    listing_id: UUID | None
    provider_mapping_id: UUID | None
    provider_mapping_active: bool
    daily_price_count: int
    latest_price_date: date | None
    completed_analysis_id: UUID | None
    completed_analysis_version: int | None
    ready: bool
    blockers: tuple[str, ...]


class TopDownReferenceReadinessService:
    """Evaluate readiness without requiring an FT-001 stock Listing for an index."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def evaluate(
        self, workspace_id: UUID
    ) -> tuple[TopDownReferenceInstrumentReadiness, ...]:
        references = tuple(
            (
                await self._session.scalars(
                    select(MarketReferenceModel)
                    .where(MarketReferenceModel.workspace_id == workspace_id)
                    .order_by(MarketReferenceModel.region, MarketReferenceModel.code)
                )
            ).all()
        )
        values: list[TopDownReferenceInstrumentReadiness] = []
        for reference in references:
            blockers: list[str] = []
            instrument = await self._session.scalar(
                select(MarketDataInstrumentModel).where(
                    MarketDataInstrumentModel.workspace_id == workspace_id,
                    MarketDataInstrumentModel.kind == "MARKET_REFERENCE",
                    MarketDataInstrumentModel.market_reference_id == reference.id,
                    MarketDataInstrumentModel.active.is_(True),
                )
            )
            if instrument is None:
                blockers.append("NO_ACTIVE_MARKET_DATA_INSTRUMENT")

            mapping = None
            if instrument is not None:
                mapping = await self._session.scalar(
                    select(ProviderInstrumentMappingModel).where(
                        ProviderInstrumentMappingModel.workspace_id == workspace_id,
                        ProviderInstrumentMappingModel.market_data_instrument_id == instrument.id,
                        ProviderInstrumentMappingModel.provider == MarketDataProvider.EODHD,
                    )
                )
            mapping_active = mapping is not None and mapping.status is MappingStatus.ACTIVE
            if mapping is None:
                blockers.append("NO_EODHD_PROVIDER_MAPPING")
            elif not mapping_active:
                blockers.append("EODHD_PROVIDER_MAPPING_NOT_ACTIVE")

            price_count = 0
            latest_price_date = None
            if instrument is not None:
                row = (
                    await self._session.execute(
                        select(func.count(DailyPriceModel.id), func.max(DailyPriceModel.trading_date)).where(
                            DailyPriceModel.workspace_id == workspace_id,
                            DailyPriceModel.market_data_instrument_id == instrument.id,
                        )
                    )
                ).one()
                price_count = int(row[0] or 0)
                latest_price_date = row[1]
            if price_count < 61:
                blockers.append("INSUFFICIENT_DAILY_PRICE_HISTORY")

            analysis_id = None
            analysis_version = None
            if instrument is not None:
                analysis_row = (
                    await self._session.execute(
                        select(MarketAnalysisModel.id, MarketAnalysisRunModel.version)
                        .join(
                            MarketAnalysisRunModel,
                            MarketAnalysisRunModel.analysis_id == MarketAnalysisModel.id,
                        )
                        .where(
                            MarketAnalysisModel.workspace_id == workspace_id,
                            MarketAnalysisModel.market_data_instrument_id == instrument.id,
                            MarketAnalysisRunModel.status.in_(
                                (
                                    AnalysisStatus.COMPLETED.value,
                                    AnalysisStatus.COMPLETED_WITH_WARNINGS.value,
                                )
                            ),
                        )
                        .order_by(
                            MarketAnalysisRunModel.analysis_time.desc(),
                            MarketAnalysisRunModel.version.desc(),
                        )
                        .limit(1)
                    )
                ).first()
                if analysis_row is not None:
                    analysis_id, analysis_version = analysis_row
            if analysis_id is None:
                blockers.append("NO_COMPLETED_MARKET_ANALYSIS")

            values.append(
                TopDownReferenceInstrumentReadiness(
                    reference_id=reference.id,
                    reference_code=reference.code,
                    reference_type=reference.reference_type,
                    market_data_instrument_id=instrument.id if instrument is not None else None,
                    listing_id=None,
                    provider_mapping_id=mapping.id if mapping is not None else None,
                    provider_mapping_active=mapping_active,
                    daily_price_count=price_count,
                    latest_price_date=latest_price_date,
                    completed_analysis_id=analysis_id,
                    completed_analysis_version=analysis_version,
                    ready=not blockers,
                    blockers=tuple(blockers),
                )
            )
        return tuple(values)


class InstrumentAwareTopDownReferenceAdministrationService(TopDownReferenceAdministrationService):
    """Keep all released admin commands while replacing only the readiness read model."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self._instrument_readiness = TopDownReferenceReadinessService(session)

    async def reference_readiness(
        self, workspace_id: UUID
    ) -> tuple[TopDownReferenceInstrumentReadiness, ...]:
        return await self._instrument_readiness.evaluate(workspace_id)
