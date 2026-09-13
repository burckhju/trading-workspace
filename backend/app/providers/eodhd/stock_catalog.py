"""Exact stock identity discovery from EODHD's official exchange catalogs."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Annotated
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from app.features.market_data.domain.enums import MarketDataCapability, MarketDataProvider
from app.features.market_data.service.errors import MarketDataInvalidResponseError
from app.features.market_data.service.types import ProviderInstrumentSearchItem
from app.providers.eodhd.client import EodhdClient
from app.providers.shared.budget import DailyCallBudget
from app.providers.shared.cache import InMemoryTtlCache
from app.providers.shared.clock import Clock
from app.providers.shared.rate_limit import TokenBucketRateLimiter
from app.providers.shared.retry import RetryPolicy

# EODHD documents these venue labels within its composite US catalog. ISO 10383
# verifies their MICs; see docs/underlying-mapping-discovery.md. Never interpret
# US itself as one venue, or broaden operating MICs to unverified segments.
_US_VENUES = {"XNAS": "NASDAQ", "XNYS": "NYSE"}
_TTL = timedelta(hours=24)
_CAPABILITY = MarketDataCapability.INSTRUMENT_SEARCH


class _Exchange(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    code: str = Field(alias="Code", min_length=1, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    operating_mic: str | None = Field(default=None, alias="OperatingMIC")

    @property
    def mics(self) -> frozenset[str]:
        return frozenset(
            m.strip().upper() for m in (self.operating_mic or "").split(",") if m.strip()
        )


class _Ticker(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    code: str = Field(alias="Code", min_length=1, max_length=100)
    exchange: str = Field(alias="Exchange", min_length=1)
    name: str | None = Field(default=None, alias="Name")
    currency: str | None = Field(default=None, alias="Currency")
    instrument_type: str | None = Field(default=None, alias="Type")
    # The symbol-list endpoint uses Isin; Search uses ISIN. Do not confuse them.
    isin: str | None = Field(default=None, alias="Isin")


@dataclass(frozen=True, slots=True)
class StockCatalogIdentity:
    item: ProviderInstrumentSearchItem
    mic: str
    endpoint: str
    catalog_retrieved_at: datetime
    exchanges_retrieved_at: datetime


@dataclass(frozen=True, slots=True)
class StockCatalogDiscovery:
    reason: str
    identity: StockCatalogIdentity | None = None
    provider_exchange_code: str | None = None
    matching_isin_count: int = 0
    candidate_currencies: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _Snapshot[T]:
    rows: tuple[T, ...]
    retrieved_at: datetime


class EodhdStockCatalog:
    """Share the adapter's quota, retries and limiter; cache only valid catalogs."""

    def __init__(
        self,
        *,
        client: EodhdClient,
        retry: RetryPolicy,
        rate_limiter: TokenBucketRateLimiter,
        budget: DailyCallBudget,
        clock: Clock,
        call_cost: int,
    ) -> None:
        self._client = client
        self._retry = retry
        self._limiter = rate_limiter
        self._budget = budget
        self._clock = clock
        self._call_cost = call_cost
        self._exchanges = InMemoryTtlCache[str, _Snapshot[_Exchange]](clock=clock)
        self._tickers = InMemoryTtlCache[str, _Snapshot[_Ticker]](clock=clock)
        self._lock = asyncio.Lock()

    async def discover(self, *, isin: str, currency: str, mic: str) -> StockCatalogDiscovery:
        """Approve exactly one stock at the requested venue; never change master data."""
        async with self._lock:
            exchanges = await self._load(
                "/exchanges-list/",
                TypeAdapter(Annotated[list[_Exchange], Field(min_length=1, max_length=256)]),
                self._exchanges,
            )
            matches = [e for e in exchanges.rows if mic in e.mics]
            if not matches:
                return StockCatalogDiscovery("EODHD_VENUE_NOT_IN_CATALOG")
            if len(matches) != 1:
                return StockCatalogDiscovery("EODHD_VENUE_CATALOG_AMBIGUOUS")
            exchange = matches[0]
            code = exchange.code.upper()
            # Query the documented US sub-venue to avoid downloading OTC/fund rows.
            # Still require the row's Exchange to agree, and retain US as price suffix.
            if code == "US":
                label = _US_VENUES.get(mic)
                if label is None:
                    return StockCatalogDiscovery(
                        "EODHD_VENUE_DETAIL_UNSUPPORTED", provider_exchange_code=code
                    )
            elif len(exchange.mics) == 1:
                label = code
            else:
                return StockCatalogDiscovery(
                    "EODHD_VENUE_DETAIL_UNSUPPORTED", provider_exchange_code=code
                )
            endpoint = f"/exchange-symbol-list/{quote(label, safe='')}"
            tickers = await self._load(
                endpoint,
                TypeAdapter(Annotated[list[_Ticker], Field(max_length=100_000)]),
                self._tickers,
            )
            same_isin = [r for r in tickers.rows if r.isin == isin]
            same_currency = [r for r in same_isin if r.currency == currency]
            stocks = [
                r
                for r in same_currency
                if (r.instrument_type or "").lower() in {"common stock", "stock"}
            ]
            venue_rows = [r for r in stocks if r.exchange.upper() == label]
            # A conflicting duplicate is not resolved by choosing the nicer row.
            symbols = {r.code.strip().upper() for r in venue_rows if r.code.strip()}
            if not same_isin:
                reason = "EODHD_ISIN_NOT_FOUND_ON_VENUE"
            elif not same_currency:
                reason = "EODHD_LISTING_CURRENCY_MISMATCH"
            elif not stocks:
                reason = "EODHD_STOCK_TYPE_REQUIRED"
            elif len(venue_rows) != len(stocks) or not symbols:
                reason = "EODHD_INSTRUMENT_VENUE_MISMATCH"
            elif len(symbols) != 1:
                reason = "EODHD_STOCK_IDENTITY_AMBIGUOUS"
            elif not re.fullmatch(r"[A-Z0-9][A-Z0-9._-]{0,99}", next(iter(symbols))):
                reason = "EODHD_PROVIDER_SYMBOL_UNSUPPORTED"
            elif any(
                r.code.strip().upper() in symbols and r not in venue_rows for r in tickers.rows
            ):
                reason = "EODHD_STOCK_IDENTITY_AMBIGUOUS"
            else:
                row = venue_rows[0]
                return StockCatalogDiscovery(
                    "EODHD_CATALOG_IDENTITY_VERIFIED",
                    StockCatalogIdentity(
                        ProviderInstrumentSearchItem(
                            MarketDataProvider.EODHD,
                            row.code,
                            code,
                            row.name,
                            row.instrument_type,
                            row.currency,
                            row.isin,
                        ),
                        mic,
                        endpoint,
                        tickers.retrieved_at,
                        exchanges.retrieved_at,
                    ),
                    code,
                    len(same_isin),
                )
            return StockCatalogDiscovery(
                reason,
                provider_exchange_code=code,
                matching_isin_count=len(same_isin),
                candidate_currencies=tuple(sorted({r.currency or "UNKNOWN" for r in same_isin})),
            )

    async def _load[T](
        self, path: str, parser: TypeAdapter[list[T]], cache: InMemoryTtlCache[str, _Snapshot[T]]
    ) -> _Snapshot[T]:
        cached = await cache.get(path)
        if cached.hit and cached.value is not None:
            return cached.value

        async def operation() -> _Snapshot[T]:
            await self._budget.consume(self._call_cost, capability=_CAPABILITY)
            await self._limiter.acquire()
            payload = await self._client.get_json(path, capability=_CAPABILITY)
            try:
                rows = parser.validate_python(payload)
            except ValidationError as exc:
                raise MarketDataInvalidResponseError(
                    "EODHD stock catalog has an invalid structure",
                    provider=MarketDataProvider.EODHD,
                    capability=_CAPABILITY,
                    retryable=False,
                ) from exc
            return _Snapshot(tuple(rows), self._clock.utcnow())

        outcome = await self._retry.execute(operation)
        await cache.set(path, outcome.value, ttl=_TTL)
        return outcome.value
