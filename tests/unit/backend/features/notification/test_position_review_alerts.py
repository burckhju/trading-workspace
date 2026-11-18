"""Separate review notices, nullable non-price values and terminal delivery decisions."""

from dataclasses import replace
from datetime import timedelta
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from tests.unit.backend.features.notification.test_hebeltrader_b04 import (
    NOW,
    executions,
    store_fixture,
)
from tests.unit.backend.features.notification.test_warrant_name import ISIN, NAME, WKN, alert

from app.features.alert.domain.models import AlertType
from app.features.notification.domain.models import DeliveryResult, DeliveryStatus
from app.features.notification.persistence.models import NotificationDeliveryAttemptModel
from app.features.notification.service.formatter import format_position_alert
from app.features.notification.service.hebeltrader_lifecycle import (
    suppress_pending_review_notifications,
)
from app.features.trade_position.persistence.repositories import (
    SqlAlchemyExecutionRecordRepository,
)

REVIEW_TYPES = (
    AlertType.INDICATIVE_ENTRY_LOSS,
    AlertType.POSITION_REVIEW_DUE,
    AlertType.POSITION_DATA_UNAVAILABLE,
)
NON_PRICE_TYPES = REVIEW_TYPES[1:]
VERSION = "synthetic-position-review-v1"


def review_alert(kind):
    priced = kind is AlertType.INDICATIVE_ENTRY_LOSS
    return replace(
        alert(kind),
        observed_value=Decimal("0.48") if priced else None,
        threshold_value=Decimal("0.55") if priced else None,
        market_data_observed_at=NOW if priced else None,
        detected_at=NOW,
        reason="Synthetische Prüfgrundlage; keine B58-Quellenqualifikation.",
        price_context={
            "basis": "WARRANT",
            "currency": "EUR",
            "provider": "SYNTHETIC",
            "evaluation_mode": "SOURCE_BID" if priced else None,
            "observed_at": NOW.isoformat() if priced else None,
            "retrieved_at": (NOW + timedelta(seconds=1)).isoformat() if priced else None,
            "rule_version": VERSION,
            "remaining_quantity": "10",
            "completed_sessions": "19" if kind is AlertType.POSITION_REVIEW_DUE else "20",
            "session_count_at": NOW.isoformat(),
            "review_completed_sessions": "20",
            "review_session_count_at": (NOW + timedelta(minutes=1)).isoformat(),
        },
    )


@pytest.mark.parametrize("kind", REVIEW_TYPES)
def test_review_formatter_keeps_identity_version_and_explicit_non_b04_scope(kind):
    item = review_alert(kind)
    body = format_position_alert(
        item, symbol=ISIN, warrant_name=NAME, warrant_isin=ISIN, warrant_wkn=WKN
    )
    for expected in (NAME, WKN, ISIN, VERSION, "SYNTHETIC", item.reason, NOW.isoformat()):
        assert expected in body
    assert "keine qualifizierte B04/B57-Bewertung" in body
    assert "Keine Order" in body and "keine automatische Stop- oder Zieländerung" in body
    assert "None" not in body
    assert "Abgeschlossene Basiswertsitzungen: 20" in body
    count_at = NOW + timedelta(minutes=1) if kind is AlertType.POSITION_REVIEW_DUE else NOW
    assert f"Bezug der Sitzungszählung: {count_at.isoformat()}" in body
    if kind is AlertType.INDICATIVE_ENTRY_LOSS:
        assert "BID-Indikation: 0.48 EUR" in body
        assert "Bruttoeinstand je Stück: 0.55 EUR" in body
        assert "Marktöffnung nicht B58-qualifiziert" in body
    else:
        assert "keinen Kursverlust und keine Erholung" in body
        for invented_price in ("BID-Indikation:", "Kurs:", "Schwelle:", "Bruttoeinstand je Stück:"):
            assert invented_price not in body
        assert "0.48" not in body and "0.55" not in body


def test_delayed_v2_notice_exposes_shared_clock_and_assumptions_without_original_bid_time():
    item = review_alert(AlertType.INDICATIVE_ENTRY_LOSS)
    shared_at = NOW - timedelta(minutes=17)
    item = replace(
        item,
        market_data_observed_at=None,
        price_context={
            **item.price_context,
            "rule_version": "indicative-entry-review-v2",
            "evaluation_mode": "DELAYED_SOURCE_BID",
            "observed_at": None,
            "source_quote_at": shared_at.isoformat(),
            "history_continuity_assumed": "true",
            "calendar_quality": "CURRENT_DOCUMENT_REFERENCE_MARKET_ASSUMED",
            "session_day_precision": "CONSERVATIVE_DATE_BOUND",
        },
    )
    body = format_position_alert(item, symbol=ISIN)
    assert f"Gemeinsame Quellkurszeit: {shared_at.isoformat()}" in body
    assert "Original-Geldkurszeit: —" in body
    assert "Alterslimit 30 Minuten" in body
    assert "angenommen und nicht unabhängig verifiziert" in body
    assert "historische persönliche Listingbindung nicht verifiziert" in body
    assert "Sitzungszahl konservativ" in body


