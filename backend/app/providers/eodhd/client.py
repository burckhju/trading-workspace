"""Asynchronous HTTP transport for EODHD without domain mapping."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import httpx
from pydantic import SecretStr

from app.core.config.settings import EodhdSettings
from app.features.market_data.domain.enums import MarketDataCapability, MarketDataProvider
from app.features.market_data.service.errors import (
    MarketDataAuthenticationError,
    MarketDataAuthorizationError,
    MarketDataConfigurationError,
    MarketDataInvalidResponseError,
    MarketDataNotFoundError,
    MarketDataRateLimitError,
    MarketDataTimeoutError,
    MarketDataUnavailableError,
)


class EodhdClient:
    """Execute authenticated EODHD GET requests and translate transport failures."""

    def __init__(self, *, settings: EodhdSettings, client: httpx.AsyncClient) -> None:
        self._settings = settings
        self._client = client

    async def get_json(
        self,
        path: str,
        *,
        capability: MarketDataCapability,
        params: dict[str, object] | None = None,
    ) -> Any:
        """Return decoded JSON or raise a provider-independent market-data error."""
        api_key = self._required_api_key()
        query: dict[str, object] = dict(params or {})
        query["api_token"] = api_key.get_secret_value()
        query.setdefault("fmt", "json")
        try:
            response = await self._client.get(path, params=query)
        except httpx.TimeoutException as exc:
            raise MarketDataTimeoutError(
                "EODHD request timed out",
                provider=MarketDataProvider.EODHD,
                capability=capability,
                retryable=True,
            ) from exc
        except httpx.NetworkError as exc:
            raise MarketDataUnavailableError(
                "EODHD network request failed",
                provider=MarketDataProvider.EODHD,
                capability=capability,
                retryable=True,
            ) from exc
        self._raise_for_status(response, capability=capability)
        try:
            return response.json()
        except ValueError as exc:
            raise MarketDataInvalidResponseError(
                "EODHD returned invalid JSON",
                provider=MarketDataProvider.EODHD,
                capability=capability,
                retryable=False,
            ) from exc

    def _required_api_key(self) -> SecretStr:
        if not self._settings.enabled:
            raise MarketDataConfigurationError(
                "EODHD provider is disabled", provider=MarketDataProvider.EODHD
            )
        if self._settings.api_key is None:
            raise MarketDataConfigurationError(
                "EODHD API key is not configured", provider=MarketDataProvider.EODHD
            )
        return self._settings.api_key

    @staticmethod
    def _retry_after(response: httpx.Response) -> timedelta | None:
        raw = response.headers.get("Retry-After")
        if raw is None:
            return None
        try:
            seconds = max(int(raw), 0)
        except ValueError:
            return None
        return timedelta(seconds=seconds)

    @classmethod
    def _raise_for_status(
        cls, response: httpx.Response, *, capability: MarketDataCapability
    ) -> None:
        common = {"provider": MarketDataProvider.EODHD, "capability": capability}
        status = response.status_code
        if 200 <= status < 300:
            return
        if status == 401:
            raise MarketDataAuthenticationError("EODHD rejected credentials", **common)
        if status == 403:
            raise MarketDataAuthorizationError("EODHD access is not permitted", **common)
        if status == 404:
            raise MarketDataNotFoundError("EODHD resource was not found", **common)
        if status == 429:
            raise MarketDataRateLimitError(
                "EODHD rate limit exceeded",
                retryable=True,
                retry_after=cls._retry_after(response),
                **common,
            )
        if status in {408, 425, 500, 502, 503, 504}:
            raise MarketDataUnavailableError(
                "EODHD is temporarily unavailable",
                retryable=True,
                retry_after=cls._retry_after(response),
                **common,
            )
        raise MarketDataInvalidResponseError(
            f"EODHD returned unexpected HTTP status {status}", retryable=False, **common
        )


def create_http_client(settings: EodhdSettings) -> httpx.AsyncClient:
    """Create a bounded HTTPX client for the EODHD transport boundary."""
    timeout = httpx.Timeout(
        connect=settings.connect_timeout_seconds,
        read=settings.read_timeout_seconds,
        write=settings.write_timeout_seconds,
        pool=settings.pool_timeout_seconds,
    )
    return httpx.AsyncClient(base_url=settings.base_url, timeout=timeout)
