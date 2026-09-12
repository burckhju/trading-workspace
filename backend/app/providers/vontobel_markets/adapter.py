"""Fail-closed adapter for the structured payload on official Vontobel product pages."""

from __future__ import annotations

import asyncio
import json
from collections import OrderedDict
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from time import monotonic
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select

from app.core.config.settings import VontobelMarketsSettings
from app.database import DatabaseManager
from app.features.market_data.domain.enums import (
    CacheStatus,
    MappingStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.persistence.models import WarrantProviderMappingModel
from app.features.market_data.service.errors import (
    MarketDataConfigurationError,
    MarketDataInvalidResponseError,
    MarketDataMappingError,
    MarketDataNotFoundError,
)
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest
from app.features.product.domain.models import WarrantLifecycle
from app.features.product.persistence.models import WarrantListingModel, WarrantModel


class _NextDataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.capture = False
        self.value: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script" and dict(attrs).get("id") == "__NEXT_DATA__":
            self.capture = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self.capture:
            self.capture = False

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.value.append(data)


@dataclass(frozen=True, slots=True)
class VontobelIdentity:
    listing_id: UUID
    isin: str
    wkn: str | None
    currency: str
    provider_symbol: str
    provider_exchange_code: str


_Identity = VontobelIdentity


class VontobelMarketsWarrantQuoteAdapter:
    """Read an exact issuer quote identified by an explicitly active ISIN mapping."""

    def __init__(
        self,
        *,
        database: DatabaseManager,
        settings: VontobelMarketsSettings,
        client: httpx.AsyncClient | None = None,
        cache_seconds: int = 0,
    ) -> None:
        self._database = database
        self._settings = settings
        self._client = client
        self._cache_seconds = cache_seconds
        self._cache: OrderedDict[
            VontobelIdentity, tuple[WarrantQuoteSnapshot | None, datetime, float]
        ] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get_warrant_listing_quote(
        self, request: WarrantQuoteRequest
    ) -> MarketDataResult[WarrantQuoteSnapshot | None]:
        if not self._settings.enabled:
            raise MarketDataConfigurationError(
                "Vontobel Markets quote provider is disabled",
                provider=MarketDataProvider.VONTOBEL_MARKETS,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )
        identity = await self._resolve_identity(request)
        quote, retrieved_at, hit = await self.probe(identity)
        if quote is not None:
            quote = replace(quote, assessed_at=datetime.now(UTC))
        return MarketDataResult(
            data=quote,
            provider=MarketDataProvider.VONTOBEL_MARKETS,
            capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            correlation_id=request.correlation_id,
            retrieved_at=retrieved_at,
            cache_status=CacheStatus.HIT if hit else CacheStatus.BYPASS,
            quality_status=QualityStatus.VALID,
            warnings=(
                "Official issuer indication; not an executable exchange order-book quote",
                "source=official_product_page_structured_payload",
            ),
            retry_count=0,
            provider_call_cost=0,
        )

    async def probe(
        self, identity: VontobelIdentity
    ) -> tuple[WarrantQuoteSnapshot | None, datetime, bool]:
        """Validate exact issuer identity before an automatic mapping may be written."""
        if not self._settings.enabled:
            raise MarketDataConfigurationError("Vontobel Markets quote provider is disabled")
        async with self._lock:
            cached = self._cache.get(identity)
            if cached is not None and monotonic() < cached[2]:
                return cached[0], cached[1], True
            quote, retrieved_at = await self._download(identity)
            if self._cache_seconds:
                self._cache[identity] = (quote, retrieved_at, monotonic() + self._cache_seconds)
                self._cache.move_to_end(identity)
                if len(self._cache) > 256:
                    self._cache.popitem(last=False)
            return quote, retrieved_at, False

    async def _download(
        self, identity: VontobelIdentity
    ) -> tuple[WarrantQuoteSnapshot | None, datetime]:
        url = (
            f"{self._settings.base_url}/{self._settings.culture}/produkte/hebel/"
            f"optionsscheine/{identity.isin}"
        )
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(
            timeout=self._settings.timeout_seconds, follow_redirects=False
        )
        retrieved_at = datetime.now(UTC)
        try:
            response = await client.get(url, headers={"Accept": "text/html"})
            response.raise_for_status()
            if str(response.url) != url:
                raise self._invalid("Vontobel product request changed identity through a redirect")
            quote = self._parse(response.text, identity)
        finally:
            if owns_client:
                await client.aclose()
        return quote, retrieved_at

    async def _resolve_identity(self, request: WarrantQuoteRequest) -> _Identity:
        async with self._database.session_context() as session:
            row = (
                await session.execute(
                    select(WarrantListingModel, WarrantModel, WarrantProviderMappingModel)
                    .join(WarrantModel, WarrantModel.id == WarrantListingModel.warrant_id)
                    .join(
                        WarrantProviderMappingModel,
                        WarrantProviderMappingModel.warrant_listing_id == WarrantListingModel.id,
                    )
                    .where(
                        WarrantListingModel.id == request.warrant_listing_id,
                        WarrantListingModel.workspace_id == request.workspace_id,
                        WarrantListingModel.lifecycle_status == WarrantLifecycle.ACTIVE,
                        WarrantModel.workspace_id == request.workspace_id,
                        WarrantModel.lifecycle_status == WarrantLifecycle.ACTIVE,
                        WarrantProviderMappingModel.workspace_id == request.workspace_id,
                        WarrantProviderMappingModel.provider == MarketDataProvider.VONTOBEL_MARKETS,
                        WarrantProviderMappingModel.status == MappingStatus.ACTIVE,
                        WarrantProviderMappingModel.validated_at.is_not(None),
                    )
                )
            ).one_or_none()
        if row is None:
            # No configured route is not a failed quote request. The shared
            # resolver skips this before HTTP; inconsistent existing mappings
            # below must still be reported as errors.
            raise MarketDataNotFoundError(
                "VONTOBEL_ACTIVE_MAPPING_NOT_FOUND",
                provider=MarketDataProvider.VONTOBEL_MARKETS,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )
        listing, warrant, mapping = row
        isin = (warrant.isin or "").upper()
        if not isin or mapping.provider_symbol.upper() != isin:
            raise MarketDataMappingError(
                "Vontobel mapping must use the Warrant ISIN as provider identity",
                provider=MarketDataProvider.VONTOBEL_MARKETS,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )
        if mapping.provider_exchange_code.upper() != "ISSUER":
            raise MarketDataMappingError(
                "Vontobel issuer quotes require provider_exchange_code=ISSUER",
                provider=MarketDataProvider.VONTOBEL_MARKETS,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )
        return _Identity(
            listing_id=listing.id,
            isin=isin,
            wkn=warrant.wkn.upper() if warrant.wkn else None,
            currency=listing.quotation_currency_code.upper(),
            provider_symbol=mapping.provider_symbol.upper(),
            provider_exchange_code=mapping.provider_exchange_code.upper(),
        )

    def _parse(self, html: str, identity: _Identity) -> WarrantQuoteSnapshot | None:
        parser = _NextDataParser()
        parser.feed(html)
        if not parser.value:
            raise self._invalid("Vontobel response has no structured __NEXT_DATA__ payload")
        try:
            root = json.loads("".join(parser.value))
            page_props = root["props"]["pageProps"]
            additional_data = page_props.get("additionalData")
            if isinstance(additional_data, dict) and isinstance(additional_data.get("data"), dict):
                # Current payload: product master data is nested under ``data``;
                # quote, identifiers and trading hours are sibling properties.
                data = additional_data["data"]
                quote_data = additional_data
            else:
                # Previous payload retained for compatibility with already
                # deployed Vontobel page versions and cached responses.
                data = page_props["data"]["additionalData"]["data"]
                quote_data = data
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise self._invalid(
                "Vontobel structured product payload has an unknown schema"
            ) from exc
        if str(data.get("isin", "")).upper() != identity.isin:
            raise self._invalid("Vontobel payload ISIN does not match the requested mapping")
        identifiers = {
            str(item.get("value", "")).upper()
            for item in quote_data.get("identifiers", [])
            if isinstance(item, dict)
        }
        if identity.isin not in identifiers or (identity.wkn and identity.wkn not in identifiers):
            raise self._invalid("Vontobel payload identifiers do not match ISIN/WKN master data")
        price = quote_data.get("price")
        if not isinstance(price, dict):
            return None
        currency = str(price.get("currency", "")).upper()
        if currency != identity.currency:
            raise self._invalid("Vontobel quote currency does not match the WarrantListing")
        bid = self._decimal(price.get("bid"), "bid")
        ask = self._decimal(price.get("ask"), "ask")
        if bid is None and ask is None:
            return None
        timestamp = price.get("latestTimestamp")
        if not isinstance(timestamp, str):
            raise self._invalid("Vontobel quote has no timestamp")
        try:
            observed_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone(UTC)
        except ValueError as exc:
            raise self._invalid("Vontobel quote timestamp is invalid") from exc
        trading = quote_data.get("tradingHours")
        status = "OPEN" if isinstance(trading, dict) and trading.get("isOpen") is True else "CLOSED"
        return WarrantQuoteSnapshot(
            warrant_listing_id=identity.listing_id,
            bid=bid,
            ask=ask,
            currency=currency,
            provider_symbol=identity.provider_symbol,
            provider_exchange_code=identity.provider_exchange_code,
            observed_at=observed_at,
            isin=identity.isin,
            wkn=identity.wkn,
            source_mode="OFFICIAL_ISSUER_INDICATION",
            trading_status=status,
        )

    def _decimal(self, value: Any, field: str) -> Decimal | None:
        if value is None:
            return None
        try:
            result = Decimal(str(value))
        except InvalidOperation as exc:
            raise self._invalid(f"Vontobel {field} is invalid") from exc
        if not result.is_finite() or result <= 0:
            raise self._invalid(f"Vontobel {field} must be positive")
        return result

    @staticmethod
    def _invalid(message: str) -> MarketDataInvalidResponseError:
        return MarketDataInvalidResponseError(
            message,
            provider=MarketDataProvider.VONTOBEL_MARKETS,
            capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
        )