def test_issuer_indication_never_turns_recent_receipt_into_original_price_time():
    item = review_alert(AlertType.INDICATIVE_ENTRY_LOSS)
    item = replace(
        item,
        market_data_observed_at=None,
        price_context={
            **item.price_context,
            "observed_at": None,
            "evaluation_mode": "INDICATIVE_ISSUER",
            "quote_time_text": "SYNTHETIC 12:00, datumlose Quellenangabe",
        },
    )
    body = format_position_alert(item, symbol=ISIN)
    assert "Original-Geldkurszeit: —" in body
    assert f"Abgerufen: {(NOW + timedelta(seconds=1)).isoformat()}" in body
    assert "Originalkurszeit und Kursfrische unbekannt" in body
    assert "Empfangszeit ist keine Originalkurszeit" in body
    assert "Sitzungszahl zur Original-BID-Zeit" not in body
    assert "None" not in body


@pytest.mark.parametrize("kind", REVIEW_TYPES)
def test_missing_review_metadata_does_not_invent_price_identity_or_version(kind):
    body = format_position_alert(replace(review_alert(kind), price_context=None), symbol=ISIN)
    assert "Regelversion: —" in body
    assert "WKN: — | ISIN: —" in body
    assert "None" not in body
    if kind is AlertType.INDICATIVE_ENTRY_LOSS:
        assert "Zeitbezug der Preisindikation nicht belegt" in body
        assert "Sitzungszahl zur Original-BID-Zeit" not in body


@pytest.mark.parametrize("kind", NON_PRICE_TYPES)
@pytest.mark.parametrize("observed,threshold", [(0, None), (None, 0), (0, 0)])
def test_non_price_review_refuses_numeric_placeholders(kind, observed, threshold):
    item = replace(review_alert(kind), observed_value=observed, threshold_value=threshold)
    with pytest.raises(ValueError, match="Non-price"):
        format_position_alert(item, symbol=ISIN)


@pytest.mark.parametrize("observed,threshold", [(None, Decimal("0.55")), (Decimal("0.48"), None)])
def test_indicative_loss_cannot_render_without_both_comparable_values(observed, threshold):
    item = replace(
        review_alert(AlertType.INDICATIVE_ENTRY_LOSS),
        observed_value=observed,
        threshold_value=threshold,
    )
    with pytest.raises(ValueError, match="BID and gross entry"):
        format_position_alert(item, symbol=ISIN)


def delivery_fixture(kind, **kwargs):
    fixture = store_fixture(**kwargs)
    fixture.alert.alert_type = kind.value
    fixture.notification.body = "Synthetic separate review; no B04 and no external delivery"
    return fixture


@pytest.mark.parametrize("kind", REVIEW_TYPES)
@pytest.mark.parametrize(
    "status,cancelled,code",
    [
        ("RESOLVED", False, "REVIEW_ALERT_RESOLVED"),
        ("INVALIDATED", False, "REVIEW_ALERT_INVALIDATED"),
        ("OPEN", True, "REVIEW_TRADE_CANCELLED"),
    ],
)
async def test_terminal_review_state_persists_reason_before_any_external_call(
    kind, status, cancelled, code
):
    fixture = delivery_fixture(kind, alert_status=status, cancelled=cancelled)
    fixture.session.scalar.side_effect = [
        fixture.trade.id,
        fixture.trade,
        fixture.notification,
        fixture.alert,
        None,
    ]
    result = await fixture.delivery.deliver(fixture.notification.id)
    assert result.status is DeliveryStatus.FAILED and not result.retryable
    assert result.error_code == code
    assert fixture.notification.status == "FAILED"
    terminal = fixture.session.add.call_args.args[0]
    assert terminal.error_code == code and terminal.attempt_number == 1
    assert terminal.status == "FAILED" and terminal.completed_at == NOW
    assert terminal.provider_message_id is None and not terminal.retryable
    fixture.adapter.deliver.assert_not_awaited()
    fixture.session.commit.assert_awaited_once()


