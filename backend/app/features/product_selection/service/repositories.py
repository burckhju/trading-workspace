"""Read-only repository contracts for FT-008 consumer boundaries.

FT-008 owns neither TradePlan nor Warrant reference data.  These contracts expose only
what Product Selection needs and keep SQLAlchemy/provider concerns outside its domain.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.product.domain.models import Warrant, WarrantListing, WarrantTermsVersion
from app.features.product.persistence.models import (
    WarrantListingModel,
    WarrantModel,
    WarrantTermsVersionModel,
)
from app.features.trade_plan.domain.models import TradePlan, TradePlanVersion
from app.features.trade_plan.persistence.repositories import (
    SqlAlchemyTradePlanRepository,
    SqlAlchemyTradePlanVersionRepository,
)


class ProductSelectionTradePlanRepository(Protocol):
    async def get_plan(self, workspace_id: UUID, trade_plan_id: UUID) -> TradePlan | None: ...

    async def get_version(
        self, trade_plan_id: UUID, trade_plan_version_id: UUID
    ) -> TradePlanVersion | None: ...


class ProductSelectionProductRepository(Protocol):
    async def warrants_for_underlying(
        self, workspace_id: UUID, underlying_id: UUID
    ) -> tuple[Warrant, ...]: ...

    async def terms_for_warrants(
        self, warrant_ids: tuple[UUID, ...]
    ) -> tuple[WarrantTermsVersion, ...]: ...

    async def listings_for_warrants(
        self, workspace_id: UUID, warrant_ids: tuple[UUID, ...]
    ) -> tuple[WarrantListing, ...]: ...


class SqlAlchemyProductSelectionTradePlanRepository:
    """Adapter over the released FT-007 repositories; no second TradePlan model."""

    def __init__(self, session: AsyncSession) -> None:
        self._plans = SqlAlchemyTradePlanRepository(session)
        self._versions = SqlAlchemyTradePlanVersionRepository(session, self._plans)

    async def get_plan(self, workspace_id: UUID, trade_plan_id: UUID) -> TradePlan | None:
        return await self._plans.get(workspace_id, trade_plan_id)

    async def get_version(
        self, trade_plan_id: UUID, trade_plan_version_id: UUID
    ) -> TradePlanVersion | None:
        return await self._versions.get(trade_plan_id, trade_plan_version_id)


class SqlAlchemyProductSelectionProductRepository:
    """Read-only adapter over released FT-004 Warrant/Terms/Listing rows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def warrants_for_underlying(
        self, workspace_id: UUID, underlying_id: UUID
    ) -> tuple[Warrant, ...]:
        rows = (
            await self._session.scalars(
                select(WarrantModel)
                .where(
                    WarrantModel.workspace_id == workspace_id,
                    WarrantModel.underlying_id == underlying_id,
                )
                .order_by(WarrantModel.id)
            )
        ).all()
        return tuple(_warrant_from_model(row) for row in rows)

    async def terms_for_warrants(
        self, warrant_ids: tuple[UUID, ...]
    ) -> tuple[WarrantTermsVersion, ...]:
        if not warrant_ids:
            return ()
        rows = (
            await self._session.scalars(
                select(WarrantTermsVersionModel)
                .where(WarrantTermsVersionModel.warrant_id.in_(warrant_ids))
                .order_by(
                    WarrantTermsVersionModel.warrant_id,
                    WarrantTermsVersionModel.version_no,
                )
            )
        ).all()
        return tuple(_terms_from_model(row) for row in rows)

    async def listings_for_warrants(
        self, workspace_id: UUID, warrant_ids: tuple[UUID, ...]
    ) -> tuple[WarrantListing, ...]:
        if not warrant_ids:
            return ()
        rows = (
            await self._session.scalars(
                select(WarrantListingModel)
                .where(
                    WarrantListingModel.workspace_id == workspace_id,
                    WarrantListingModel.warrant_id.in_(warrant_ids),
                )
                .order_by(WarrantListingModel.warrant_id, WarrantListingModel.id)
            )
        ).all()
        return tuple(_listing_from_model(row) for row in rows)


def _warrant_from_model(model: WarrantModel) -> Warrant:
    return Warrant(
        id=model.id,
        workspace_id=model.workspace_id,
        issuer_id=model.issuer_id,
        underlying_id=model.underlying_id,
        product_family=model.product_family,
        display_name=model.display_name,
        isin=model.isin,
        wkn=model.wkn,
        lifecycle_status=model.lifecycle_status,
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _terms_from_model(model: WarrantTermsVersionModel) -> WarrantTermsVersion:
    return WarrantTermsVersion(
        id=model.id,
        warrant_id=model.warrant_id,
        version_no=model.version_no,
        effective_from=model.effective_from,
        effective_to=model.effective_to,
        option_direction=model.option_direction,
        strike=model.strike,
        maturity_date=model.maturity_date,
        ratio=model.ratio,
        created_at=model.created_at,
    )


def _listing_from_model(model: WarrantListingModel) -> WarrantListing:
    return WarrantListing(
        id=model.id,
        workspace_id=model.workspace_id,
        warrant_id=model.warrant_id,
        trading_venue_id=model.trading_venue_id,
        symbol=model.symbol,
        quotation_currency_code=model.quotation_currency_code,
        lifecycle_status=model.lifecycle_status,
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
