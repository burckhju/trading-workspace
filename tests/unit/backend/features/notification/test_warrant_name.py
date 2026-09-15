"""Synthetic product identities in the persisted, plain-text Telegram message."""

import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr
from tests.unit.backend.features.notification.test_creation import Repo

from app.features.alert.domain.models import Alert, AlertSeverity, AlertType
from app.features.notification.domain.models import DeliveryStatus
from app.features.notification.providers.telegram import (
    TelegramDeliveryAdapter,
    TelegramDeliveryConfig,
)
from app.features.notification.service.creation import AlertNotificationService
from app.features.notification.service.formatter import format_position_alert

NOW = datetime(2026, 9, 14, 10, tzinfo=UTC)
NAME = "SYNTHETIC Musterbank Call auf Beispiel AG 120 2028"
ISIN = "DE000SYN0010"
WKN = "SYN001"


def alert(kind: AlertType = AlertType.TARGET_REACHED) -> Alert:
    return Alert(
        id=uuid4(),
        position_id=uuid4(),
        trade_id=uuid4(),
        alert_type=kind,
        severity=AlertSeverity.INFO,
        rule_key="synthetic-rule",
        reason="threshold reached",
        observed_value=Decimal("121"),
        threshold_value=Decimal("120"),
        market_data_observed_at=NOW,
        detected_at=NOW,
        price_context={
            "basis": "UNDERLYING",
            "currency": "USD",
            "price_type": "DAILY_HIGH",
            "provider": "SYNTHETIC",
            "provider_identity": "EXAMPLE.US",
            "observed_at": NOW.isoformat(),
            "warning": "INDICATIVE_REFERENCE_PRICE",
        },
    )


@pytest.mark.parametrize("kind", list(AlertType))
def test_product_name_does_not_replace_price_basis_or_warning(kind: AlertType) -> None:
    value = alert(kind)
    body = format_position_alert(
        value, symbol="EXAMPLE", warrant_name=NAME, warrant_isin=ISIN, warrant_wkn=WKN
    )
    assert body.splitlines()[:3] == [
        "Position Alert",
        f"Optionsschein: {NAME}",
        f"WKN: {WKN} | ISIN: {ISIN}",
    ]
    assert "EXAMPLE\n" in body
    assert ("Stop erreicht" if kind is AlertType.STOP_REACHED else "Target erreicht") in body
    for text in (
        "Kursbezug: UNDERLYING",
        "Währung: USD",
        "Kursart: DAILY_HIGH",
        "Quelle: SYNTHETIC",
        "Provider-ID: EXAMPLE.US",
        f"Kurszeitpunkt: {NOW.isoformat()}",
        "Hinweis: INDICATIVE_REFERENCE_PRICE",
        "Keine Orderfreigabe.",
        "Kurs: 121",
        "Schwelle: 120",
    ):
        assert text in body
    assert value.price_context["basis"] == "UNDERLYING"


@pytest.mark.parametrize("name", [None, "", " \t\n"])
def test_missing_name_is_explicit_and_not_the_underlying_symbol(name: str | None) -> None:
    body = format_position_alert(
        alert(), symbol="EXAMPLE", warrant_name=name, warrant_isin=ISIN, warrant_wkn=WKN
    )
    assert "Optionsschein: Name nicht verfügbar\n" in body
    assert f"WKN: {WKN} | ISIN: {ISIN}" in body
    assert "Optionsschein: EXAMPLE" not in body


def test_legacy_caller_without_identity_remains_supported() -> None:
    body = format_position_alert(alert(), symbol="EXAMPLE")
    assert "Optionsschein: Name nicht verfügbar\n" in body
    assert "WKN: — | ISIN: —\n" in body
    assert "None" not in body


def test_identity_fields_are_single_line_without_interpreting_markup() -> None:
    name = "  SYNTHETIC\nBank\t<A&B> [Call]_2028* 🚀  "
    body = format_position_alert(
        alert(), symbol="EXAMPLE", warrant_name=name, warrant_isin=f" {ISIN}\n", warrant_wkn=WKN
    )
    assert body.splitlines()[1] == "Optionsschein: SYNTHETIC Bank <A&B> [Call]_2028* 🚀"
    assert body.splitlines()[2] == f"WKN: {WKN} | ISIN: {ISIN}"


def test_full_valid_length_name_is_retained() -> None:
    name = "SYNTHETIC " + "Ä" * 190
    body = format_position_alert(
        alert(), symbol="EXAMPLE", warrant_name=name, warrant_isin=ISIN, warrant_wkn=WKN
    )
    assert name in body
    assert len(body) < 4096


@pytest.mark.asyncio
async def test_name_is_snapshotted_once_and_rename_does_not_recreate_notification() -> None:
    repo = Repo()
    service = AlertNotificationService(notifications=repo, new_id=uuid4, now=lambda: NOW)
    value = alert()
    first = await service.create_telegram(
        alert=value, symbol="EXAMPLE", warrant_name=NAME, warrant_isin=ISIN, warrant_wkn=WKN
    )
    repeated = await service.create_telegram(
        alert=value, symbol="EXAMPLE", warrant_name="SYNTHETIC Renamed", warrant_isin=ISIN
    )
    assert repeated is first
    assert len(repo.values) == 1
    assert NAME in first.body
    assert "Renamed" not in repeated.body


@pytest.mark.asyncio
async def test_real_adapter_sends_product_text_as_plain_json_without_network() -> None:
    body = format_position_alert(
        alert(),
        symbol="EXAMPLE",
        warrant_name="SYNTHETIC <A&B> [Call]_2028* 🚀",
        warrant_isin=ISIN,
        warrant_wkn=WKN,
    )
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        requests.append(payload)
        assert payload["text"] == body
        assert "parse_mode" not in payload
        assert "entities" not in payload
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 42}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = TelegramDeliveryAdapter(
            config=TelegramDeliveryConfig(bot_token=SecretStr("synthetic-token"), chat_id="test"),
            client=client,
        )
        result = await adapter.deliver(body=body)
    assert result.status is DeliveryStatus.DELIVERED
    assert len(requests) == 1
