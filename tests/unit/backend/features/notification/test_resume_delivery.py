from __future__ import annotations

import httpx
import pytest
from pydantic import SecretStr

from app.features.notification.domain.models import DeliveryStatus
from app.features.notification.providers.telegram import (
    TelegramDeliveryAdapter,
    TelegramDeliveryConfig,
)
from app.tools.monitoring_resume import monitoring_checks


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [{"ok": False}, {"ok": True, "result": {}}, {"ok": True, "result": {"message_id": True}}, []],
)
async def test_http_200_is_not_delivery_confirmation(payload: object) -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    ) as client:
        adapter = TelegramDeliveryAdapter(
            config=TelegramDeliveryConfig(bot_token=SecretStr("fixture"), chat_id="123"),
            client=client,
        )
        result = await adapter.deliver(body="fixture")
    assert result.status is DeliveryStatus.FAILED
    assert result.provider_message_id is None


def test_flags_alone_do_not_prove_monitoring_cycle() -> None:
    runtime = {
        "enabled": True,
        "running": True,
        "telegram_enabled": True,
        "telegram_configured": True,
    }
    refresh = {"enabled": True, "leader": True, "settings": {"auto_select_position_sources": True}}
    assert not all(monitoring_checks(runtime, refresh).values())
    runtime.update(
        last_cycle_completed_at="2026-09-29T20:00:00Z", last_result={"notification_failures": 0}
    )
    assert all(monitoring_checks(runtime, refresh).values())
    runtime["last_result"] = {"notification_failures": 1}
    assert not all(monitoring_checks(runtime, refresh).values())


@pytest.mark.asyncio
async def test_preflight_rejects_different_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from app.tools import monitoring_resume as tool

    monkeypatch.setattr(
        tool,
        "get_settings",
        lambda: SimpleNamespace(
            notification=SimpleNamespace(telegram=SimpleNamespace(chat_id="123"))
        ),
    )
    call = AsyncMock(side_effect=[{"is_bot": True, "id": 1}, {"id": 999}])
    monkeypatch.setattr(tool, "telegram_call", call)
    with pytest.raises(ValueError, match="RECIPIENT_NOT_VERIFIED"):
        await tool.preflight()
    assert [c.args[1] for c in call.await_args_list] == ["getMe", "getChat"]


@pytest.mark.asyncio
async def test_smoke_does_not_send_when_running_cycle_is_unverified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unittest.mock import AsyncMock

    from app.tools import monitoring_resume as tool

    monkeypatch.setattr(
        tool, "verify", AsyncMock(return_value={"status": "ACTIVATION_NOT_VERIFIED"})
    )
    checked = AsyncMock()
    monkeypatch.setattr(tool, "preflight", checked)
    with pytest.raises(ValueError, match="TEST_NOT_SENT"):
        await tool.telegram_test()
    checked.assert_not_awaited()
