"""Tests for the EODHD HTTP transport boundary."""

from datetime import timedelta

import httpx
import pytest
from pydantic import SecretStr

from app.core.config.settings import EodhdSettings
from app.features.market_data.domain.enums import MarketDataCapability
from app.features.market_data.service.errors import (
    MarketDataAuthenticationError,
    MarketDataConfigurationError,
    MarketDataInvalidResponseError,
    MarketDataRateLimitError,
    MarketDataTimeoutError,
    MarketDataUnavailableError,
)
from app.providers.eodhd.client import EodhdClient

CAPABILITY = MarketDataCapability.HISTORICAL_DAILY_PRICES


def settings(**overrides: object) -> EodhdSettings:
    values: dict[str, object] = {"enabled": True, "api_key": SecretStr("top-secret")}
    values.update(overrides)
    return EodhdSettings(**values)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_client_adds_credentials_without_exposing_them_in_result() -> None:
    seen_url = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_url
        seen_url = str(request.url)
        return httpx.Response(200, json=[{"date": "2026-08-04"}])

    async with httpx.AsyncClient(
        base_url="https://eodhd.test/api", transport=httpx.MockTransport(handler)
    ) as http:
        result = await EodhdClient(settings=settings(), client=http).get_json(
            "/eod/SAP.XETRA", capability=CAPABILITY, params={"from": "2026-08-01"}
        )
    assert result == [{"date": "2026-08-04"}]
    assert "api_token=top-secret" in seen_url
    assert "fmt=json" in seen_url


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "error_type", "retryable"),
    [
        (401, MarketDataAuthenticationError, False),
        (429, MarketDataRateLimitError, True),
        (503, MarketDataUnavailableError, True),
        (418, MarketDataInvalidResponseError, False),
    ],
)
async def test_client_translates_statuses(
    status: int, error_type: type[Exception], retryable: bool
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status, headers={"Retry-After": "7"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(error_type) as exc_info:
            await EodhdClient(settings=settings(), client=http).get_json(
                "https://eodhd.test/api/eod/SAP", capability=CAPABILITY
            )
    assert getattr(exc_info.value, "retryable") is retryable
    if status in {429, 503}:
        assert getattr(exc_info.value, "retry_after") == timedelta(seconds=7)


@pytest.mark.asyncio
async def test_client_translates_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(MarketDataTimeoutError) as exc_info:
            await EodhdClient(settings=settings(), client=http).get_json(
                "https://eodhd.test/api/eod/SAP", capability=CAPABILITY
            )
    assert exc_info.value.retryable is True


@pytest.mark.asyncio
async def test_client_rejects_disabled_or_missing_credentials_before_request() -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        for config in (settings(enabled=False), settings(api_key=None)):
            with pytest.raises(MarketDataConfigurationError):
                await EodhdClient(settings=config, client=http).get_json(
                    "https://eodhd.test/api/eod/SAP", capability=CAPABILITY
                )
    assert calls == 0


@pytest.mark.asyncio
async def test_client_rejects_invalid_json() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-json")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(MarketDataInvalidResponseError):
            await EodhdClient(settings=settings(), client=http).get_json(
                "https://eodhd.test/api/eod/SAP", capability=CAPABILITY
            )