@pytest.mark.parametrize("kind", REVIEW_TYPES)
async def test_full_sale_reuses_effective_owner_and_terminal_replay_keeps_history(
    kind, monkeypatch
):
    fixture = delivery_fixture(kind)
    owner = AsyncMock(return_value=executions(fixture.trade))
    monkeypatch.setattr(SqlAlchemyExecutionRecordRepository, "list_effective_for_trade", owner)
    fixture.session.scalar.side_effect = [
        fixture.trade.id,
        fixture.trade,
        fixture.notification,
        fixture.alert,
        2,
    ]
    result = await fixture.delivery.deliver(fixture.notification.id)
    assert result.error_code == "REVIEW_POSITION_CLOSED" and not result.retryable
    owner.assert_awaited_once_with(fixture.trade.id)
    terminal = fixture.session.add.call_args.args[0]
    assert terminal.attempt_number == 3
    trade_lock = fixture.session.scalar.call_args_list[1].args[0]
    assert "FOR UPDATE" in str(trade_lock) and "trades" in str(trade_lock)
    fixture.session.scalar.side_effect = [
        fixture.trade.id,
        fixture.trade,
        fixture.notification,
        fixture.alert,
        terminal,
    ]
    assert await fixture.delivery.deliver(fixture.notification.id) == result
    fixture.session.add.assert_called_once()
    fixture.adapter.deliver.assert_not_awaited()


@pytest.mark.parametrize("kind", REVIEW_TYPES)
async def test_delivered_review_history_is_not_rewritten_after_resolution(kind):
    fixture = delivery_fixture(kind, alert_status="RESOLVED", notification_status="DELIVERED")
    fixture.session.scalar.side_effect = [
        fixture.trade.id,
        fixture.trade,
        fixture.notification,
        fixture.alert,
    ]
    result = await fixture.delivery.deliver(fixture.notification.id)
    assert result.status is DeliveryStatus.DELIVERED
    assert fixture.notification.status == "DELIVERED"
    fixture.session.add.assert_not_called()
    fixture.adapter.deliver.assert_not_awaited()


@pytest.mark.parametrize("kind", REVIEW_TYPES)
async def test_review_helper_leaves_transaction_boundary_with_the_economic_caller(kind):
    fixture = delivery_fixture(kind)
    fixture.session.scalar.side_effect = [kind.value, 4]
    fixture.session.scalars.return_value = [fixture.notification]
    assert (
        await suppress_pending_review_notifications(
            fixture.session,
            alert_id=fixture.alert.id,
            now=NOW,
            reason="REVIEW_ALERT_RESOLVED",
        )
        == 1
    )
    assert fixture.notification.status == "FAILED"
    assert fixture.session.add.call_args.args[0].attempt_number == 5
    fixture.session.commit.assert_not_awaited()
    fixture.adapter.deliver.assert_not_awaited()


@pytest.mark.parametrize("kind", [AlertType.HEBELTRADER_B04_LOSS, AlertType.STOP_REACHED])
async def test_review_helper_cannot_suppress_a_different_rule_family(kind):
    fixture = store_fixture()
    fixture.session.scalar.return_value = kind.value
    with pytest.raises(ValueError, match="review alert"):
        await suppress_pending_review_notifications(
            fixture.session,
            alert_id=fixture.alert.id,
            now=NOW,
            reason="REVIEW_ALERT_RESOLVED",
        )
    fixture.session.scalars.assert_not_awaited()
    fixture.session.add.assert_not_called()


async def test_review_helper_rejects_a_b04_reason_even_for_a_review_alert():
    fixture = delivery_fixture(AlertType.INDICATIVE_ENTRY_LOSS)
    fixture.session.scalar.return_value = AlertType.INDICATIVE_ENTRY_LOSS.value
    with pytest.raises(ValueError, match="review suppression reason"):
        await suppress_pending_review_notifications(
            fixture.session,
            alert_id=fixture.alert.id,
            now=NOW,
            reason="B04_ALERT_RESOLVED",
        )
    fixture.session.scalars.assert_not_awaited()
    fixture.session.add.assert_not_called()


@pytest.mark.parametrize("kind", REVIEW_TYPES)
async def test_late_retryable_result_preserves_review_suppression_and_actual_attempt(kind):
    fixture = delivery_fixture(kind, notification_status="FAILED")
    attempt = NotificationDeliveryAttemptModel(
        id=uuid4(),
        notification_id=fixture.notification.id,
        attempt_number=1,
        status="IN_PROGRESS",
        attempted_at=NOW,
        retryable=True,
    )
    fixture.session.scalar.side_effect = [attempt, fixture.notification, uuid4()]
    await fixture.store.complete(
        notification_id=fixture.notification.id,
        attempt_id=attempt.id,
        result=DeliveryResult(status=DeliveryStatus.FAILED, retryable=True, error_code="TIMEOUT"),
        completed_at=NOW + timedelta(seconds=1),
        max_attempts=3,
    )
    assert attempt.status == "FAILED" and attempt.error_code == "TIMEOUT"
    assert attempt.retryable is True
    assert fixture.notification.status == "FAILED"
    fixture.session.commit.assert_awaited_once()
