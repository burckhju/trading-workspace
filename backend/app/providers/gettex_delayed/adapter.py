"""Fail-closed adapter for official gettex MUND/MUNC delayed pre-trade files."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from tempfile import SpooledTemporaryFile
from time import monotonic
from uuid import UUID

import httpx
from sqlalchemy import select

from app.core.config.gettex import GettexDelayedSettings
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
from app.features.market_data.persistence.quote_identity import QuoteIdentity, read_quote_identity
from app.features.market_data.service.errors import (
    MarketDataAuthorizationError,
    MarketDataInvalidResponseError,
    MarketDataNotFoundError,
    MarketDataUnavailableError,
)
from app.features.market_data.service.types import MarketDataResult, WarrantQuoteRequest
from app.providers.gettex_delayed.parser import GettexPayloadError, GettexQuoteRow, scan_gzip_quotes


@dataclass(frozen=True, slots=True)
class _CacheEntry:
    file_name: str
    quotes: dict[str, GettexQuoteRow]
    retrieved_at: datetime


class GettexDelayedWarrantQuoteAdapter:
    """Read delayed gettex quotes only for explicitly validated MUND/MUNC mappings."""

    def __init__(
        self,
        *,
        database: DatabaseManager,
        settings: GettexDelayedSettings,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._database = database
        self._settings = settings
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=settings.timeout_seconds,
            follow_redirects=False,
        )
        self._lock = asyncio.Lock()
        self._cache: dict[tuple[UUID, str], _CacheEntry] = {}
        self._missing_until: dict[tuple[str, str], float] = {}

    async def close(self) -> None:
        """Close the HTTP client owned by this adapter."""
        if self._owns_client:
            await self._client.aclose()

    async def get_warrant_listing_quote(
        self, request: WarrantQuoteRequest
    ) -> MarketDataResult[WarrantQuoteSnapshot | None]:
        identity = await self._resolve_identity(request)
        if (
            request.expected_currency is not None
            and request.expected_currency.upper() != identity.currency
        ):
            raise MarketDataInvalidResponseError(
                "GETTEX_DELAYED_EXPECTED_CURRENCY_MISMATCH",
                provider=MarketDataProvider.GETTEX_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )
        quotes, retrieved_at, cache_hit = await self._quotes_for(
            request.workspace_id,
            identity.exchange,
            request.as_of,
        )
        row = quotes.get(identity.isin)
        quote = None
        if row is not None:
            if row.currency != identity.currency:
                raise MarketDataInvalidResponseError(
                    "GETTEX_DELAYED_CURRENCY_MISMATCH",
                    provider=MarketDataProvider.GETTEX_DELAYED,
                    capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
                )
            quote = WarrantQuoteSnapshot(
                warrant_listing_id=request.warrant_listing_id,
                bid=row.bid,
                ask=row.ask,
                currency=row.currency,
                provider_symbol=identity.isin,
                provider_exchange_code=identity.exchange,
                observed_at=row.observed_at,
                isin=identity.isin,
                wkn=identity.wkn,
                source_mode="OFFICIAL_DELAYED_PRETRADE",
                trading_status="UNKNOWN",
                assessed_at=datetime.now(UTC),
                feed_delay_seconds=self._settings.feed_delay_seconds,
                venue_mic=identity.mic,
                max_quote_age_seconds=request.max_quote_age_seconds,
            )

        return MarketDataResult(
            data=quote,
            provider=MarketDataProvider.GETTEX_DELAYED,
            capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            correlation_id=request.correlation_id,
            retrieved_at=retrieved_at,
            cache_status=CacheStatus.HIT if cache_hit else CacheStatus.BYPASS,
            quality_status=QualityStatus.VALID,
            warnings=(
                "Official gettex delayed pre-trade data; not a real-time executable quote",
                f"mic={identity.exchange}",
            ),
            retry_count=0,
            provider_call_cost=0,
        )

    async def _resolve_identity(self, request: WarrantQuoteRequest) -> QuoteIdentity:
        async with self._database.session_context() as session:
            identity = await read_quote_identity(
                session,
                request,
                MarketDataProvider.GETTEX_DELAYED,
            )
        if identity is None or identity.exchange not in {"MUND", "MUNC"}:
            raise MarketDataNotFoundError(
                "GETTEX_DELAYED_ACTIVE_MAPPING_NOT_FOUND",
                provider=MarketDataProvider.GETTEX_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            )
        return identity

    async def _tracked_isins(self, workspace_id: UUID, mic: str) -> set[str]:
        async with self._database.session_context() as session:
            values = (
                await session.scalars(
                    select(WarrantProviderMappingModel.provider_symbol).where(
                        WarrantProviderMappingModel.workspace_id == workspace_id,
                        WarrantProviderMappingModel.provider == MarketDataProvider.GETTEX_DELAYED,
                        WarrantProviderMappingModel.provider_exchange_code == mic,
                        WarrantProviderMappingModel.status == MappingStatus.ACTIVE,
                        WarrantProviderMappingModel.validated_at.is_not(None),
                    )
                )
            ).all()
        return {value.upper() for value in values}

    async def _quotes_for(
        self,
        workspace_id: UUID,
        mic: str,
        as_of: datetime,
    ) -> tuple[dict[str, GettexQuoteRow], datetime, bool]:
        async with self._lock:
            tracked_isins = await self._tracked_isins(workspace_id, mic)
            if not tracked_isins:
                raise MarketDataNotFoundError(
                    "GETTEX_DELAYED_NO_TRACKED_ISINS",
                    provider=MarketDataProvider.GETTEX_DELAYED,
                    capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
                )

            cache_key = (workspace_id, mic)
            for file_name in self._candidate_file_names(as_of, mic):
                cached = self._cache.get(cache_key)
                if cached is not None and cached.file_name == file_name:
                    return cached.quotes, cached.retrieved_at, True

                missing_key = (mic, file_name)
                if monotonic() < self._missing_until.get(missing_key, 0):
                    continue

                loaded = await self._download(file_name, tracked_isins)
                if loaded is None:
                    self._missing_until[missing_key] = (
                        monotonic() + self._settings.unavailable_retry_seconds
                    )
                    continue
                quotes, retrieved_at = loaded
                self._cache[cache_key] = _CacheEntry(
                    file_name=file_name,
                    quotes=quotes,
                    retrieved_at=retrieved_at,
                )
                return quotes, retrieved_at, False

        raise MarketDataNotFoundError(
            "GETTEX_DELAYED_RECENT_FILE_NOT_AVAILABLE",
            provider=MarketDataProvider.GETTEX_DELAYED,
            capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
            retryable=True,
        )

    def _candidate_file_names(self, as_of: datetime, mic: str) -> tuple[str, ...]:
        quarter_minute = (as_of.minute // 15) * 15
        latest_end = as_of.astimezone(UTC).replace(
            minute=quarter_minute,
            second=0,
            microsecond=0,
        )
        return tuple(
            f"pretrade.{(latest_end - timedelta(minutes=15 * offset)):%Y%m%d.%H.%M}."
            f"{mic.lower()}.csv.gz"
            for offset in range(self._settings.fallback_windows)
        )

    async def _download(
        self,
        file_name: str,
        tracked_isins: set[str],
    ) -> tuple[dict[str, GettexQuoteRow], datetime] | None:
        url = f"{self._settings.base_url.rstrip('/')}/{file_name}"
        try:
            async with self._client.stream(
                "GET",
                url,
                headers={"Accept": "application/gzip, application/octet-stream"},
            ) as response:
                if response.status_code == 404:
                    return None
                if response.status_code == 403:
                    raise MarketDataAuthorizationError(
                        "GETTEX_DELAYED_ACCESS_FORBIDDEN",
                        provider=MarketDataProvider.GETTEX_DELAYED,
                        capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
                    )
                if response.status_code >= 500:
                    raise MarketDataUnavailableError(
                        "GETTEX_DELAYED_UPSTREAM_UNAVAILABLE",
                        provider=MarketDataProvider.GETTEX_DELAYED,
                        capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
                        retryable=True,
                    )
                if response.status_code != 200:
                    raise MarketDataInvalidResponseError(
                        f"GETTEX_DELAYED_UNEXPECTED_HTTP_{response.status_code}",
                        provider=MarketDataProvider.GETTEX_DELAYED,
                        capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
                    )
                if str(response.url) != url:
                    raise MarketDataInvalidResponseError(
                        "GETTEX_DELAYED_REDIRECT_REJECTED",
                        provider=MarketDataProvider.GETTEX_DELAYED,
                        capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
                    )

                content_length = response.headers.get("Content-Length")
                if (
                    content_length is not None
                    and int(content_length) > self._settings.max_download_bytes
                ):
                    raise MarketDataInvalidResponseError(
                        "GETTEX_DELAYED_FILE_TOO_LARGE",
                        provider=MarketDataProvider.GETTEX_DELAYED,
                        capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
                    )

                with SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b") as temporary:
                    total = 0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > self._settings.max_download_bytes:
                            raise MarketDataInvalidResponseError(
                                "GETTEX_DELAYED_FILE_TOO_LARGE",
                                provider=MarketDataProvider.GETTEX_DELAYED,
                                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
                            )
                        temporary.write(chunk)
                    temporary.seek(0)
                    try:
                        quotes = await asyncio.to_thread(
                            scan_gzip_quotes,
                            temporary,
                            file_name=file_name,
                            tracked_isins=tracked_isins,
                        )
                    except GettexPayloadError as exc:
                        raise MarketDataInvalidResponseError(
                            str(exc),
                            provider=MarketDataProvider.GETTEX_DELAYED,
                            capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
                        ) from exc
        except httpx.TimeoutException as exc:
            raise MarketDataUnavailableError(
                "GETTEX_DELAYED_TIMEOUT",
                provider=MarketDataProvider.GETTEX_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
                retryable=True,
            ) from exc
        except httpx.RequestError as exc:
            raise MarketDataUnavailableError(
                "GETTEX_DELAYED_NETWORK_ERROR",
                provider=MarketDataProvider.GETTEX_DELAYED,
                capability=MarketDataCapability.WARRANT_LISTING_QUOTE,
                retryable=True,
            ) from exc
        return quotes, datetime.now(UTC)
