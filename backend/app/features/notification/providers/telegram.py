from __future__ import annotations

from dataclasses import dataclass

import httpx
from pydantic import SecretStr

from app.features.notification.domain.models import DeliveryResult, DeliveryStatus


@dataclass(frozen=True, slots=True)
class TelegramDeliveryConfig:
    bot_token: SecretStr
    chat_id: str
    base_url: str = "https://api.telegram.org"
    timeout_seconds: float = 10.0


class TelegramDeliveryAdapter:
    """Outbound-only Telegram Bot API adapter; contains no trading semantics."""

    def __init__(
        self,
        *,
        config: TelegramDeliveryConfig,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not config.chat_id.strip():
            raise ValueError("Telegram chat_id must not be blank")
        if not config.bot_token.get_secret_value().strip():
            raise ValueError("Telegram bot_token must not be blank")
        self._config = config
        self._client = client

    async def deliver(self, *, body: str) -> DeliveryResult:
        endpoint = (
            f"{self._config.base_url.rstrip('/')}/bot"
            f"{self._config.bot_token.get_secret_value()}/sendMessage"
        )
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._config.timeout_seconds)
        try:
            response = await client.post(
                endpoint,
                json={
                    "chat_id": self._config.chat_id,
                    "text": body,
                    "disable_web_page_preview": True,
                },
            )
            if response.status_code == 429:
                return DeliveryResult(
                    status=DeliveryStatus.FAILED,
                    retryable=True,
                    error_code="TELEGRAM_RATE_LIMIT",
                    error_message="Telegram rate limit exceeded",
                )
            if response.status_code >= 500:
                return DeliveryResult(
                    status=DeliveryStatus.FAILED,
                    retryable=True,
                    error_code=f"TELEGRAM_HTTP_{response.status_code}",
                    error_message="Telegram server error",
                )
            if response.status_code >= 400:
                return DeliveryResult(
                    status=DeliveryStatus.FAILED,
                    retryable=False,
                    error_code=f"TELEGRAM_HTTP_{response.status_code}",
                    error_message="Telegram rejected delivery request",
                )
            payload = response.json()
            message_id = payload.get("result", {}).get("message_id")
            return DeliveryResult(
                status=DeliveryStatus.DELIVERED,
                retryable=False,
                provider_message_id=str(message_id) if message_id is not None else None,
            )
        except (httpx.TimeoutException, httpx.NetworkError):
            return DeliveryResult(
                status=DeliveryStatus.FAILED,
                retryable=True,
                error_code="TELEGRAM_TRANSPORT_ERROR",
                error_message="Telegram transport failed",
            )
        finally:
            if owns_client:
                await client.aclose()
