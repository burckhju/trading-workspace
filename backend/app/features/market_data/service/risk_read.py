"""Public bounded persisted-data reads for risk consumers. No network or writes."""

from datetime import date, datetime
from uuid import UUID, uuid4

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market_data.domain.enums import MarketDataProvider, QualityStatus
from app.features.market_data.domain.models import DailyPrice, WarrantQuoteSnapshot
from app.features.market_data.domain.risk_evidence import SavedQuoteEvidence
from app.features.market_data.persistence.mapping import daily_price_to_domain
from app.features.market_data.persistence.models import (
    DailyPriceModel,
    PositionQuoteSourceSelectionModel,
    WarrantQuoteObservationModel,
)
from app.features.market_data.persistence.quote_identity import read_quote_identity
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest


class RiskMarketDataReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_daily_prices(
        self, workspace_id: UUID, listing_id: UUID, start_date: date, end_date: date
    ) -> tuple[DailyPrice, ...]:
        rows = (
            await self._session.scalars(
                select(DailyPriceModel)
                .where(
                    DailyPriceModel.workspace_id == workspace_id,
                    DailyPriceModel.listing_id == listing_id,
                    DailyPriceModel.trading_date.between(start_date, end_date),
                )
                .order_by(DailyPriceModel.trading_date.desc())
                .limit(61)
            )
        ).all()
        return tuple(daily_price_to_domain(row) for row in reversed(rows))

    async def saved_quote(
        self, *, workspace_id: UUID, position_id: UUID, as_of: datetime
    ) -> SavedQuoteEvidence:
        selection = await self._session.scalar(
            select(PositionQuoteSourceSelectionModel).where(
                PositionQuoteSourceSelectionModel.workspace_id == workspace_id,
                PositionQuoteSourceSelectionModel.position_id == position_id,
                PositionQuoteSourceSelectionModel.superseded_at.is_(None),
            )
        )
        if (
            selection is None
            or selection.selection_status != "SELECTED"
            or selection.warrant_listing_id is None
            or selection.provider is None
        ):
            return SavedQuoteEvidence("NO_CONFIRMED_SAVED_QUOTE_SOURCE")
        try:
            provider = MarketDataProvider(selection.provider)
        except ValueError:
            return SavedQuoteEvidence("SAVED_QUOTE_PROVIDER_UNSUPPORTED")
        identity = await read_quote_identity(
            self._session,
            WarrantQuoteRequest(
                workspace_id,
                selection.warrant_listing_id,
                uuid4(),
                as_of,
            ),
            provider,
        )
        if identity is None or identity.key != selection.identity_key:
            return SavedQuoteEvidence("SAVED_QUOTE_ROUTE_IDENTITY_CHANGED")
        record = await self._session.get(
            WarrantQuoteObservationModel,
            (workspace_id, selection.warrant_listing_id, provider.value),
        )
        if record is None or record.identity_key != identity.key:
            return SavedQuoteEvidence("NO_SAVED_QUOTE_FOR_CURRENT_ROUTE")
        try:
            result = TypeAdapter(MarketDataResult[WarrantQuoteSnapshot | None]).validate_python(
                record.payload
            )
        except ValueError:
            return SavedQuoteEvidence("SAVED_QUOTE_PAYLOAD_INVALID")
        if result.quality_status is not QualityStatus.VALID or result.data is None:
            return SavedQuoteEvidence("SAVED_QUOTE_QUALITY_INVALID")
        if (
            result.provider is not provider
            or result.retrieved_at > as_of
            or (
                result.data.observed_at is not None
                and result.data.observed_at > result.retrieved_at
            )
            or result.data.provider_symbol != identity.isin
            or result.data.currency != identity.currency
            or result.data.warrant_listing_id != selection.warrant_listing_id
        ):
            return SavedQuoteEvidence("SAVED_QUOTE_IDENTITY_OR_TIME_INVALID")
        return SavedQuoteEvidence(
            "LAST_SUCCESS_IS_NOT_A_PRICE_SERIES",
            result.data,
            provider.value,
            result.retrieved_at,
            identity.key,
            history_observations=1,
        )
