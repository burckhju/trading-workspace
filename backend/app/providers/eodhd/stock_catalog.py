"""Exact stock identity discovery from EODHD's official exchange catalogs."""

from __future__ import annotations

import asyncio
import re
from collections import OrderedDict
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Annotated
from urllib.parse import quote

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
    search_endpoint: str | None = None
    search_retrieved_at: datetime | None = None

    @property
    def source(self) -> str:
        return (
            "EODHD_ISIN_SEARCH_AND_CATALOG"
            if self.search_endpoint is not None
            else "EODHD_OFFICIAL_STOCK_CATALOG"
        )


@dataclass(frozen=True, slots=True)
class StockCatalogAlternative:
    provider_symbol: str
    provider_exchange_code: str
    currency: str | None
    mic: str | None
    reason: str
    identity: StockCatalogIdentity | None = None


@dataclass(frozen=True, slots=True)
class StockCatalogDiscovery:
    reason: str
    identity: StockCatalogIdentity | None = None
    provider_exchange_code: str | None = None
    matching_isin_count: int = 0
    candidate_currencies: tuple[str, ...] = ()
    alternatives: tuple[StockCatalogAlternative, ...] = ()
    search_endpoint: str | None = None
    search_retrieved_at: datetime | None = None
    search_reason: str | None = None


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
        self._searches = InMemoryTtlCache[str, _Snapshot[EodhdSearchResultDto]](clock=clock)
        self._search_keys: OrderedDict[str, None] = OrderedDict()

    async def discover(self, *, isin: str, currency: str, mic: str) -> StockCatalogDiscovery:
        """Approve exactly one stock at the requested venue; never change master data."""
        async with self._lock:
            return await self._discover(isin=isin, currency=currency, mic=mic)

    async def _discover(self, *, isin: str, currency: str, mic: str) -> StockCatalogDiscovery:
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
        elif not re.fullmatch(r"[A-Z0-9][A-Z0-9._-]{0,63}", next(iter(symbols))):
            reason = "EODHD_PROVIDER_SYMBOL_UNSUPPORTED"
        elif any(r.code.strip().upper() in symbols and r not in venue_rows for r in tickers.rows):
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

    async def discover_with_search(
        self, *, isin: str, currency: str, mic: str
    ) -> StockCatalogDiscovery:
        """Fill absent catalog ISINs using corroborated search, never override conflicts."""
        async with self._lock:
            result = await self._discover(isin=isin, currency=currency, mic=mic)
            if result.reason != "EODHD_ISIN_NOT_FOUND_ON_VENUE":
                return result
            endpoint = f"/search/{quote(isin, safe='')}"
            if endpoint not in self._search_keys and len(self._search_keys) >= 256:
                oldest, _ = self._search_keys.popitem(last=False)
                await self._searches.delete(oldest)
            self._search_keys[endpoint] = None
            self._search_keys.move_to_end(endpoint)
            search = await self._load(
                endpoint,
                TypeAdapter(Annotated[list[EodhdSearchResultDto], Field(max_length=500)]),
                self._searches,
                params={"limit": 500},
            )
            result = replace(
                result, search_endpoint=endpoint, search_retrieved_at=search.retrieved_at
            )
            if len(search.rows) >= 500:
                return replace(result, search_reason="EODHD_SEARCH_RESULT_LIMIT_REACHED")
            # No fuzzy-name or ticker fallback; ADRs retain their own ISIN.
            matches = sorted(
                {row for row in search.rows if row.isin == isin},
                key=lambda r: (
                    r.exchange.upper() != result.provider_exchange_code,
                    r.currency != currency,
                    r.exchange,
                    r.code,
                    r.currency or "",
                    r.type or "",
                    r.name or "",
                ),
            )
            current = [r for r in matches if r.exchange.upper() == result.provider_exchange_code]
            # Never activate from a partially checked set of candidates at the
            # requested provider venue. Other venues are bounded review suggestions.
            if len(current) > 12:
                return replace(result, search_reason="EODHD_SEARCH_CANDIDATE_LIMIT_REACHED")
            alternatives: list[StockCatalogAlternative] = []
            for row in current:
                alternatives.extend(await self._verify_search_row(row, search, endpoint))
            applicable = [
                a for a in alternatives if a.mic in {mic, None} and a.currency in {currency, None}
            ]
            verified = [a for a in applicable if a.identity is not None]
            identities = {a.provider_symbol for a in verified}
            identity = (
                verified[0].identity
                if len(identities) == 1 and len(verified) == len(applicable)
                else None
            )
            if identity is not None:
                # A verified current listing must not depend on unrelated markets'
                # availability, nor spend quota fetching alternatives it does not need.
                return replace(
                    result,
                    reason="EODHD_SEARCH_CATALOG_IDENTITY_VERIFIED",
                    identity=identity,
                    alternatives=tuple(alternatives),
                    search_reason="EODHD_SEARCH_CANDIDATES_CHECKED",
                )
            for row in [r for r in matches if r not in current][: 12 - len(current)]:
                alternatives.extend(await self._verify_search_row(row, search, endpoint))
            search_reason = (
                "EODHD_SEARCH_CANDIDATES_CHECKED" if matches else "EODHD_SEARCH_ISIN_NOT_FOUND"
            )
            if len(matches) > 12:
                search_reason = "EODHD_SEARCH_ALTERNATIVES_TRUNCATED"
            return replace(
                result,
                reason=("EODHD_STOCK_IDENTITY_AMBIGUOUS" if len(identities) > 1 else result.reason),
                alternatives=tuple(alternatives),
                search_reason=search_reason,
            )

    async def _verify_search_row(
        self, row: EodhdSearchResultDto, search: _Snapshot[EodhdSearchResultDto], endpoint: str
    ) -> list[StockCatalogAlternative]:
        symbol, code = row.code.strip().upper(), row.exchange.upper()
        candidate = StockCatalogAlternative(symbol, code, row.currency, None, "UNVERIFIED")
        if (
            not re.fullmatch(r"[A-Z0-9][A-Z0-9._-]{0,63}", symbol)
            or not row.currency
            or (row.type or "").lower() not in {"common stock", "stock"}
        ):
            return [replace(candidate, reason="EODHD_SEARCH_STOCK_IDENTITY_REQUIRED")]
        if any(
            other.code.strip().upper() == symbol
            and other.exchange.upper() == code
            and (
                other.isin != row.isin
                or other.currency != row.currency
                or (other.type or "").lower() != (row.type or "").lower()
            )
            for other in search.rows
        ):
            return [replace(candidate, reason="EODHD_SEARCH_IDENTITY_CONFLICT")]
        exchanges = await self._load(
            "/exchanges-list/",
            TypeAdapter(Annotated[list[_Exchange], Field(min_length=1, max_length=256)]),
            self._exchanges,
        )
        venues = [e for e in exchanges.rows if e.code.upper() == code]
        if len(venues) != 1:
            return [replace(candidate, reason="EODHD_VENUE_CATALOG_AMBIGUOUS")]
        venue = venues[0]
        mics = sorted(venue.mics & _US_VENUES.keys()) if code == "US" else sorted(venue.mics)
        if not mics or (code != "US" and len(mics) != 1):
            return [replace(candidate, reason="EODHD_VENUE_DETAIL_UNSUPPORTED")]
        alternatives = []
        for mic in mics:
            if sum(mic in exchange.mics for exchange in exchanges.rows) != 1:
                alternatives.append(
                    replace(candidate, mic=mic, reason="EODHD_VENUE_CATALOG_AMBIGUOUS")
                )
                continue
            label = _US_VENUES[mic] if code == "US" else code
            catalog_endpoint = f"/exchange-symbol-list/{quote(label, safe='')}"
            tickers = await self._load(
                catalog_endpoint,
                TypeAdapter(Annotated[list[_Ticker], Field(max_length=100_000)]),
                self._tickers,
            )
            rows = [r for r in tickers.rows if r.code.strip().upper() == symbol]
            reason = "EODHD_SEARCH_SYMBOL_NOT_IN_VENUE_CATALOG"
            identity = None
            if rows:
                valid = all(
                    r.isin in {None, "", row.isin}
                    and r.currency == row.currency
                    and r.exchange.upper() == label
                    and (r.instrument_type or "").lower() in {"common stock", "stock"}
                    for r in rows
                )
                reason = "EODHD_SEARCH_CATALOG_CONFLICT"
                if valid:
                    reason = "EODHD_SEARCH_CATALOG_IDENTITY_VERIFIED"
                    identity = StockCatalogIdentity(
                        ProviderInstrumentSearchItem(
                            MarketDataProvider.EODHD,
                            symbol,
                            code,
                            row.name,
                            row.type,
                            row.currency,
                            row.isin,
                        ),
                        mic,
                        catalog_endpoint,
                        tickers.retrieved_at,
                        exchanges.retrieved_at,
                        endpoint,
                        search.retrieved_at,
                    )
            alternatives.append(replace(candidate, mic=mic, reason=reason, identity=identity))
        return alternatives

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
                    "EODHD stock catalog has an invalid structure",
                    provider=MarketDataProvider.EODHD,
                    capability=_CAPABILITY,
                    retryable=False,
                ) from exc
            return _Snapshot(tuple(rows), self._clock.utcnow())

        outcome = await self._retry.execute(operation)
        await cache.set(path, outcome.value, ttl=_TTL)
        return outcome.value
