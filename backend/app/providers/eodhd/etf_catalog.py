"""Corroborate reviewed ETF listings with exact live EODHD catalog identities."""

from __future__ import annotations

import asyncio
import re
from collections import OrderedDict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Annotated
from urllib.parse import quote, urlsplit

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from app.features.market_data.domain.enums import MarketDataCapability, MarketDataProvider
from app.features.market_data.service.errors import MarketDataInvalidResponseError
from app.features.market_data.service.types import ProviderInstrumentSearchItem
from app.providers.eodhd.client import EodhdClient, QueryValue
from app.providers.eodhd.dto import EodhdSearchResultDto
from app.providers.shared.budget import DailyCallBudget
from app.providers.shared.cache import InMemoryTtlCache
from app.providers.shared.clock import Clock
from app.providers.shared.rate_limit import TokenBucketRateLimiter
from app.providers.shared.retry import RetryPolicy

# These are deliberately separate proofs: EODHD identifies the US operating
# venue; the versioned, reviewed exchange/issuer source identifies the segment.
# NASDAQ alone is NOT proof of XNMS. See SP500_ETF_CHART_UNIVERSE_20261109.md.
_VENUES = {"ARCX": ("XNYS", "NYSE ARCA"), "XNMS": ("XNAS", "NASDAQ")}
_TTL = timedelta(hours=24)
_CAPABILITY = MarketDataCapability.INSTRUMENT_SEARCH
_CATALOG = "/exchange-symbol-list/US"


