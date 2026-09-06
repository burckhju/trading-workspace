"""Schema-gated adapter for the official XSTU delayed pre-trade download service."""

from __future__ import annotations

import gzip
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy import select

from app.core.config.settings import StuttgartDelayedSettings
from app.database import DatabaseManager
from app.features.market.persistence.models import TradingVenueModel
from app.features.market_data.domain.enums import (
    CacheStatus,
    MarketDataCapability,
    MarketDataProvider,
    QualityStatus,
)
from app.features.market_data.domain.models import WarrantQuoteSnapshot
from app.features.market_data.service.errors import (
    MarketDataConfigurationError,
    MarketDataInvalidResponseError,
    MarketDataMappingError,
)
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest
from app.features.product.persistence.models import WarrantListingModel, WarrantModel

_DOWNLOAD_LINK = re.compile(
    r'href=["\'](?P<href>[^"\']*ddl\.service\.boerse-stuttgart\.de[^"\']*)["\']',
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class _ListingIdentity:
    listing_id: Any
    symbol: str
    currency: str
    isin: str
    mic: str


class StuttgartDelayedWarrantQuoteAdapter:
    """Read an exact XSTU warrant listing quote from the official delayed-data files."""

    def __init__(
        self,
        *,
        database: DatabaseManager,
        settings: StuttgartDelayedSettings,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._database = database
        self._settings = settings
        self._client = client

    async def get_warrant_listing_quote(
        self, request: WarrantQuoteRequest
    ) -> MarketDataResult[WarrantQuoteSnapshot | None]:
        self._require_ready_configuration()
        identity = await self._resolve_identity(request)
        if identity.mic != "XSTU":
            raise MarketDataMappingError(
                "Börse Stuttgart delayed quotes are only valid for XSTU warrant listings",
                provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )

        retrieved_at = datetime.now(UTC)
        payload = await self._load_latest_payload()
        quote = self._parse_quote(payload, identity)
        return MarketDataResult(
            data=quote,
            provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
            capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            correlation_id=request.correlation_id,
            retrieved_at=retrieved_at,
            cache_status=CacheStatus.BYPASS,
            quality_status=QualityStatus.VALID,
            warnings=(
                "Börse Stuttgart XSTU delayed pre-trade data; not a real-time executable quote",
                f"schema={self._settings.schema_version}",
            ),
            retry_count=0,
            provider_call_cost=None,
        )

    def _require_ready_configuration(self) -> None:
        if not self._settings.enabled or not self._settings.has_verified_schema:
            raise MarketDataConfigurationError(
                "Stuttgart delayed quote provider requires enabled=true and a verified schema map",
                provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )

    async def _resolve_identity(self, request: WarrantQuoteRequest) -> _ListingIdentity:
        async with self._database.session_context() as session:
            row = (
                await session.execute(
                    select(WarrantListingModel, WarrantModel, TradingVenueModel)
                    .join(WarrantModel, WarrantModel.id == WarrantListingModel.warrant_id)
                    .join(
                        TradingVenueModel,
                        TradingVenueModel.id == WarrantListingModel.trading_venue_id,
                    )
                    .where(
                        WarrantListingModel.id == request.warrant_listing_id,
                        WarrantListingModel.workspace_id == request.workspace_id,
                        WarrantModel.workspace_id == request.workspace_id,
                    )
                )
            ).one_or_none()
        if row is None:
            raise MarketDataMappingError(
                "WarrantListing identity could not be resolved for Stuttgart delayed data",
                provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )
        listing, warrant, venue = row
        if warrant.isin is None:
            raise MarketDataMappingError(
                "Warrant ISIN is required for Stuttgart delayed quote matching",
                provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )
        return _ListingIdentity(
            listing_id=listing.id,
            symbol=listing.symbol,
            currency=listing.quotation_currency_code.upper(),
            isin=warrant.isin.upper(),
            mic=venue.mic.upper(),
        )

    async def _load_latest_payload(self) -> Any:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._settings.timeout_seconds)
        try:
            index_response = await client.get(self._settings.index_url)
            index_response.raise_for_status()
            download_url = self._extract_official_download_url(index_response.text)
            response = await client.get(download_url)
            response.raise_for_status()
            try:
                decoded = gzip.decompress(response.content).decode("utf-8")
                return json.loads(decoded)
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise MarketDataInvalidResponseError(
                    "Stuttgart delayed download is not valid UTF-8 JSON gzip content",
                    provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                    capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
                ) from exc
        finally:
            if owns_client:
                await client.aclose()

    def _extract_official_download_url(self, html: str) -> str:
        match = _DOWNLOAD_LINK.search(html)
        if match is None:
            raise MarketDataInvalidResponseError(
                "No official Stuttgart delayed download link found in XSTU index",
                provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )
        url = urljoin(self._settings.index_url, match.group("href"))
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != "ddl.service.boerse-stuttgart.de":
            raise MarketDataInvalidResponseError(
                "Stuttgart delayed download link uses an unexpected host",
                provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )
        return url

    def _parse_quote(self, payload: Any, identity: _ListingIdentity) -> WarrantQuoteSnapshot | None:
        records = self._records(payload)
        bid: Decimal | None = None
        ask: Decimal | None = None
        currency: str | None = None
        observed_at: datetime | None = None

        for record in records:
            if not isinstance(record, dict):
                continue
            isin = self._text(record, self._settings.isin_field)
            mic = self._text(record, self._settings.mic_field)
            if isin is None or mic is None:
                continue
            if isin.upper() != identity.isin or mic.upper() != identity.mic:
                continue

            row_currency = self._text(record, self._settings.currency_field)
            side = self._text(record, self._settings.side_field)
            price_text = self._text(record, self._settings.price_field)
            timestamp = self._text(record, self._settings.observed_at_field)
            if row_currency is None or side is None or price_text is None or timestamp is None:
                continue
            row_currency = row_currency.upper()
            if row_currency != identity.currency:
                raise MarketDataMappingError(
                    "Stuttgart delayed quote currency does not match WarrantListing currency",
                    provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                    capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
                )
            if currency is not None and currency != row_currency:
                raise MarketDataInvalidResponseError(
                    "Stuttgart delayed quote contains conflicting currencies for one listing",
                    provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                    capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
                )
            currency = row_currency
            price = self._decimal(price_text)
            row_observed_at = self._datetime(timestamp)
            observed_at = max(observed_at, row_observed_at) if observed_at else row_observed_at
            if side.upper() == self._settings.bid_side_value.upper():
                bid = max(bid, price) if bid is not None else price
            elif side.upper() == self._settings.ask_side_value.upper():
                ask = min(ask, price) if ask is not None else price

        if bid is None and ask is None:
            return None
        if bid is not None and ask is not None and ask < bid:
            raise MarketDataInvalidResponseError(
                "Stuttgart delayed quote is crossed after best-price aggregation",
                provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )
        assert currency is not None and observed_at is not None
        return WarrantQuoteSnapshot(
            warrant_listing_id=identity.listing_id,
            bid=bid,
            ask=ask,
            currency=currency,
            provider_symbol=identity.symbol,
            provider_exchange_code="XSTU",
            observed_at=observed_at,
        )

    def _records(self, payload: Any) -> list[Any]:
        path = self._settings.records_path
        assert path is not None
        value = payload if path == "$" else self._value(payload, path)
        if not isinstance(value, list):
            raise MarketDataInvalidResponseError(
                "Configured Stuttgart records_path does not resolve to a JSON array",
                provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )
        return value

    @staticmethod
    def _value(record: Any, path: str) -> Any:
        value = record
        for part in path.split("."):
            if not isinstance(value, dict) or part not in value:
                return None
            value = value[part]
        return value

    def _text(self, record: dict[str, Any], path: str | None) -> str | None:
        if path is None:
            return None
        value = self._value(record, path)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _decimal(value: str) -> Decimal:
        try:
            price = Decimal(value)
        except InvalidOperation as exc:
            raise MarketDataInvalidResponseError(
                "Stuttgart delayed quote contains an invalid price",
                provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            ) from exc
        if price <= 0:
            raise MarketDataInvalidResponseError(
                "Stuttgart delayed quote price must be positive",
                provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )
        return price

    @staticmethod
    def _datetime(value: str) -> datetime:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise MarketDataInvalidResponseError(
                "Stuttgart delayed quote contains an invalid timestamp",
                provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            ) from exc
        if parsed.tzinfo is None:
            raise MarketDataInvalidResponseError(
                "Stuttgart delayed quote timestamp must be timezone-aware",
                provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )
        return parsed.astimezone(UTC)
