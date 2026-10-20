"""Verify the running scheduler and the already-configured Telegram destination."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import UTC, datetime
from time import monotonic
from typing import Any

import httpx

from app.core.config import get_settings
from app.features.notification.domain.models import DeliveryStatus
from app.features.notification.providers.telegram import (
    TelegramDeliveryAdapter,
    TelegramDeliveryConfig,
)

# JSON envelopes returned by provider/API: values are validated before use.
Json = dict[str, Any]


async def telegram_call(client: httpx.AsyncClient, method: str, params: Json | None = None) -> Json:
    settings = get_settings().notification.telegram
    if settings.bot_token is None or not settings.chat_id:
        raise ValueError("TELEGRAM_CONFIGURATION_MISSING")
    if settings.base_url.rstrip("/") != "https://api.telegram.org":
        raise ValueError("TELEGRAM_DESTINATION_HOST_UNEXPECTED")
    token = settings.bot_token.get_secret_value()
    response = await client.post(
        f"{settings.base_url.rstrip('/')}/bot{token}/{method}", json=params or {}
    )
    if response.status_code != 200:
        raise ValueError("TELEGRAM_PREFLIGHT_HTTP_ERROR")
    payload = response.json()
    if (
        not isinstance(payload, dict)
        or payload.get("ok") is not True
        or not isinstance(payload.get("result"), dict)
    ):
        raise ValueError("TELEGRAM_PREFLIGHT_UNCONFIRMED")
    result = payload["result"]
    assert isinstance(result, dict)  # Validated in the envelope check above.
    return result


async def preflight() -> Json:
    settings = get_settings()
    target = settings.notification.telegram.chat_id
    async with httpx.AsyncClient(timeout=15, trust_env=False, follow_redirects=False) as client:
        bot = await telegram_call(client, "getMe")
        chat = await telegram_call(client, "getChat", {"chat_id": target})
    matches = str(chat.get("id")) == target or (
        isinstance(target, str)
        and target.startswith("@")
        and str(chat.get("username", "")).casefold() == target[1:].casefold()
    )
    if bot.get("is_bot") is not True or not matches:
        raise ValueError("TELEGRAM_CONFIGURED_RECIPIENT_NOT_VERIFIED")
    return {
        "status": "PREFLIGHT_OK",
        "read_only": True,
        "telegram_bot_verified": True,
        "configured_recipient_verified": True,
        "message_sent": False,
        "note": "WRITE_PERMISSION_IS_PROVED_ONLY_BY_A_CONFIRMED_SEND",
    }


def monitoring_checks(runtime: Json, refresh: Json) -> dict[str, bool]:
    result = runtime.get("last_result") or {}
    return {
        "monitoring_enabled": runtime.get("enabled") is True,
        "monitoring_running": runtime.get("running") is True,
        "completed_cycle": bool(runtime.get("last_cycle_completed_at")),
        "cycle_without_runtime_error": runtime.get("last_error") is None,
        "telegram_enabled_in_running_process": runtime.get("telegram_enabled") is True,
        "telegram_configured_in_running_process": runtime.get("telegram_configured") is True,
        "completed_cycle_without_delivery_failure": result.get("notification_failures") == 0,
        "refresh_enabled": refresh.get("enabled") is True,
        "refresh_leader": refresh.get("leader") is True,
        "automatic_source_selection": refresh.get("settings", {}).get(
            "auto_select_position_sources"
        )
        is True,
    }


async def verify(wait_seconds: int) -> Json:
    deadline = monotonic() + wait_seconds
    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:8000", timeout=15, trust_env=False
    ) as client:
        while True:
            monitoring = await client.get("/api/v1/position-monitoring/runtime/status")
            refresh = await client.get("/api/v1/market-data/refresh/status")
            monitoring.raise_for_status()
            refresh.raise_for_status()
            runtime, market = monitoring.json(), refresh.json()
            checks = monitoring_checks(runtime, market)
            if all(checks.values()) or monotonic() >= deadline or runtime.get("enabled") is False:
                break
            print("Warte auf bestätigten Überwachungszyklus ...", file=sys.stderr, flush=True)
            await asyncio.sleep(min(5, max(0, deadline - monotonic())))
    return {
        "schema_version": "MONITORING_RESUME_V1",
        "read_only": True,
        "status": "MONITORING_ACTIVE" if all(checks.values()) else "ACTIVATION_NOT_VERIFIED",
        "checks": checks,
        "monitoring": runtime,
        "checked_at": datetime.now(UTC).isoformat(),
        "coverage_note": "ACTIVE_SCHEDULER_DOES_NOT_MEAN_ALL_POSITIONS_HAVE_USABLE_QUOTES",
    }


async def telegram_test() -> Json:
    active = await verify(0)
    if active["status"] != "MONITORING_ACTIVE":
        raise ValueError("MONITORING_NOT_VERIFIED_TEST_NOT_SENT")
    await preflight()
    telegram = get_settings().notification.telegram
    assert telegram.bot_token is not None and telegram.chat_id is not None
    adapter = TelegramDeliveryAdapter(
        config=TelegramDeliveryConfig(
            bot_token=telegram.bot_token,
            chat_id=telegram.chat_id,
            base_url=telegram.base_url,
            timeout_seconds=telegram.timeout_seconds,
        )
    )
    result = await adapter.deliver(
        body=(
            "Trading-Workspace: Überwachung und Telegram-Versand sind wieder aktiviert. "
            "Dies ist eine technische Testnachricht. Fehlende Kursquellen einzelner Produkte "
            "bleiben separat gekennzeichnet."
        )
    )
    return {
        "status": (
            "TELEGRAM_TEST_CONFIRMED"
            if result.status is DeliveryStatus.DELIVERED
            else "TELEGRAM_TEST_NOT_CONFIRMED"
        ),
        "read_only": False,
        "message_sent": result.status is DeliveryStatus.DELIVERED,
        "provider_message_id": result.provider_message_id,
        "error_code": result.error_code,
        "checked_at": datetime.now(UTC).isoformat(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "verify", "telegram-test"))
    parser.add_argument("--wait-seconds", type=int, default=0)
    args = parser.parse_args()
    if not 0 <= args.wait_seconds <= 600:
        parser.error("wait-seconds must be between 0 and 600")
    # Bot tokens appear in Bot API URLs; never allow httpx request logging here.
    logging.getLogger("httpx").setLevel(logging.CRITICAL)
    logging.getLogger("httpcore").setLevel(logging.CRITICAL)
    try:
        action = (
            preflight()
            if args.action == "preflight"
            else telegram_test() if args.action == "telegram-test" else verify(args.wait_seconds)
        )
        result = asyncio.run(action)
    except Exception as exc:
        result = {"status": "OPERATION_NOT_CONFIRMED", "error_type": type(exc).__name__}
        if isinstance(exc, ValueError) and str(exc).startswith(("TELEGRAM_", "MONITORING_")):
            result["reason"] = str(exc)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result["status"] not in {"PREFLIGHT_OK", "MONITORING_ACTIVE", "TELEGRAM_TEST_CONFIRMED"}:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
