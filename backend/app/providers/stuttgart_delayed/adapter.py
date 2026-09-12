"""Schema-gated adapter for verified XSTU delayed pre-trade payloads."""

from __future__ import annotations

import asyncio
import gzip
import json
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from time import monotonic
from typing import Any, cast
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy import select

from app.core.config.settings import StuttgartDelayedSettings, StuttgartDelayedSourceMode
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
    MarketDataNotFoundError,
)
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest
from app.features.product.domain.models import WarrantLifecycle
from app.features.product.persistence.models import WarrantListingModel, WarrantModel

_DOWNLOAD_LINK = re.compile(
    r'href=["\'](?P<href>[^"\']*ddl\.service\.boerse-stuttgart\.de[^"\']*)["\']',
    re.IGNORECASE,
)
_XSTU_FILE_NAME = re.compile(r"^XSTU-pretrade-(?P<stamp>\d{8}T\d{4})\.json\.gz$")


@dataclass(frozen=True, slots=True)
class _ListingIdentity:
    listing_id: Any
    symbol: str | None
    currency: str
    isin: str
    mic: str


class StuttgartDelayedWarrantQuoteAdapter:
    """Read an exact XSTU warrant listing quote from a configured delayed-data source."""

    def __init__(
        self,
        *,
        database: DatabaseManager,
        settings: StuttgartDelayedSettings,
        client: httpx.AsyncClient | None = None,
        cache_seconds: int = 0,
    ) -> None:
        self._database = database
        self._settings = settings
        self._client = client
        self._cache_seconds = cache_seconds
        self._payload_cache: tuple[Any, datetime, float] | None = None
        self._payload_lock = asyncio.Lock()

    async def get_warrant_listing_quote(
        self, request: WarrantQuoteRequest
    ) -> MarketDataResult[WarrantQuoteSnapshot | None]:
        self._require_ready_configuration()
        identity = await self._resolve_identity(request)

        payload, retrieved_at = await self._cached_payload()
        quote = self._parse_quote(payload, identity)
        if quote is not None:
            quote = replace(quote, assessed_at=datetime.now(UTC))
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
                f"source={self._settings.source_mode.value}",
            ),
            retry_count=0,
            provider_call_cost=None,
        )

    async def _cached_payload(self) -> tuple[Any, datetime]:
        """Share the large exchange snapshot; never replace its retrieval timestamp."""
        async with self._payload_lock:
            if self._payload_cache is not None and monotonic() < self._payload_cache[2]:
                return self._payload_cache[0], self._payload_cache[1]
            payload = await self._load_latest_payload()
            retrieved_at = datetime.now(UTC)
            if self._cache_seconds:
                self._payload_cache = (payload, retrieved_at, monotonic() + self._cache_seconds)
            return payload, retrieved_at

    def _require_ready_configuration(self) -> None:
        if (
            not self._settings.enabled
            or not self._settings.has_verified_schema
            or not self._settings.has_source_configuration
        ):
            raise MarketDataConfigurationError(
                "Stuttgart delayed quote provider requires enabled=true, a verified schema map, "
                "and a configured payload source",
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
                        WarrantListingModel.lifecycle_status == WarrantLifecycle.ACTIVE,
                        WarrantModel.workspace_id == request.workspace_id,
                    )
                )
            ).one_or_none()
        if row is None:
            raise MarketDataMappingError(
                "Active WarrantListing identity could not be resolved for Stuttgart delayed data",
                provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )
        listing, warrant, venue = row
        if venue.mic.upper() != "XSTU":
            # The implicit ISIN route of this feed applies only to XSTU. An
            # eligible listing at another venue is ordinary routing metadata,
            # not an invalid mapping and must not cause any feed download.
            raise MarketDataNotFoundError(
                "STUTTGART_LISTING_VENUE_NOT_SUPPORTED",
                provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )
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
        if self._settings.source_mode == StuttgartDelayedSourceMode.LOCAL_DIRECTORY:
            return self._load_latest_local_payload()
        if self._settings.source_mode == StuttgartDelayedSourceMode.DIRECT_URL:
            assert self._settings.direct_url is not None
            return await self._load_url_payload(self._settings.direct_url)
        return await self._load_index_payload()

    def _load_latest_local_payload(self) -> Any:
        assert self._settings.local_directory is not None
        directory = Path(self._settings.local_directory)
        if not directory.is_dir():
            raise MarketDataConfigurationError(
                "Configured Stuttgart delayed local_directory is not an accessible directory",
                provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )

        candidates = [
            path
            for path in directory.glob(self._settings.local_file_pattern)
            if path.is_file() and _XSTU_FILE_NAME.fullmatch(path.name)
        ]
        if not candidates:
            raise MarketDataInvalidResponseError(
                "No verified XSTU delayed payload file found in configured local_directory",
                provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )
        latest = max(candidates, key=lambda path: path.name)
        try:
            return self._decode_payload(latest.read_bytes())
        except OSError as exc:
            raise MarketDataInvalidResponseError(
                "Latest local Stuttgart delayed payload could not be read",
                provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            ) from exc

    async def _load_index_payload(self) -> Any:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._settings.timeout_seconds)
        try:
            index_response = await client.get(self._settings.index_url)
            index_response.raise_for_status()
            download_url = self._extract_official_download_url(index_response.text)
            response = await client.get(download_url)
            response.raise_for_status()
            return self._decode_payload(response.content)
        finally:
            if owns_client:
                await client.aclose()

    async def _load_url_payload(self, url: str) -> Any:
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._settings.timeout_seconds)
        try:
            response = await client.get(url)
            response.raise_for_status()
            return self._decode_payload(response.content)
        finally:
            if owns_client:
                await client.aclose()

    @staticmethod
    def _decode_payload(content: bytes) -> Any:
        try:
            decoded = gzip.decompress(content).decode("utf-8")
            return json.loads(decoded)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MarketDataInvalidResponseError(
                "Stuttgart delayed payload is not valid UTF-8 JSON gzip content",
                provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            ) from exc

    def _extract_official_download_url(self, html: str) -> str:
        match = _DOWNLOAD_LINK.search(html)
        if match is None:
            raise MarketDataInvalidResponseError(
                "No official Stuttgart delayed download link found in XSTU index",
                provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )
        url = cast(str, urljoin(self._settings.index_url, match.group("href")))
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != "ddl.service.boerse-stuttgart.de":
            raise MarketDataInvalidResponseError(
                "Stuttgart delayed download link uses an unexpected host",
                provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )
        return url

    def _parse_quote(self, payload: Any, identity: _ListingIdentity) -> WarrantQuoteSnapshot | None:
        selected_at: datetime | None = None
        selected_bid: Decimal | None = None
        selected_ask: Decimal | None = None
        selected_currency: str | None = None

        for record in self._records(payload):
            if not isinstance(record, dict):
                continue
            isin = self._text(record, self._settings.isin_field)
            mic = self._text(record, self._settings.mic_field)
            if isin is None or mic is None:
                continue
            if isin.upper() != identity.isin or mic.upper() != identity.mic:
                continue

            row_currency = self._text(record, self._settings.currency_field)
            timestamp = self._text(record, self._settings.observed_at_field)
            if row_currency is None or timestamp is None:
                continue
            row_currency = row_currency.upper()
            if row_currency != identity.currency:
                raise MarketDataMappingError(
                    "Stuttgart delayed quote currency does not match WarrantListing currency",
                    provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                    capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
                )

            row_bid = self._quote_side(record, self._settings.bid_field)
            row_ask = self._quote_side(record, self._settings.ask_field)
            if row_bid is None and row_ask is None:
                continue

            row_observed_at = self._datetime(timestamp)
            if selected_at is None or row_observed_at > selected_at:
                selected_at = row_observed_at
                selected_bid = row_bid
                selected_ask = row_ask
                selected_currency = row_currency
                continue
            if row_observed_at == selected_at:
                if selected_currency is not None and selected_currency != row_currency:
                    raise MarketDataInvalidResponseError(
                        "Stuttgart delayed quote contains conflicting currencies at one timestamp",
                        provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                        capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
                    )
                if row_bid is not None:
                    selected_bid = (
                        max(selected_bid, row_bid) if selected_bid is not None else row_bid
                    )
                if row_ask is not None:
                    selected_ask = (
                        min(selected_ask, row_ask) if selected_ask is not None else row_ask
                    )

        if selected_at is None or (selected_bid is None and selected_ask is None):
            return None
        if selected_bid is not None and selected_ask is not None and selected_ask < selected_bid:
            raise MarketDataInvalidResponseError(
                "Stuttgart delayed latest quote is crossed",
                provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )
        assert selected_currency is not None
        return WarrantQuoteSnapshot(
            warrant_listing_id=identity.listing_id,
            bid=selected_bid,
            ask=selected_ask,
            currency=selected_currency,
            provider_symbol=identity.isin,
            provider_exchange_code="XSTU",
            observed_at=selected_at,
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

    def _quote_side(self, record: dict[str, Any], path: str | None) -> Decimal | None:
        if path is None:
            return None
        value = self._value(record, path)
        if value is None:
            return None
        try:
            price = Decimal(str(value))
        except InvalidOperation as exc:
            raise MarketDataInvalidResponseError(
                "Stuttgart delayed quote contains an invalid price",
                provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            ) from exc
        if price < 0:
            raise MarketDataInvalidResponseError(
                "Stuttgart delayed quote price must not be negative",
                provider=MarketDataProvider.BOERSE_STUTTGART_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )
        return price if price > 0 else None

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
