"""Read-only reference-data queries required by FT-001 clients."""

from collections.abc import Sequence
from uuid import UUID

from app.features.market.persistence.models import CurrencyModel, IssuerModel, TradingVenueModel
from app.features.market.service.unit_of_work import MarketUnitOfWork


class ReferenceDataService:
    def __init__(self, uow: MarketUnitOfWork) -> None:
        self._uow = uow

    async def list_active_issuers(self) -> Sequence[IssuerModel]:
        async with self._uow:
            return await self._uow.reference_data.list_active_issuers()

    async def list_issuers(self) -> Sequence[IssuerModel]:
        async with self._uow:
            return await self._uow.reference_data.list_issuers()

    async def get_issuer(self, issuer_id: UUID) -> IssuerModel | None:
        async with self._uow:
            return await self._uow.reference_data.get_issuer(issuer_id)

    async def list_active_trading_venues(self) -> Sequence[TradingVenueModel]:
        async with self._uow:
            return await self._uow.reference_data.list_active_trading_venues()

    async def list_trading_venues(self) -> Sequence[TradingVenueModel]:
        async with self._uow:
            return await self._uow.reference_data.list_trading_venues()

    async def list_active_currencies(self) -> Sequence[CurrencyModel]:
        async with self._uow:
            return await self._uow.reference_data.list_active_currencies()
