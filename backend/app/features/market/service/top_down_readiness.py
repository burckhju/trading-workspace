"""MarketReference readiness on the provider-neutral market-data identity chain."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select

from app.features.analysis.domain.enums import AnalysisStatus
from app.features.analysis.persistence.models import MarketAnalysisModel, MarketAnalysisRunModel
from app.features.market.persistence.top_down_models import MarketReferenceListingAssignmentModel
from app.features.market.service.top_down_administration import (
    TopDownReferenceAdministrationService,
    TopDownReferenceReadiness,
)
from app.features.market_data.domain.enums import MappingStatus, MarketDataProvider
from app.features.market_data.persistence.instruments import MarketDataInstrumentModel
from app.features.market_data.persistence.models import DailyPriceModel, ProviderInstrumentMappingModel


class MarketDataTopDownReferenceAdministrationService(TopDownReferenceAdministrationService):
    """Use MarketReference -> MarketDataInstrument as the readiness owner chain."""

    async def reference_readiness(
        self, workspace_id: UUID
    ) -> tuple[TopDownReferenceReadiness, ...]:
        references = await self.list_market_references(workspace_id)
        results: list[TopDownReferenceReadiness] = []
        today = datetime.now(UTC).date()

        for reference in references:
            blockers: list[str] = []
            if not reference.active:
                blockers.append("MARKET_REFERENCE_INACTIVE")

            assignment = await self._session.scalar(
                select(MarketReferenceListingAssignmentModel)
                .where(
                    MarketReferenceListingAssignmentModel.workspace_id == workspace_id,
                    MarketReferenceListingAssignmentModel.market_reference_id == reference.id,
                    MarketReferenceListingAssignmentModel.valid_from <= today,
                    or_(
                        MarketReferenceListingAssignmentModel.valid_to.is_(None),
                        MarketReferenceListingAssignmentModel.valid_to >= today,
                    ),
                )
                .order_by(MarketReferenceListingAssignmentModel.valid_from.desc())
            )
            listing_id = assignment.listing_id if assignment is not None else None

            instrument = await self._session.scalar(
                select(MarketDataInstrumentModel).where(
                    MarketDataInstrumentModel.workspace_id == workspace_id,
                    MarketDataInstrumentModel.market_reference_id == reference.id,
                    MarketDataInstrumentModel.kind == "MARKET_REFERENCE",
                )
            )
            instrument_id = instrument.id if instrument is not None else None
            if instrument_id is None:
                blockers.append("NO_MARKET_DATA_INSTRUMENT")

            mapping = None
            if instrument_id is not None:
                mapping = await self._session.scalar(
                    select(ProviderInstrumentMappingModel).where(
                        ProviderInstrumentMappingModel.workspace_id == workspace_id,
                        ProviderInstrumentMappingModel.market_data_instrument_id == instrument_id,
                        ProviderInstrumentMappingModel.listing_id.is_(None),
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
            if instrument_id is not None:
                price_count, latest_price_date = (
                    await self._session.execute(
                        select(
                            func.count(DailyPriceModel.id),
                            func.max(DailyPriceModel.trading_date),
                        ).where(
                            DailyPriceModel.workspace_id == workspace_id,
                            DailyPriceModel.market_data_instrument_id == instrument_id,
                            DailyPriceModel.listing_id.is_(None),
                        )
                    )
                ).one()
                price_count = int(price_count or 0)
            if price_count < 61:
                blockers.append("INSUFFICIENT_DAILY_PRICE_HISTORY")

            analysis_id = None
            analysis_version = None
            if instrument_id is not None:
                row = (
                    await self._session.execute(
                        select(MarketAnalysisModel.id, MarketAnalysisRunModel.version)
                        .join(
                            MarketAnalysisRunModel,
                            MarketAnalysisRunModel.analysis_id == MarketAnalysisModel.id,
                        )
                        .where(
                            MarketAnalysisModel.workspace_id == workspace_id,
                            MarketAnalysisModel.market_data_instrument_id == instrument_id,
                            MarketAnalysisModel.listing_id.is_(None),
                            MarketAnalysisRunModel.status == AnalysisStatus.COMPLETED.value,
                        )
                        .order_by(
                            MarketAnalysisRunModel.analysis_time.desc(),
                            MarketAnalysisRunModel.version.desc(),
                        )
                        .limit(1)
                    )
                ).first()
                if row is not None:
                    analysis_id, analysis_version = row
            if analysis_id is None:
                blockers.append("NO_COMPLETED_MARKET_ANALYSIS")

            results.append(
                TopDownReferenceReadiness(
                    reference_id=reference.id,
                    reference_code=reference.code,
                    reference_type=reference.reference_type,
                    listing_id=listing_id,
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
        return tuple(results)
