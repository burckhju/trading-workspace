"""Market-data administration and EOD import for semantic MarketReferences.

This service uses the neutral MarketDataInstrument identity directly. It deliberately
avoids manufacturing an FT-001 Underlying or Listing for an index.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import TypeVar
from uuid import UUID, uuid4

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.market_data.domain.enums import (
    MappingStatus,
    MarketDataCapability,
    MarketDataProvider,
    PriceType,
    QualityStatus,
)
from app.features.market_data.persistence.models import (
    DailyPriceModel,
    ProviderInstrumentMappingModel,
)
from app.features.market_data.service.instrument_identity import MarketDataInstrumentIdentityService
from app.providers.eodhd.client import EodhdClient
from app.providers.eodhd.dto import EodhdDailyPriceDto, EodhdSearchResultDto
from app.providers.shared.budget import DailyCallBudget
from app.providers.shared.rate_limit import TokenBucketRateLimiter
from app.providers.shared.retry import RetryPolicy

_SEARCH_RESULTS = TypeAdapter(list[EodhdSearchResultDto])
_DAILY_PRICES = TypeAdapter(list[EodhdDailyPriceDto])
T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ReferencePriceImportResult:
    market_reference_id: UUID
    market_data_instrument_id: UUID
    mapping_id: UUID
    currency: str
    start_date: date
    end_date: date
    inserted: int
    updated: int
    unchanged: int


class ReferenceMarketDataService:
    """Own provider mapping and persisted EOD history for MarketReferences."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        client: EodhdClient,
        call_budget: DailyCallBudget,
        retry_policy: RetryPolicy,
        rate_limiter: TokenBucketRateLimiter,
        provider_call_cost: int = 1,
    ) -> None:
        self._session = session
        self._client = client
        self._budget = call_budget
        self._retry = retry_policy
        self._rate_limiter = rate_limiter
        self._provider_call_cost = provider_call_cost
        self._identity = MarketDataInstrumentIdentityService(session)

    async def upsert_mapping(
        self,
        *,
        workspace_id: UUID,
        market_reference_id: UUID,
        provider_symbol: str,
        provider_exchange_code: str,
    ) -> ProviderInstrumentMappingModel:
        instrument = await self._identity.for_market_reference(
            workspace_id=workspace_id,
            market_reference_id=market_reference_id,
        )
        mapping = await self._session.scalar(
            select(ProviderInstrumentMappingModel).where(
                ProviderInstrumentMappingModel.workspace_id == workspace_id,
                ProviderInstrumentMappingModel.market_data_instrument_id == instrument.id,
                ProviderInstrumentMappingModel.provider == MarketDataProvider.EODHD,
            )
        )
        now = datetime.now(UTC)
        symbol = provider_symbol.strip().upper()
        exchange = provider_exchange_code.strip().upper()
        if not symbol or not exchange:
            raise ValueError("provider symbol and exchange code must not be blank")
        if mapping is None:
            mapping = ProviderInstrumentMappingModel(
                id=uuid4(),
                workspace_id=workspace_id,
                listing_id=None,
                market_data_instrument_id=instrument.id,
                provider=MarketDataProvider.EODHD,
                provider_symbol=symbol,
                provider_exchange_code=exchange,
                status=MappingStatus.DISABLED,
                validated_at=None,
                validation_message="Awaiting explicit validation",
                created_at=now,
                updated_at=now,
                version=1,
            )
            self._session.add(mapping)
        else:
            mapping.provider_symbol = symbol
            mapping.provider_exchange_code = exchange
            mapping.status = MappingStatus.DISABLED
            mapping.validated_at = None
            mapping.validation_message = "Awaiting explicit validation"
            mapping.updated_at = now
            mapping.version += 1
        await self._session.commit()
        return mapping

    async def validate_mapping(
        self,
        *,
        workspace_id: UUID,
        market_reference_id: UUID,
    ) -> ProviderInstrumentMappingModel:
        mapping = await self._require_mapping(workspace_id, market_reference_id)
        match = await self._exact_search_match(mapping)
        now = datetime.now(UTC)
        mapping.validated_at = now
        mapping.updated_at = now
        mapping.version += 1
        if match is None:
            mapping.status = MappingStatus.INVALID
            mapping.validation_message = "EODHD did not return an exact symbol and exchange match"
        elif not (match.currency or "").strip():
            mapping.status = MappingStatus.INVALID
            mapping.validation_message = "EODHD exact match did not provide a currency"
        else:
            mapping.status = MappingStatus.ACTIVE
            mapping.validation_message = (
                f"Validated against EODHD Search API; currency={match.currency.strip().upper()}"
            )
        await self._session.commit()
        return mapping

    async def import_daily_prices(
        self,
        *,
        workspace_id: UUID,
        market_reference_id: UUID,
        start_date: date,
        end_date: date,
    ) -> ReferencePriceImportResult:
        if end_date < start_date:
            raise ValueError("end_date must not be before start_date")
        mapping = await self._require_mapping(workspace_id, market_reference_id)
        if mapping.status is not MappingStatus.ACTIVE:
            raise ValueError("EODHD provider mapping is not active")
        instrument_id = mapping.market_data_instrument_id
        if instrument_id is None:
            raise ValueError("provider mapping has no market-data instrument identity")
        match = await self._exact_search_match(mapping)
        if match is None or not (match.currency or "").strip():
            raise ValueError("provider currency could not be resolved from the validated mapping")
        currency = match.currency.strip().upper()

        async def load_prices() -> object:
            return await self._provider_call(
                capability=MarketDataCapability.HISTORICAL_DAILY_PRICES,
                operation=lambda: self._client.get_json(
                    f"/eod/{mapping.provider_symbol}.{mapping.provider_exchange_code}",
                    capability=MarketDataCapability.HISTORICAL_DAILY_PRICES,
                    params={
                        "from": start_date.isoformat(),
                        "to": end_date.isoformat(),
                        "period": "d",
                        "order": "a",
                    },
                ),
            )

        payload = await load_prices()
        try:
            rows = _DAILY_PRICES.validate_python(payload)
        except ValidationError as exc:
            raise ValueError("EODHD daily-price response has an invalid structure") from exc

        inserted = updated = unchanged = 0
        now = datetime.now(UTC)
        for row in rows:
            if not start_date <= row.date <= end_date:
                continue
            self._validate_ohlc(row)
            existing = await self._session.scalar(
                select(DailyPriceModel).where(
                    DailyPriceModel.workspace_id == workspace_id,
                    DailyPriceModel.market_data_instrument_id == instrument_id,
                    DailyPriceModel.trading_date == row.date,
                    DailyPriceModel.price_type == PriceType.EOD,
                )
            )
            values = {
                "open": row.open,
                "high": row.high,
                "low": row.low,
                "close": row.close,
                "adjusted_close": row.adjusted_close,
                "volume": row.volume,
                "currency": currency,
                "provider": MarketDataProvider.EODHD,
                "provider_symbol": mapping.provider_symbol,
                "retrieved_at": now,
                "source_updated_at": None,
                "quality_status": QualityStatus.VALID,
                "warnings": "",
                "price_type": PriceType.EOD,
            }
            if existing is None:
                self._session.add(
                    DailyPriceModel(
                        id=uuid4(),
                        workspace_id=workspace_id,
                        listing_id=None,
                        market_data_instrument_id=instrument_id,
                        trading_date=row.date,
                        created_at=now,
                        updated_at=now,
                        **values,
                    )
                )
                inserted += 1
                continue
            changed = False
            for field, value in values.items():
                if getattr(existing, field) != value:
                    setattr(existing, field, value)
                    changed = True
            if changed:
                existing.updated_at = now
                updated += 1
            else:
                unchanged += 1
        await self._session.commit()
        return ReferencePriceImportResult(
            market_reference_id=market_reference_id,
            market_data_instrument_id=instrument_id,
            mapping_id=mapping.id,
            currency=currency,
            start_date=start_date,
            end_date=end_date,
            inserted=inserted,
            updated=updated,
            unchanged=unchanged,
        )

    async def _require_mapping(
        self, workspace_id: UUID, market_reference_id: UUID
    ) -> ProviderInstrumentMappingModel:
        instrument = await self._identity.for_market_reference(
            workspace_id=workspace_id,
            market_reference_id=market_reference_id,
        )
        mapping = await self._session.scalar(
            select(ProviderInstrumentMappingModel).where(
                ProviderInstrumentMappingModel.workspace_id == workspace_id,
                ProviderInstrumentMappingModel.market_data_instrument_id == instrument.id,
                ProviderInstrumentMappingModel.provider == MarketDataProvider.EODHD,
            )
        )
        if mapping is None:
            raise ValueError("EODHD provider mapping was not found")
        return mapping

    async def _exact_search_match(
        self, mapping: ProviderInstrumentMappingModel
    ) -> EodhdSearchResultDto | None:
        payload = await self._provider_call(
            capability=MarketDataCapability.INSTRUMENT_MAPPING_VALIDATION,
            operation=lambda: self._client.get_json(
                f"/search/{mapping.provider_symbol}",
                capability=MarketDataCapability.INSTRUMENT_MAPPING_VALIDATION,
                params={"exchange": mapping.provider_exchange_code, "limit": 20},
            ),
        )
        try:
            rows = _SEARCH_RESULTS.validate_python(payload)
        except ValidationError as exc:
            raise ValueError("EODHD search response has an invalid structure") from exc
        symbol = mapping.provider_symbol.upper()
        exchange = mapping.provider_exchange_code.upper()
        return next(
            (
                row
                for row in rows
                if row.code.upper() == symbol and row.exchange.upper() == exchange
            ),
            None,
        )

    async def _provider_call(
        self,
        *,
        capability: MarketDataCapability,
        operation: Callable[[], Awaitable[T]],
    ) -> T:
        async def guarded() -> T:
            await self._budget.consume(self._provider_call_cost, capability=capability)
            await self._rate_limiter.acquire()
            return await operation()

        return (await self._retry.execute(guarded)).value

    @staticmethod
    def _validate_ohlc(row: EodhdDailyPriceDto) -> None:
        if min(row.open, row.high, row.low, row.close) <= 0:
            raise ValueError("provider returned non-positive OHLC data")
        if (
            row.low > row.high
            or not row.low <= row.open <= row.high
            or not row.low <= row.close <= row.high
        ):
            raise ValueError("provider returned inconsistent OHLC data")
        if row.adjusted_close is not None and row.adjusted_close <= 0:
            raise ValueError("provider returned non-positive adjusted close")
