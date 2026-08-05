"""Read-only reference-data queries required by FT-001 clients."""

from collections.abc import Sequence

from app.features.market.persistence.models import CurrencyModel, TradingVenueModel
from app.features.market.service.unit_of_work import MarketUnitOfWork


class ReferenceDataService:
    def __init__(self, uow: MarketUnitOfWork) -> None:
        self._uow = uow

    async def list_active_trading_venues(self) -> Sequence[TradingVenueModel]:
        async with self._uow:
            return await self._uow.reference_data.list_active_trading_venues()

    async def list_active_currencies(self) -> Sequence[CurrencyModel]:
        async with self._uow:
            return await self._uow.reference_data.list_active_currencies()
