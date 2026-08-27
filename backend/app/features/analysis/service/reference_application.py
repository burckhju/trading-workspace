"""FT-006 analysis orchestration for semantic market references.

D01-D reuses the released FT-006 calculator and lifecycle. Only the market-data
identity used to locate persisted prices changes; no synthetic FT-001 Underlying
or Listing is created for a MarketReference.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.analysis.domain.enums import AnalysisStatus
from app.features.analysis.domain.errors import AnalysisDataUnavailable
from app.features.analysis.domain.models import AnalysisParameters, SnapshotRow
from app.features.analysis.persistence.models import (
    MarketAnalysisEventModel,
    MarketAnalysisModel,
    MarketAnalysisRunModel,
)
from app.features.analysis.service.application import MarketAnalysisService
from app.features.market.persistence.top_down_models import MarketReferenceModel
from app.features.market_data.persistence.models import DailyPriceModel
from app.features.market_data.service.instrument_identity import MarketDataInstrumentIdentityService


class MarketReferenceAnalysisService(MarketAnalysisService):
    """Create and run analyses whose semantic owner is a MarketReference."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self._identity = MarketDataInstrumentIdentityService(session)

    async def create_for_market_reference(
        self,
        *,
        workspace_id: UUID,
        market_reference_id: UUID,
        actor: str,
    ) -> MarketAnalysisModel:
        reference = await self._active_reference(workspace_id, market_reference_id)
        if reference is None:
            raise AnalysisDataUnavailable("active market reference was not found")

        instrument = await self._identity.for_market_reference(
            workspace_id=workspace_id,
            market_reference_id=market_reference_id,
        )
        now = datetime.now(UTC)
        model = MarketAnalysisModel(
            id=uuid4(),
            workspace_id=workspace_id,
            market_data_instrument_id=instrument.id,
            underlying_id=None,
            listing_id=None,
            created_at=now,
            created_by=actor,
        )
        await self._repo.add_analysis(model)
        await self._session.flush()
        await self._repo.add_event(
            MarketAnalysisEventModel(
                id=uuid4(),
                analysis_id=model.id,
                run_id=None,
                version=None,
                event_type="CREATED",
                from_status=None,
                to_status=AnalysisStatus.DRAFT.value,
                source_version=None,
                replacement_version=None,
                reason=None,
                correlation_id=None,
                occurred_at=now,
            )
        )
        await self._session.commit()
        return model

    async def run_market_reference(
        self,
        *,
        workspace_id: UUID,
        analysis_id: UUID,
        start_date: date,
        end_date: date,
        parameters: AnalysisParameters,
        correlation_id: str | None,
    ) -> MarketAnalysisRunModel:
        analysis = await self._require_analysis(workspace_id, analysis_id)
        instrument_id = analysis.market_data_instrument_id
        if instrument_id is None or analysis.listing_id is not None:
            raise AnalysisDataUnavailable("analysis is not market-reference owned")

        instrument = await self._identity.get(
            workspace_id=workspace_id,
            instrument_id=instrument_id,
        )
        if instrument.kind != "MARKET_REFERENCE" or instrument.market_reference_id is None:
            raise AnalysisDataUnavailable("analysis is not market-reference owned")
        if await self._active_reference(workspace_id, instrument.market_reference_id) is None:
            raise AnalysisDataUnavailable("active market reference was not found")

        prices = tuple(
            (
                await self._session.scalars(
                    select(DailyPriceModel)
                    .where(
                        DailyPriceModel.workspace_id == workspace_id,
                        DailyPriceModel.market_data_instrument_id == instrument_id,
                        DailyPriceModel.listing_id.is_(None),
                        DailyPriceModel.trading_date.between(start_date, end_date),
                    )
                    .order_by(DailyPriceModel.trading_date)
                )
            ).all()
        )
        if not prices:
            raise AnalysisDataUnavailable("no persisted market data in requested range")

        rows = tuple(
            SnapshotRow(
                price.trading_date,
                price.open,
                price.high,
                price.low,
                price.close,
                price.adjusted_close,
                price.volume,
                price.currency,
                price.provider.value,
                price.provider_symbol,
                price.quality_status.value,
                tuple(filter(None, price.warnings.split("\n"))),
            )
            for price in prices
        )
        return await self._execute_snapshot(
            analysis_id=analysis_id,
            parameters=parameters,
            rows=rows,
            correlation_id=correlation_id,
            source_version=None,
        )

    async def _active_reference(
        self,
        workspace_id: UUID,
        market_reference_id: UUID,
    ) -> MarketReferenceModel | None:
        return await self._session.scalar(
            select(MarketReferenceModel).where(
                MarketReferenceModel.id == market_reference_id,
                MarketReferenceModel.workspace_id == workspace_id,
                MarketReferenceModel.active.is_(True),
            )
        )
