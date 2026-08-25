"""FT-006 analysis orchestration for semantic market references.

This adapter deliberately reuses the released FT-006 calculator/lifecycle while changing
only the identity used to locate persisted market data. It does not create an FT-001
Underlying or Listing for an index.
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
from app.features.market_data.persistence.instruments import MarketDataInstrumentModel
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
        instrument = await self._identity.for_market_reference(
            workspace_id=workspace_id,
            market_reference_id=market_reference_id,
        )
        if not instrument.active:
            raise AnalysisDataUnavailable("market reference is not active")
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
        if instrument_id is None:
            raise AnalysisDataUnavailable("analysis has no market-data instrument identity")
        instrument = await self._session.scalar(
            select(MarketDataInstrumentModel).where(
                MarketDataInstrumentModel.workspace_id == workspace_id,
                MarketDataInstrumentModel.id == instrument_id,
                MarketDataInstrumentModel.kind == "MARKET_REFERENCE",
                MarketDataInstrumentModel.active.is_(True),
            )
        )
        if instrument is None:
            raise AnalysisDataUnavailable("market-reference instrument is unavailable")
        prices = tuple(
            (
                await self._session.scalars(
                    select(DailyPriceModel)
                    .where(
                        DailyPriceModel.workspace_id == workspace_id,
                        DailyPriceModel.market_data_instrument_id == instrument_id,
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
                p.trading_date,
                p.open,
                p.high,
                p.low,
                p.close,
                p.adjusted_close,
                p.volume,
                p.currency,
                p.provider.value,
                p.provider_symbol,
                p.quality_status.value,
                tuple(filter(None, p.warnings.split("\n"))),
            )
            for p in prices
        )
        return await self._execute_snapshot(
            analysis_id=analysis_id,
            parameters=parameters,
            rows=rows,
            correlation_id=correlation_id,
            source_version=None,
        )