class _Exchange(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    code: str = Field(alias="Code", min_length=1, max_length=32)
    operating_mic: str | None = Field(default=None, alias="OperatingMIC")

    @property
    def mics(self) -> frozenset[str]:
        return frozenset(m.strip().upper() for m in (self.operating_mic or "").split(","))


class _Ticker(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    code: str = Field(alias="Code", min_length=1, max_length=100)
    exchange: str = Field(alias="Exchange", min_length=1)
    name: str | None = Field(default=None, alias="Name")
    currency: str | None = Field(default=None, alias="Currency")
    instrument_type: str | None = Field(default=None, alias="Type")
    isin: str | None = Field(default=None, alias="Isin")


@dataclass(frozen=True, slots=True)
class EtfCatalogIdentity:
    item: ProviderInstrumentSearchItem
    mic: str
    endpoint: str
    catalog_retrieved_at: datetime
    exchanges_retrieved_at: datetime
    listing_ticker: str
    listing_source_url: str
    listing_reviewed_on: date
    venue_source_url: str
    provider_venue: str
    search_endpoint: str | None = None
    search_retrieved_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class _Snapshot[T]:
    rows: tuple[T, ...]
    retrieved_at: datetime


class EodhdEtfCatalog:
    """Use shared provider quota/retries; never infer a provider code from a ticker."""

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
        self._lock = asyncio.Lock()
        self._exchanges = InMemoryTtlCache[str, _Snapshot[_Exchange]](clock=clock)
        self._tickers = InMemoryTtlCache[str, _Snapshot[_Ticker]](clock=clock)
        self._searches = InMemoryTtlCache[str, _Snapshot[EodhdSearchResultDto]](clock=clock)
        self._search_keys: OrderedDict[str, None] = OrderedDict()

    async def verify(
        self,
        *,
        isin: str,
        currency: str,
        mic: str,
        listing_ticker: str,
        listing_source_url: str,
        listing_reviewed_on: date,
        venue_source_url: str,
    ) -> EtfCatalogIdentity:
        """Verify the listing and return evidence, without changing any master data."""
        if (
            mic not in _VENUES
            or listing_reviewed_on > self._clock.utcnow().date()
            or not all(
                urlsplit(url).scheme == "https" and bool(urlsplit(url).hostname)
                for url in (listing_source_url, venue_source_url)
            )
        ):
            raise ValueError("ETF_REVIEWED_LISTING_EVIDENCE_REQUIRED")
        async with self._lock:
            exchanges = await self._load(
                "/exchanges-list/",
                TypeAdapter(Annotated[list[_Exchange], Field(min_length=1, max_length=256)]),
                self._exchanges,
            )
            us = [e for e in exchanges.rows if e.code.upper() == "US"]
            operating_mic, venue_label = _VENUES[mic]
            if len(us) != 1 or operating_mic not in us[0].mics:
                raise ValueError("EODHD_ETF_OPERATING_VENUE_NOT_VERIFIED")
            catalog = await self._load(
                _CATALOG,
                TypeAdapter(Annotated[list[_Ticker], Field(min_length=1, max_length=100_000)]),
                self._tickers,
                params={"type": "etf"},
            )
            rows = [row for row in catalog.rows if row.isin == isin]
            search: _Snapshot[EodhdSearchResultDto] | None = None
            search_endpoint = None
            if not rows:
                search_endpoint = f"/search/{quote(isin, safe='')}"
                search = await self._search(search_endpoint)
                exact = [
                    row for row in search.rows if row.isin == isin and row.exchange.upper() == "US"
                ]
                if not exact or len(exact) > 12:
                    raise ValueError("EODHD_ETF_EXACT_ISIN_REQUIRED")
                candidates = {row.code.strip().upper() for row in exact}
                if len(candidates) != 1 or any(
                    row.currency != currency or (row.type or "").upper() != "ETF" for row in exact
                ):
                    raise ValueError("EODHD_ETF_IDENTITY_AMBIGUOUS")
                if any(
                    row.exchange.upper() == "US"
                    and row.code.strip().upper() in candidates
                    and (row.isin != isin or row.currency != currency or row.type != exact[0].type)
                    for row in search.rows
                ):
                    raise ValueError("EODHD_ETF_SEARCH_IDENTITY_CONFLICT")
                rows = [row for row in catalog.rows if row.code.strip().upper() in candidates]
            symbols = {row.code.strip().upper() for row in rows}
            if len(symbols) != 1:
                raise ValueError("EODHD_ETF_IDENTITY_AMBIGUOUS")
            symbol = next(iter(symbols))
            if not re.fullmatch(r"[A-Z0-9][A-Z0-9._-]{0,63}", symbol):
                raise ValueError("EODHD_PROVIDER_SYMBOL_UNSUPPORTED")
            # Corroborate the reviewed listing, never assign its ticker as a provider code.
            if symbol != listing_ticker.strip().upper():
                raise ValueError("EODHD_ETF_REVIEWED_LISTING_CONFLICT")
            duplicates = [row for row in catalog.rows if row.code.strip().upper() == symbol]
            if not all(
                row.isin in ({isin, None, ""} if search is not None else {isin})
                and row.currency == currency
                and (row.instrument_type or "").upper() == "ETF"
                and row.exchange.upper() == venue_label
                for row in duplicates
            ):
                raise ValueError("EODHD_ETF_CATALOG_IDENTITY_CONFLICT")
            row = rows[0]
            return EtfCatalogIdentity(
                ProviderInstrumentSearchItem(
                    MarketDataProvider.EODHD,
                    symbol,
                    us[0].code.upper(),
                    row.name,
                    row.instrument_type,
                    currency,
                    isin,
                ),
                mic,
                _CATALOG,
                catalog.retrieved_at,
                exchanges.retrieved_at,
                listing_ticker,
                listing_source_url,
                listing_reviewed_on,
                venue_source_url,
                venue_label,
                search_endpoint,
                search.retrieved_at if search else None,
            )

    async def _search(self, endpoint: str) -> _Snapshot[EodhdSearchResultDto]:
        if endpoint not in self._search_keys and len(self._search_keys) >= 256:
            oldest, _ = self._search_keys.popitem(last=False)
            await self._searches.delete(oldest)
        self._search_keys[endpoint] = None
        self._search_keys.move_to_end(endpoint)
        snapshot = await self._load(
            endpoint,
            TypeAdapter(Annotated[list[EodhdSearchResultDto], Field(max_length=500)]),
            self._searches,
            params={"limit": 500},
        )
        if len(snapshot.rows) >= 500:
            raise ValueError("EODHD_SEARCH_RESULT_LIMIT_REACHED")
        return snapshot

    async def _load[T](
        self,
        path: str,
        parser: TypeAdapter[list[T]],
        cache: InMemoryTtlCache[str, _Snapshot[T]],
        *,
        params: dict[str, QueryValue] | None = None,
    ) -> _Snapshot[T]:
        cached = await cache.get(path)
        if cached.hit and cached.value is not None:
            return cached.value

        async def operation() -> _Snapshot[T]:
            await self._budget.consume(self._call_cost, capability=_CAPABILITY)
            await self._limiter.acquire()
            payload = await self._client.get_json(path, capability=_CAPABILITY, params=params)
            try:
                rows = parser.validate_python(payload)
            except ValidationError as exc:
                raise MarketDataInvalidResponseError(
                    "EODHD ETF catalog has an invalid structure",
                    provider=MarketDataProvider.EODHD,
                    capability=_CAPABILITY,
                    retryable=False,
                ) from exc
            return _Snapshot(tuple(rows), self._clock.utcnow())

        result = await self._retry.execute(operation)
        await cache.set(path, result.value, ttl=_TTL)
        return result.value
