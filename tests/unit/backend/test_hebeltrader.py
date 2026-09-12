"""Regression and boundary tests for the reconstructed policy (no broker orders)."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.features.position_monitoring.domain.hebeltrader import (
    SessionCalendar,
    evaluate_management,
)
from app.features.product_selection.domain.hebeltrader_pricing import european_call_scenario
from app.features.trade_plan.api.hebeltrader_router import router
from app.features.trade_plan.domain.hebeltrader import (
    Levels,
    assess_entry,
    build_levels,
    diagnose_bands,
    round_down,
)

D = Decimal


def levels() -> Levels:
    return Levels(D("100"), D("90"), D("130"), D("160"))


def assessment(**kwargs):
    values = dict(
        levels=levels(),
        stock_levels=levels(),
        stock_price=D("100"),
        gd200=D("95"),
        fundamental_ok=True,
        bid=D("100"),
        ask=D("100"),
    )
    values.update(kwargs)
    return assess_entry(**values)


def calendar() -> SessionCalendar:
    # Explicit synthetic fixture: skip a weekday holiday as well as weekends.
    start = date(2026, 8, 10)
    days = tuple(
        start + timedelta(days=i)
        for i in range(180)
        if (start + timedelta(days=i)).weekday() < 5
        and start + timedelta(days=i) != date(2026, 8, 17)
    )
    return SessionCalendar(
        "TEST",
        "synthetic-fixture-not-an-exchange-calendar",
        start,
        start + timedelta(days=179),
        days,
    )


def management(**kwargs):
    cal = calendar()
    values = dict(
        levels=levels(),
        actual_entry=D("100"),
        current_stop=D("90"),
        bid=D("105"),
        quote_usable=True,
        entered_on=cal.sessions[0],
        as_of=cal.sessions[10],
        calendar=cal,
    )
    values.update(kwargs)
    return evaluate_management(**values)


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as result:
        yield result


BASE = "/api/v1/trade-plans/strategies/hebeltrader"


def preview_payload():
    return {
        "as_of": "2026-09-11T16:00:00+02:00",
        "analysis_date": "2026-09-11",
        "source_ref": "synthetic-reviewed-input",
        "quote": {
            "bid": "100",
            "ask": "101",
            "observed_at": "2026-09-11T15:59:00+02:00",
            "currency": "EUR",
            "source": "synthetic",
        },
        "gd200": "95",
        "band_width": "30",
        "fundamental_ok": True,
    }


@pytest.mark.parametrize("bad", ["NaN", "Infinity", "-Infinity", "0", "-1"])
def test_reject_invalid_levels(bad):
    with pytest.raises(ValueError):
        Levels(D(bad), D("1"), D("3"), D("4"))


@pytest.mark.parametrize(
    "values",
    [
        (100, 100, 130, 160),
        (100, 90, 100, 160),
        (100, 90, 130, 130),
        (100, 90, 150, 140),
    ],
)
def test_reject_bad_order(values):
    with pytest.raises(ValueError):
        Levels(*(D(x) for x in values))


def test_band_formula_and_tick_multiple():
    value = build_levels(
        entry=D("102"),
        gd200=D("95.02"),
        band_width=D("30.04"),
        support=D("95.02"),
        buffer_fraction=D("0"),
        tick=D("0.05"),
    )
    assert value.stop == D("95")
    assert value.target1 == D("125.05")
    assert value.target2 == D("155.10")
    assert round_down(D("1.079"), D("0.05")) == D("1.05")


@pytest.mark.parametrize("buffer", ["-0.1", "1", "NaN"])
def test_invalid_buffer(buffer):
    with pytest.raises(ValueError):
        build_levels(
            entry=D("100"),
            gd200=D("95"),
            band_width=D("30"),
            support=D("95"),
            buffer_fraction=D(buffer),
            tick=D("0.01"),
        )


def test_support_cannot_be_above_entry():
    with pytest.raises(ValueError):
        build_levels(
            entry=D("100"),
            gd200=D("95"),
            band_width=D("30"),
            support=D("105"),
            buffer_fraction=D("0.1"),
            tick=D("0.01"),
        )


@pytest.mark.parametrize(
    "values, expected",
    [
        (("0.16", "0.07", "0.71", "2.12"), "13.94"),  # BP issue 167, pp. 1-2
        (("0.30", "0.11", "1.10", "5.65"), "16.18"),  # MTU issue 1: table, not prose
    ],
)
def test_published_crv_regressions(values, expected):
    assert Levels(*(D(v) for v in values)).reward_risk.quantize(D("0.01")) == D(expected)


def test_intel_band_exception_preserved():
    value = Levels(D("90"), D("80"), D("132"), D("210"))
    diagnostic = diagnose_bands(value, D("79.59"))
    assert diagnostic.implied_base == 54
    assert diagnostic.status == "REVIEW"


def test_original_entry_crv_is_not_reused_for_more_expensive_ask():
    assert assessment(ask=D("105")).reward_risk < assessment().reward_risk


@pytest.mark.parametrize(
    "field, value, reason",
    [
        ("fundamental_ok", False, "FUNDAMENTAL_REVIEW_REQUIRED"),
        ("gd200", D("100"), "STOCK_NOT_ABOVE_GD200"),
        ("bid", D("90"), "STOP_ALREADY_REACHED"),
        ("ask", D("130"), "SPREAD_CROSSES_TARGET1"),
        ("ask", D("160"), "TARGET2_ALREADY_REACHED_OR_NOT_ABOVE_ASK"),
    ],
)
def test_entry_rejections(field, value, reason):
    result = assessment(**{field: value})
    assert not result.eligible and result.allocation_fraction == 0
    assert reason in result.reasons


def test_exact_two_percent_allowed_but_less_blocked():
    assert assessment(stock_levels=Levels(D("100"), D("98"), D("130"), D("160"))).eligible
    assert not assessment(stock_levels=Levels(D("100"), D("98.01"), D("130"), D("160"))).eligible


def test_warrant_uses_stock_two_percent_rule():
    warrant = Levels(D("0.16"), D("0.07"), D("0.71"), D("2.12"))
    result = assessment(
        levels=warrant,
        bid=D("0.16"),
        ask=D("0.16"),
        stock_levels=Levels(D("100"), D("99"), D("130"), D("160")),
    )
    assert not result.eligible
    assert result.stock_stop_distance == D("0.01")


def test_late_entry_only_counts_remaining_target():
    result = assessment(stock_price=D("135"), bid=D("135"), ask=D("136"), target1_seen=True)
    assert result.eligible and result.allocation_fraction == D("0.5")
    assert result.effective_stop == 100
    assert result.reward_risk == (D("160") - 136) / (136 - 100)


def test_late_entry_after_pullback_remains_late():
    result = assessment(stock_price=D("120"), bid=D("120"), ask=D("121"), target1_seen=True)
    assert result.late_entry


def test_crossed_quotes_rejected():
    with pytest.raises(ValueError):
        assessment(bid=D("102"), ask=D("100"))


def test_inconsistent_target_flags_rejected():
    with pytest.raises(ValueError):
        assessment(target2_seen=True)


def test_session_counter_excludes_entry_and_holidays():
    cal = calendar()
    assert cal.count(cal.sessions[0], cal.sessions[0]) == 0
    assert cal.count(cal.sessions[0], date(2026, 8, 17)) == 4
    assert cal.count(cal.sessions[0], cal.sessions[20]) == 20


@pytest.mark.parametrize(
    "field, value",
    [
        ("source", ""),
        ("time_zone", "not/a/zone"),
        ("sessions", (date(2026, 8, 11), date(2026, 8, 10))),
        ("sessions", (date(2026, 8, 10), date(2026, 8, 10))),
    ],
)
def test_invalid_calendar(field, value):
    with pytest.raises(ValueError):
        replace(calendar(), **{field: value})


def test_calendar_coverage_cannot_silently_count_zero_days():
    with pytest.raises(ValueError):
        calendar().count(date(2025, 1, 1), date(2026, 8, 10))


@pytest.mark.parametrize(
    "index, expected",
    [
        (19, "NO_EXIT_CONDITION"),
        (20, "LOSS_AFTER_20_SESSIONS"),
        (21, "LOSS_AFTER_20_SESSIONS"),
    ],
)
def test_twenty_session_loss_boundary(index, expected):
    assert management(as_of=calendar().sessions[index], bid=D("99")).reason == expected


def test_break_even_not_a_loss_at_twenty_sessions():
    assert management(as_of=calendar().sessions[20], bid=D("100")).reason == "NO_EXIT_CONDITION"


def test_stop_priority_over_time_exit_and_zero_bid():
    assert management(as_of=calendar().sessions[20], bid=D("0")).reason == "STOP_REACHED"


def test_target1_signal_does_not_claim_fill_or_raise_stop_yet():
    first = management(bid=D("130"))
    assert first.action == "PARTIAL_EXIT_REVIEW"
    assert first.sell_fraction_of_initial == D("0.5")
    assert first.proposed_stop == D("90")
    assert first.stop_after_confirmed_fill == 100
    assert first.requires_fill_confirmation
    assert management(bid=D("130")) == first  # deterministic, no hidden mutation


def test_confirmed_target1_prevents_repeated_half_sales():
    result = management(
        bid=D("135"),
        remaining_fraction=D("0.5"),
        target1_completed_on=calendar().sessions[5],
    )
    assert result.sell_fraction_of_initial == 0
    assert result.proposed_stop == 100


def test_target2_gap_exits_whole_remaining_position_without_fake_t1_fill():
    assert management(bid=D("170")).sell_fraction_of_initial == 1
    assert management(bid=D("170")).reason == "TARGET2_REACHED"


def test_post_target1_twenty_session_boundary_and_monotonic_stop():
    cal = calendar()
    options = dict(
        bid=D("120"),
        remaining_fraction=D("0.5"),
        target1_completed_on=cal.sessions[5],
    )
    assert management(as_of=cal.sessions[24], **options).proposed_stop == 100
    assert management(as_of=cal.sessions[25], **options).proposed_stop == 104
    assert management(as_of=cal.sessions[25], current_stop=D("110"), **options).proposed_stop == 110


def test_published_lowering_ambiguity_does_not_lower_breakeven():
    result = management(
        levels=Levels(D("100"), D("90"), D("110"), D("130")),
        bid=D("115"),
        remaining_fraction=D("0.5"),
        target1_completed_on=calendar().sessions[5],
        as_of=calendar().sessions[25],
    )
    assert result.proposed_stop == 100  # not 88


@pytest.mark.parametrize(
    "remaining, expected",
    [
        (21, "NO_EXIT_CONDITION"),
        (20, "EXPIRY_20_SESSIONS"),
        (19, "EXPIRY_20_SESSIONS"),
    ],
)
def test_expiry_boundary(remaining, expected):
    cal = calendar()
    result = management(last_trading_date=cal.sessions[10 + remaining], instrument_kind="CALL")
    assert result.reason == expected


def test_expiry_review_does_not_need_a_fabricated_quote():
    result = management(
        last_trading_date=calendar().sessions[30],
        instrument_kind="CALL",
        quote_usable=False,
        bid=None,
    )
    assert result.reason == "EXPIRY_20_SESSIONS"
    assert result.requires_fill_confirmation


def test_missing_quote_is_not_a_hold_signal():
    assert management(quote_usable=False, bid=None).action == "DATA_REQUIRED"


def test_call_requires_verified_last_trading_date():
    with pytest.raises(ValueError):
        management(instrument_kind="CALL")


@pytest.mark.parametrize(
    "changes",
    [
        {"remaining_fraction": D("0.25")},
        {"remaining_fraction": D("0.5")},
        {"current_stop": D("89")},
        {"late_entry": True},
        {"target1_completed_on": date(2026, 8, 17)},
        {"entered_on": date(2026, 8, 17)},
        {"last_trading_date": date(2027, 12, 31)},
        {"instrument_kind": "PUT"},
    ],
)
def test_inconsistent_management_state_fails_closed(changes):
    with pytest.raises(ValueError):
        management(**changes)


def test_closed_position_has_no_action():
    assert management(remaining_fraction=D("0")).action == "NONE"


def test_late_entry_stop_uses_recommended_not_actual_entry():
    result = management(
        actual_entry=D("135"),
        bid=D("140"),
        remaining_fraction=D("0.5"),
        target1_completed_on=calendar().sessions[0],
        late_entry=True,
    )
    assert result.proposed_stop == 100


def call(**changes):
    values = dict(
        spot=D("100"),
        strike=D("100"),
        ratio=D("1"),
        valuation_date=date(2026, 9, 11),
        exercise_date=date(2027, 9, 11),
        implied_volatility=D("0.2"),
        risk_free_rate=D("0.05"),
        dividend_yield=D("0"),
        fx_quote_per_underlying=D("1"),
    )
    values.update(changes)
    return european_call_scenario(**values)


def test_black_scholes_reference_and_expiry_intrinsic():
    assert float(call()) == pytest.approx(10.450583572185565)
    assert call(spot=D("110"), exercise_date=date(2026, 9, 11)) == 10
    assert call(exercise_date=date(2026, 9, 11)) == 0


def test_explicit_fx_and_subscription_ratio():
    assert call(ratio=D("0.01"), fx_quote_per_underlying=D("0.9")) == call() * D("0.009")


def test_zero_iv_and_volatility_crush():
    assert call(implied_volatility=D("0")) >= 0
    assert call(spot=D("103"), implied_volatility=D("0.2")) < call(implied_volatility=D("0.5"))


@pytest.mark.parametrize(
    "changes",
    [
        {"spot": D("NaN")},
        {"implied_volatility": D("20")},
        {"risk_free_rate": D("Infinity")},
        {"exercise_date": date(2026, 1, 1)},
        {"spot": D("1e-500")},
    ],
)
def test_invalid_pricing_input_rejected(changes):
    with pytest.raises(ValueError):
        call(**changes)


def test_api_preview_returns_compatible_product_neutral_content(client):
    response = client.post(BASE + "/preview", json=preview_payload())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["execution_enabled"] is False
    assert body["trade_plan_content"]["entry"]["type"] == "PRICE"
    assert body["trade_plan_content"]["entry"]["price"] == "101"
    assert body["trade_plan_content"]["invalidation"]["stop_price"] == "95"
    assert len(body["input_digest"]) == 64
    assert body["levels"]["target1"] == "125"


@pytest.mark.parametrize(
    "edit",
    [
        {"band_width": None},
        {"gd200": "NaN"},
        {"support_source": "GD50"},
        {"unknown": "field"},
        {"as_of": "2026-09-11T16:00:00"},
        {"analysis_date": "2026-09-12"},
    ],
)
def test_api_invalid_inputs_are_422(client, edit):
    payload = preview_payload() | edit
    assert client.post(BASE + "/preview", json=payload).status_code == 422


def test_api_stale_and_future_quotes_never_produce_a_draft(client):
    for stamp in ("2026-09-10T16:00:00+02:00", "2026-09-11T16:01:00+02:00"):
        payload = preview_payload()
        payload["quote"]["observed_at"] = stamp
        body = client.post(BASE + "/preview", json=payload).json()
        assert body["assessment"]["eligible"] is False
        assert body["trade_plan_content"] is None


def test_api_fundamental_and_old_analysis_gates(client):
    for edit in ({"fundamental_ok": False}, {"analysis_date": "2026-08-01"}):
        body = client.post(BASE + "/preview", json=preview_payload() | edit).json()
        assert body["trade_plan_content"] is None


def test_api_ambiguous_original_values_are_not_repaired(client):
    payload = preview_payload()
    payload.pop("band_width")
    payload["published_levels"] = {
        "entry": "90",
        "stop": "80",
        "target1": "132",
        "target2": "210",
    }
    payload["gd200"] = "79.59"
    body = client.post(BASE + "/preview", json=payload).json()
    assert body["levels"]["target2"] == "210"
    assert "BAND_DEVIATION_REQUIRES_REVIEW" in body["warnings"]


def test_api_rule_profile_is_explicitly_non_executing(client):
    body = client.get(BASE + "/rules").json()
    assert body["profile_effective_from"] == "2026-08-10"
    assert body["execution_enabled"] is False
