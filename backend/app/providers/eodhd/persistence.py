"""SQLAlchemy-backed read ports required by the EODHD adapter."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.database import DatabaseManager
from app.features.market.persistence.models import ListingModel
from app.features.market_data.domain.models import ProviderInstrumentMapping
from app.features.market_data.persistence.mapping import mapping_to_domain
from app.features.market_data.persistence.models import ProviderInstrumentMappingModel


class SqlAlchemyMappingReader:
    """Resolve provider mappings through short-lived read-only sessions."""

    def __init__(self, database: DatabaseManager) -> None:
        self._database = database

    async def get_mapping(
        self, workspace_id: UUID, mapping_id: UUID
    ) -> ProviderInstrumentMapping | None:
        """Return one workspace-scoped mapping as an immutable domain value."""
        async with self._database.session_context() as session:
            model = await session.scalar(
                select(ProviderInstrumentMappingModel).where(
                    ProviderInstrumentMappingModel.workspace_id == workspace_id,
                    ProviderInstrumentMappingModel.id == mapping_id,
                )
            )
        return mapping_to_domain(model) if model is not None else None


class SqlAlchemyListingCurrencyReader:
    """Resolve listing currencies without exposing FT-001 persistence models."""

    def __init__(self, database: DatabaseManager) -> None:
        self._database = database

    async def get_currency(self, workspace_id: UUID, listing_id: UUID) -> str | None:
        """Return the ISO currency code of one workspace-scoped listing."""
        async with self._database.session_context() as session:
            return await session.scalar(
                select(ListingModel.currency_code).where(
                    ListingModel.workspace_id == workspace_id,
                    ListingModel.id == listing_id,
                )
            )
