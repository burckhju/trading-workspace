"""Durable observations behind the existing warrant quote provider contract."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.manager import DatabaseManager
from app.features.market.persistence.models import TradingVenueModel
from app.features.market_data.domain.enums import (
    CacheStatus,
    MappingStatus,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.persistence.models import (
    WarrantProviderMappingModel,
    WarrantQuoteObservationModel,
)
from app.features.market_data.service.contracts import WarrantListingQuoteProvider
from app.features.market_data.service.errors import (
    MarketDataConfigurationError,
    MarketDataError,
    MarketDataInvalidResponseError,
    MarketDataMappingError,
    MarketDataNotFoundError,
)
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest
from app.features.product.domain.models import WarrantLifecycle
from app.features.product.persistence.models import WarrantListingModel, WarrantModel

QuoteResult = MarketDataResult[WarrantQuoteSnapshot | None]
_RESULT = TypeAdapter(QuoteResult)


@dataclass(frozen=True)
class QuoteIdentity:
    key: str
    isin: str
    wkn: str | None
    currency: str
    exchange: str
    mic: str


class RetainedWarrantQuoteProvider:
    """Keep successful data indefinitely; revalidate the current route on every read.

    Provider budgets/caches remain shared. Network I/O never holds a DB lock.
    Listing row locks serialize writers, including the first observation.
    """

    def __init__(
        self,
        database: DatabaseManager,
        provider: WarrantListingQuoteProvider,
        name: MarketDataProvider,
    ) -> None:
        self._database = database
        self._provider = provider
        self._name = name

    async def get_warrant_listing_quote(self, request: WarrantQuoteRequest) -> QuoteResult:
        async with self._database.session_context() as session:
            identity = await self._identity(session, request)
        if identity is None:
            raise MarketDataNotFoundError("WARRANT_ACTIVE_QUOTE_IDENTITY_NOT_FOUND")

        result = None
        error = None
        try:
            result = await self._provider.get_warrant_listing_quote(request)
        except (MarketDataConfigurationError, MarketDataMappingError, MarketDataNotFoundError):
            # A disabled/unmapped source is not an outage of a verified route.
            raise
        except Exception as exc:  # preserve bounded diagnostics, never response bodies/secrets
            error = type(exc).__name__
            if isinstance(exc, MarketDataError) and re.fullmatch(
                r"(?:FRANKFURT|VONTOBEL|STUTTGART|WARRANT)_[A-Z0-9_]{1,100}", str(exc)
            ):
                error = str(exc)

        async with self._database.session_context() as session:
            # Lock the existing parent even when no observation has been inserted yet.
            await session.scalar(
                select(WarrantListingModel.id)
                .where(
                    WarrantListingModel.id == request.warrant_listing_id,
                    WarrantListingModel.workspace_id == request.workspace_id,
                )
                .with_for_update()
            )
            if await self._identity(session, request) != identity:
                raise MarketDataMappingError("WARRANT_QUOTE_IDENTITY_CHANGED_DURING_REFRESH")
            key = (request.workspace_id, request.warrant_listing_id, self._name.value)
            row = await session.get(WarrantQuoteObservationModel, key)
            previous = (
                _RESULT.validate_python(row.payload)
                if row is not None and row.identity_key == identity.key
                else None
            )
            reason = error or self._invalid_reason(result, request, identity)
            if reason is None and result is not None:
                assert result.data is not None
                if previous is not None and previous.data is not None:
                    old_at, new_at = previous.data.observed_at, result.data.observed_at
                    if (old_at is not None and (new_at is None or new_at < old_at)) or (
                        result.retrieved_at < previous.retrieved_at
                    ):
                        reason = "WARRANT_QUOTE_OLDER_THAN_LAST_SUCCESS"
                if reason is None:
                    # Persist only provider success, never the result of a fallback.
                    payload = _RESULT.dump_python(result, mode="json")
                    if row is None:
                        session.add(
                            WarrantQuoteObservationModel(
                                workspace_id=request.workspace_id,
                                warrant_listing_id=request.warrant_listing_id,
                                provider=self._name.value,
                                identity_key=identity.key,
                                payload=payload,
                            )
                        )
                    elif row.payload != payload or row.identity_key != identity.key:
                        row.identity_key, row.payload = identity.key, payload
                    await session.commit()
                    return result
            if previous is not None and previous.data is not None:
                return replace(
                    previous,
                    correlation_id=request.correlation_id,
                    data=replace(
                        previous.data,
                        assessed_at=datetime.now(UTC),
                        refresh_error=reason,
                        retained=True,
                    ),
                    cache_status=CacheStatus.HIT,
                    provider_call_cost=result.provider_call_cost if result is not None else None,
                    retry_count=result.retry_count if result is not None else 0,
                )
        if result is not None and result.data is None:
            return result
        raise MarketDataInvalidResponseError(
            reason or "WARRANT_NO_QUOTE_RETURNED", provider=self._name
        )

    def _invalid_reason(
        self, result: QuoteResult | None, request: WarrantQuoteRequest, identity: QuoteIdentity
    ) -> str | None:
        if result is None or result.data is None:
            return "WARRANT_NO_QUOTE_RETURNED"
        quote = result.data
        if quote.refresh_error:
            return quote.refresh_error
        if (
            result.provider != self._name
            or result.quality_status != QualityStatus.VALID
            or quote.retained
            or (quote.bid is None and quote.reference_price is None)
        ):
            return "WARRANT_QUOTE_NOT_VALIDATED"
        if (
            quote.warrant_listing_id != request.warrant_listing_id
            or quote.provider_symbol != identity.isin
            or quote.provider_exchange_code != identity.exchange
            or (quote.venue_mic is not None and quote.venue_mic != identity.mic)
            or (quote.isin is not None and quote.isin != identity.isin)
            or (quote.wkn is not None and identity.wkn is not None and quote.wkn != identity.wkn)
            or quote.currency != identity.currency
            or (request.expected_currency and quote.currency != request.expected_currency)
        ):
            return "WARRANT_QUOTE_IDENTITY_MISMATCH"
        assessed_at = quote.assessed_at or result.retrieved_at
        if (
            (quote.observed_at is not None and quote.observed_at > result.retrieved_at)
            or result.retrieved_at > datetime.now(UTC)
            or assessed_at < result.retrieved_at
        ):
            return "WARRANT_QUOTE_TIME_INCONSISTENT"
        return None

    async def _identity(
        self, session: AsyncSession, request: WarrantQuoteRequest
    ) -> QuoteIdentity | None:
        row = (
            await session.execute(
                select(WarrantListingModel, WarrantModel, TradingVenueModel)
                .join(WarrantModel, WarrantModel.id == WarrantListingModel.warrant_id)
                .join(
                    TradingVenueModel, TradingVenueModel.id == WarrantListingModel.trading_venue_id
                )
                .where(
                    WarrantListingModel.id == request.warrant_listing_id,
                    WarrantListingModel.workspace_id == request.workspace_id,
                    WarrantModel.workspace_id == request.workspace_id,
                    WarrantListingModel.lifecycle_status == WarrantLifecycle.ACTIVE,
                    WarrantModel.lifecycle_status == WarrantLifecycle.ACTIVE,
                    TradingVenueModel.is_active.is_(True),
                )
            )
        ).one_or_none()
        if row is None:
            return None
        listing, warrant, venue = row
        if not warrant.isin or not re.fullmatch(r"[A-Z0-9]{12}", warrant.isin):
            return None
        fingerprint = [
            str(request.workspace_id),
            str(warrant.id),
            str(warrant.version),
            str(listing.id),
            str(listing.version),
            venue.mic,
            warrant.isin,
            warrant.wkn or "",
            listing.quotation_currency_code,
            self._name.value,
        ]
        if self._name == MarketDataProvider.BOERSE_STUTTGART_DELAYED:
            if venue.mic != "XSTU":
                return None
            exchange = "XSTU"
        else:
            mapping = await session.scalar(
                select(WarrantProviderMappingModel).where(
                    WarrantProviderMappingModel.workspace_id == request.workspace_id,
                    WarrantProviderMappingModel.warrant_listing_id == listing.id,
                    WarrantProviderMappingModel.provider == self._name,
                    WarrantProviderMappingModel.status == MappingStatus.ACTIVE,
                    WarrantProviderMappingModel.validated_at.is_not(None),
                )
            )
            if mapping is None or mapping.provider_symbol != warrant.isin:
                return None
            exchange = mapping.provider_exchange_code
            if self._name == MarketDataProvider.VONTOBEL_MARKETS and exchange != "ISSUER":
                return None
            if self._name == MarketDataProvider.FRANKFURT_QUOTES and (
                venue.mic != "XFRA" or exchange not in {"XSC", "XFRA"}
            ):
                return None
            fingerprint.extend([str(mapping.id), str(mapping.version), exchange])
        return QuoteIdentity(
            hashlib.sha256("|".join(fingerprint).encode()).hexdigest(),
            warrant.isin,
            warrant.wkn,
            listing.quotation_currency_code,
            exchange,
            venue.mic,
        )
