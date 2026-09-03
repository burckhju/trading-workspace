import httpx
import pytest
from pydantic import SecretStr

from app.features.notification.domain.models import DeliveryStatus
from app.features.notification.providers.telegram import (
    TelegramDeliveryAdapter,
    TelegramDeliveryConfig,
)


@pytest.mark.asyncio
async def test_telegram_adapter_maps_success_without_real_network() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/sendMessage")
        assert b'"chat_id":"123"' in request.content
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 42}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = TelegramDeliveryAdapter(
            config=TelegramDeliveryConfig(bot_token=SecretStr("test-token"), chat_id="123"),
            client=client,
        )
        result = await adapter.deliver(body="hello")

    assert result.status is DeliveryStatus.DELIVERED
    assert result.provider_message_id == "42"


@pytest.mark.asyncio
async def test_telegram_rate_limit_is_retryable() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"ok": False})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = TelegramDeliveryAdapter(
            config=TelegramDeliveryConfig(bot_token=SecretStr("test-token"), chat_id="123"),
            client=client,
        )
        result = await adapter.deliver(body="hello")

    assert result.status is DeliveryStatus.FAILED
    assert result.retryable is True
    assert result.error_code == "TELEGRAM_RATE_LIMIT"
