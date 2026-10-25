"""API-specific currency, expiry, model and session-timezone boundaries."""

from datetime import date, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.features.trade_plan.api.hebeltrader_router import router

BASE = "/api/v1/trade-plans/strategies/hebeltrader"


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as value:
        yield value


def calendar_payload():
    start = date(2026, 8, 10)
    sessions = [
        (start + timedelta(days=i)).isoformat()
        for i in range(180)
        if (start + timedelta(days=i)).weekday() < 5
    ]
    return {
        "venue": "TEST",
        "source": "synthetic",
        "coverage_start": "2026-08-10",
        "coverage_end": "2027-02-05",
        "sessions": sessions,
    }


def quote():
    return {
        "bid": "0.16",
        "ask": "0.17",
        "currency": "EUR",
        "source": "synthetic",
        "observed_at": "2026-09-11T16:00:00+02:00",
    }


def entry_payload():
    return {
        "as_of": "2026-09-11T16:00:00+02:00",
        "instrument_kind": "CALL",
        "levels": {"entry": "0.16", "stop": "0.07", "target1": "0.71", "target2": "2.12"},
        "stock_levels": {"entry": "100", "stop": "90", "target1": "130", "target2": "160"},
        "stock_price": "100",
        "gd200": "95",
        "fundamental_ok": True,
        "stock_currency": "USD",
        "levels_currency": "EUR",
        "quote": quote(),
        "strike": "140",
        "calendar": calendar_payload(),
        "last_trading_date": "2027-01-15",
    }


def management_payload():
    return {
        "as_of": "2026-09-11T16:00:00+02:00",
        "instrument_kind": "CALL",
        "levels": {"entry": "0.16", "stop": "0.07", "target1": "0.71", "target2": "2.12"},
        "position_currency": "EUR",
        "actual_entry": "0.16",
        "current_stop": "0.07",
        "quote": quote(),
        "entered_on": "2026-08-10",
        "calendar": calendar_payload(),
        "last_trading_date": "2027-01-15",
    }


def test_call_entry_api_preserves_decimal_strings_and_distinct_currencies(client):
    response = client.post(BASE + "/entry-check", json=entry_payload())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["eligible"] is True
    assert isinstance(body["reward_risk"], str)
    assert body["execution_enabled"] is False


@pytest.mark.parametrize(
    "update",
    [
        {"strike": None},
        {"calendar": None},
        {"last_trading_date": None},
        {"levels_currency": "USD"},
        {"last_trading_date": "2028-01-01"},
    ],
)
def test_call_entry_missing_or_mismatched_inputs_fail_closed(client, update):
    assert client.post(BASE + "/entry-check", json=entry_payload() | update).status_code == 422


@pytest.mark.parametrize(
    "update, reason",
    [
        ({"strike": "100"}, "CALL_NOT_OTM_AT_RECOMMENDATION"),
        ({"last_trading_date": "2026-09-11"}, "EXPIRY_BUFFER_NOT_MET"),
        ({"last_trading_date": "2026-08-14"}, "EXPIRY_BUFFER_NOT_MET"),
    ],
)
def test_call_entry_expiry_and_otm_filters(client, update, reason):
    body = client.post(BASE + "/entry-check", json=entry_payload() | update).json()
    assert body["eligible"] is False
    assert reason in body["reasons"]


def test_entry_stale_quote_rejected_without_inventing_a_replacement(client):
    payload = entry_payload()
    payload["quote"]["observed_at"] = "2026-09-10T16:00:00+02:00"
    body = client.post(BASE + "/entry-check", json=payload).json()
    assert not body["eligible"]
    assert "QUOTE_STALE_OR_FUTURE" in body["reasons"]


def test_management_api_returns_read_only_decimal_projection(client):
    response = client.post(BASE + "/management-preview", json=management_payload())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["proposed_stop"] == "0.07"
    assert body["action"] == "HOLD_REVIEW"
    assert body["execution_enabled"] is False


def test_management_unknown_quote_does_not_fabricate_hold(client):
    response = client.post(
        BASE + "/management-preview", json=management_payload() | {"quote": None}
    )
    body = response.json()
    assert body["action"] == "DATA_REQUIRED"


def test_management_currency_mismatch_fails_closed(client):
    response = client.post(
        BASE + "/management-preview",
        json=management_payload() | {"position_currency": "USD"},
    )
    assert response.status_code == 422


def test_management_uses_venue_timezone_not_utc_date(client):
    payload = management_payload()
    payload["as_of"] = "2026-09-10T23:30:00Z"  # already Friday in Berlin
    payload["quote"]["observed_at"] = payload["as_of"]
    body = client.post(BASE + "/management-preview", json=payload).json()
    assert body["held_sessions"] == 24


def test_old_management_profile_is_not_silently_used(client):
    payload = management_payload()
    payload["as_of"] = "2026-08-07T16:00:00+02:00"
    assert client.post(BASE + "/management-preview", json=payload).status_code == 422


def scenario_payload():
    return {
        "spot": "100",
        "strike": "100",
        "ratio": "0.1",
        "valuation_date": "2026-09-11",
        "exercise_date": "2027-09-11",
        "implied_volatility": "0.2",
        "risk_free_rate": "0.05",
        "dividend_yield": "0",
        "fx_quote_per_underlying": "0.9",
        "underlying_currency": "USD",
        "warrant_currency": "EUR",
        "exercise_style": "EUROPEAN",
        "quanto": False,
    }


def test_scenario_api_reports_assumptions_not_an_executable_bid(client):
    response = client.post(BASE + "/call-scenario", json=scenario_payload())
    assert response.status_code == 200, response.text
    body = response.json()
    assert float(body["theoretical_value"]) == pytest.approx(0.9405525214967009)
    assert body["execution_enabled"] is False
    assert body["inputs"]["fx_quote_per_underlying"] == "0.9"


@pytest.mark.parametrize(
    "update",
    [
        {"exercise_style": "AMERICAN"},
        {"quanto": True},
        {"underlying_currency": "EUR"},
        {"implied_volatility": None},
        {"exercise_date": "2025-01-01"},
    ],
)
def test_scenario_does_not_guess_unsupported_contracts_or_missing_inputs(client, update):
    assert client.post(BASE + "/call-scenario", json=scenario_payload() | update).status_code == 422


def stock_entry_payload():
    payload = entry_payload()
    payload.update(
        instrument_kind="STOCK",
        levels=payload["stock_levels"],
        levels_currency="USD",
        quote=quote() | {"bid": "100", "ask": "101", "currency": "USD"},
    )
    return payload


def test_stock_entry_uses_one_consistent_price_axis(client):
    response = client.post(BASE + "/entry-check", json=stock_entry_payload())
    assert response.status_code == 200
    assert response.json()["eligible"] is True


@pytest.mark.parametrize("update", [{"stock_currency": "EUR"}, {"stock_price": "99"}])
def test_stock_axes_cannot_be_mixed(client, update):
    response = client.post(BASE + "/entry-check", json=stock_entry_payload() | update)
    assert response.status_code == 422


def test_subnormal_volatility_has_a_finite_zero_vol_limit(client):
    payload = scenario_payload() | {
        "exercise_date": "2026-09-12",
        "implied_volatility": "1e-323",
    }
    response = client.post(BASE + "/call-scenario", json=payload)
    assert response.status_code == 200, response.text
    assert float(response.json()["theoretical_value"]) >= 0
