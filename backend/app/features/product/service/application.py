"""FT-004 warrant reference-data application service."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from app.features.market.domain.enums import LifecycleStatus
from app.features.market.persistence.models import (
    CurrencyModel,
    IssuerModel,
    TradingVenueModel,
    UnderlyingModel,
)
from app.features.product.domain.models import OptionDirection, ProductFamily, WarrantLifecycle
from app.features.product.persistence.models import (
    WarrantListingModel,
    WarrantModel,
    WarrantTermsVersionModel,
)
from app.features.product.service.errors import (
    DuplicateWarrantIsin,
    DuplicateWarrantListing,
    DuplicateWarrantWkn,
    InactiveWarrantReference,
    WarrantConcurrentModification,
    WarrantNotFound,
    WarrantServiceError,
)


class WarrantService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, workspace_id: UUID) -> list[WarrantModel]:
        rows = await self._session.scalars(
            select(WarrantModel)
            .where(WarrantModel.workspace_id == workspace_id)
            .order_by(WarrantModel.display_name)
        )
        return list(rows)

    async def get(self, workspace_id: UUID, warrant_id: UUID) -> WarrantModel:
        model = await self._session.scalar(
            select(WarrantModel).where(
                WarrantModel.workspace_id == workspace_id, WarrantModel.id == warrant_id
            )
        )
        if model is None:
            raise WarrantNotFound("Warrant does not exist")
        return model

    async def create(
        self,
        workspace_id: UUID,
        *,
        issuer_id: UUID,
        underlying_id: UUID,
        display_name: str,
        isin: str | None,
        wkn: str | None,
        option_direction: OptionDirection,
        strike: Decimal,
        maturity_date: date,
        ratio: Decimal,
    ) -> WarrantModel:
        normalized_name = display_name.strip()
        if not normalized_name:
            raise WarrantServiceError("display_name must not be blank", field="display_name")
        await self._require_references(workspace_id, issuer_id, underlying_id)
        normalized_isin, normalized_wkn = _up(isin), _up(wkn)
        await self._require_unique_identifiers(workspace_id, normalized_isin, normalized_wkn)
        now = datetime.now(UTC)
        model = WarrantModel(
            id=uuid4(),
            workspace_id=workspace_id,
            issuer_id=issuer_id,
            underlying_id=underlying_id,
            product_family=ProductFamily.WARRANT,
            display_name=normalized_name,
            isin=normalized_isin,
            wkn=normalized_wkn,
            lifecycle_status=WarrantLifecycle.ACTIVE,
            version=1,
            created_at=now,
            updated_at=now,
        )
        terms = WarrantTermsVersionModel(
            id=uuid4(),
            warrant_id=model.id,
            version_no=1,
            effective_from=now,
            effective_to=None,
            option_direction=option_direction,
            strike=strike,
            maturity_date=maturity_date,
            ratio=ratio,
            created_at=now,
        )
        self._validate_terms(strike, ratio)
        self._session.add_all([model, terms])
        await self._commit()
        return model

    async def change_status(
        self, workspace_id: UUID, warrant_id: UUID, expected_version: int, status: WarrantLifecycle
    ) -> WarrantModel:
        model = await self.get(workspace_id, warrant_id)
        if model.version != expected_version:
            raise WarrantConcurrentModification(
                f"Expected version {expected_version}, found {model.version}"
            )
        if model.lifecycle_status is status:
            return model
        model.lifecycle_status = status
        model.version += 1
        model.updated_at = datetime.now(UTC)
        await self._commit()
        return model

    async def current_terms(self, workspace_id: UUID, warrant_id: UUID) -> WarrantTermsVersionModel:
        await self.get(workspace_id, warrant_id)
        terms = await self._session.scalar(
            select(WarrantTermsVersionModel).where(
                WarrantTermsVersionModel.warrant_id == warrant_id,
                WarrantTermsVersionModel.effective_to.is_(None),
            )
        )
        if terms is None:
            raise WarrantServiceError("Warrant has no current terms")
        return terms

    async def terms_history(
        self, workspace_id: UUID, warrant_id: UUID
    ) -> Sequence[WarrantTermsVersionModel]:
        await self.get(workspace_id, warrant_id)
        rows = await self._session.scalars(
            select(WarrantTermsVersionModel)
            .where(WarrantTermsVersionModel.warrant_id == warrant_id)
            .order_by(WarrantTermsVersionModel.version_no)
        )
        return list(rows)

    async def add_terms_version(
        self,
        workspace_id: UUID,
        warrant_id: UUID,
        *,
        expected_version: int,
        option_direction: OptionDirection,
        strike: Decimal,
        maturity_date: date,
        ratio: Decimal,
    ) -> WarrantTermsVersionModel:
        self._validate_terms(strike, ratio)
        model = await self.get(workspace_id, warrant_id)
        if model.version != expected_version:
            raise WarrantConcurrentModification(
                f"Expected version {expected_version}, found {model.version}",
                field="expected_version",
            )
        now = datetime.now(UTC)
        current = await self.current_terms(workspace_id, warrant_id)
        current.effective_to = now
        next_no = (
            int(
                (
                    await self._session.scalar(
                        select(func.max(WarrantTermsVersionModel.version_no)).where(
                            WarrantTermsVersionModel.warrant_id == warrant_id
                        )
                    )
                )
                or 0
            )
            + 1
        )
        terms = WarrantTermsVersionModel(
            id=uuid4(),
            warrant_id=warrant_id,
            version_no=next_no,
            effective_from=now,
            effective_to=None,
            option_direction=option_direction,
            strike=strike,
            maturity_date=maturity_date,
            ratio=ratio,
            created_at=now,
        )
        model.version += 1
        model.updated_at = now
        self._session.add(terms)
        await self._commit()
        return terms

    async def add_listing(
        self,
        workspace_id: UUID,
        warrant_id: UUID,
        *,
        trading_venue_id: UUID,
        symbol: str,
        quotation_currency_code: str,
    ) -> WarrantListingModel:
        await self.get(workspace_id, warrant_id)
        normalized_symbol = symbol.strip().upper()
        if not normalized_symbol:
            raise WarrantServiceError("symbol must not be blank", field="symbol")
        normalized_currency = quotation_currency_code.strip().upper()
        venue = await self._session.get(TradingVenueModel, trading_venue_id)
        if venue is None:
            raise WarrantServiceError("Trading venue does not exist", field="trading_venue_id")
        if not venue.is_active:
            raise InactiveWarrantReference("Trading venue is inactive", field="trading_venue_id")
        currency = await self._session.get(CurrencyModel, normalized_currency)
        if currency is None:
            raise WarrantServiceError(
                "Quotation currency does not exist", field="quotation_currency_code"
            )
        if not currency.is_active:
            raise InactiveWarrantReference(
                "Quotation currency is inactive", field="quotation_currency_code"
            )
        duplicate = await self._session.scalar(
            select(WarrantListingModel.id).where(
                WarrantListingModel.workspace_id == workspace_id,
                WarrantListingModel.trading_venue_id == trading_venue_id,
                WarrantListingModel.symbol == normalized_symbol,
            )
        )
        if duplicate is not None:
            raise DuplicateWarrantListing(
                "A warrant listing with this venue and symbol already exists", field="symbol"
            )
        now = datetime.now(UTC)
        listing = WarrantListingModel(
            id=uuid4(),
            workspace_id=workspace_id,
            warrant_id=warrant_id,
            trading_venue_id=trading_venue_id,
            symbol=normalized_symbol,
            quotation_currency_code=normalized_currency,
            lifecycle_status=WarrantLifecycle.ACTIVE,
            version=1,
            created_at=now,
            updated_at=now,
        )
        self._session.add(listing)
        await self._commit()
        return listing

    async def listings(self, workspace_id: UUID, warrant_id: UUID) -> Sequence[WarrantListingModel]:
        await self.get(workspace_id, warrant_id)
        rows = await self._session.scalars(
            select(WarrantListingModel)
            .where(
                WarrantListingModel.workspace_id == workspace_id,
                WarrantListingModel.warrant_id == warrant_id,
            )
            .order_by(WarrantListingModel.symbol)
        )
        return list(rows)

    async def _require_references(
        self, workspace_id: UUID, issuer_id: UUID, underlying_id: UUID
    ) -> None:
        issuer = await self._session.get(IssuerModel, issuer_id)
        if issuer is None:
            raise WarrantServiceError("Issuer does not exist", field="issuer_id")
        if not issuer.is_active:
            raise InactiveWarrantReference("Issuer is inactive", field="issuer_id")
        underlying = await self._session.scalar(
            select(UnderlyingModel).where(
                UnderlyingModel.id == underlying_id, UnderlyingModel.workspace_id == workspace_id
            )
        )
        if underlying is None:
            raise WarrantServiceError(
                "Underlying does not exist in workspace", field="underlying_id"
            )
        if underlying.lifecycle_status != LifecycleStatus.ACTIVE:
            raise InactiveWarrantReference("Underlying is inactive", field="underlying_id")

    async def _require_unique_identifiers(
        self, workspace_id: UUID, isin: str | None, wkn: str | None
    ) -> None:
        if (
            isin is not None
            and await self._session.scalar(
                select(WarrantModel.id).where(
                    WarrantModel.workspace_id == workspace_id, WarrantModel.isin == isin
                )
            )
            is not None
        ):
            raise DuplicateWarrantIsin("A warrant with this ISIN already exists", field="isin")
        if (
            wkn is not None
            and await self._session.scalar(
                select(WarrantModel.id).where(
                    WarrantModel.workspace_id == workspace_id, WarrantModel.wkn == wkn
                )
            )
            is not None
        ):
            raise DuplicateWarrantWkn("A warrant with this WKN already exists", field="wkn")

    @staticmethod
    def _validate_terms(strike: Decimal, ratio: Decimal) -> None:
        if strike < 0:
            raise WarrantServiceError("strike must be non-negative")
        if ratio <= 0:
            raise WarrantServiceError("ratio must be greater than zero")

    async def _commit(self) -> None:
        try:
            await self._session.commit()
        except StaleDataError as error:
            await self._session.rollback()
            raise WarrantConcurrentModification(
                "Warrant was changed concurrently; reload and retry", field="expected_version"
            ) from error
        except IntegrityError as error:
            await self._session.rollback()
            message = str(error.orig)
            if "uq_warrants_workspace_isin" in message:
                raise DuplicateWarrantIsin(
                    "A warrant with this ISIN already exists", field="isin"
                ) from error
            if "uq_warrants_workspace_wkn" in message:
                raise DuplicateWarrantWkn(
                    "A warrant with this WKN already exists", field="wkn"
                ) from error
            if "uq_warrant_listings_workspace_venue_symbol" in message:
                raise DuplicateWarrantListing(
                    "A warrant listing with this venue and symbol already exists", field="symbol"
                ) from error
            if (
                "uq_warrant_terms_versions_open" in message
                or "uq_warrant_terms_versions_warrant_version" in message
            ):
                raise WarrantConcurrentModification(
                    "Warrant terms were changed concurrently; reload and retry",
                    field="expected_version",
                ) from error
            raise WarrantServiceError("Warrant data violates a persistence constraint") from error
        except Exception:
            await self._session.rollback()
            raise


def _up(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip().upper()
    return value or None
