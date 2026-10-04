from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.features.analysis.domain.product_comparison import SynchronizedPricePair, compare_product
from app.features.analysis.domain.risk_analytics import RiskMetrics, risk_metrics
from app.features.market_data.domain.enums import MarketDataProvider, QualityStatus
from app.features.market_data.domain.models import DailyPrice
from app.features.position_monitoring.domain.risk_signals import RiskParameters, assess_risk

D = Decimal
LISTING = UUID("00000000-0000-4000-8000-000000000099")
NOW = datetime(2026, 9, 29, tzinfo=UTC)


def prices(count=45):
    dates = []
    day = date(2026, 7, 27)
    while len(dates) < count:
        if day.weekday() < 5:
            dates.append(day)
        day += timedelta(days=1)
    return tuple(
        DailyPrice(
            LISTING,
            day,
            D(100),
            D(101),
            D(99),
            D(100),
            D(100),
            D(1000),
            "EUR",
            MarketDataProvider.EODHD,
            "TEST.XETRA",
            datetime.combine(day, datetime.min.time(), tzinfo=UTC) + timedelta(hours=22),
            None,
            QualityStatus.VALID,
        )
        for day in dates
    )


def metrics(day, distance=".02", volatility=".2"):
    return RiskMetrics(
        "AVAILABLE",
        "QUALIFIED",
        session=date(2026, 9, day),
        distance_sma20=D(distance),
        realized_volatility20=D(volatility),
    )


def assess(value, previous=None, direction="CALL"):
    return assess_risk(value, direction=direction, parameters=RiskParameters(), previous=previous)


def test_short_window_without_sma200_constant_prices_and_previous_window():
    result = risk_metrics(prices(), as_of=NOW)
    assert result.status == "AVAILABLE"
    assert result.sma20 == D(100)
    assert result.realized_volatility20 == 0
    assert result.previous_volatility20 == 0
    assert result.distance_sma20 == result.sma20_slope == 0
    assert result.atr14_relative == D(".02")
    assert risk_metrics(prices(20), as_of=NOW).status == "NOT_EVALUABLE"


@pytest.mark.parametrize(
    "change,reason",
    [
        ("gap", "MISSING_SESSION_OR_UNVERIFIED_HOLIDAY"),
        ("order", "DATES_NOT_STRICTLY_INCREASING"),
        ("duplicate", "DATES_NOT_STRICTLY_INCREASING"),
        ("missing_adjusted", "ADJUSTED_CLOSE_MISSING"),
        ("currency", "SERIES_IDENTITY_OR_CURRENCY_CHANGED"),
        ("identity", "SERIES_IDENTITY_OR_CURRENCY_CHANGED"),
        ("future_receipt", "DATA_NOT_KNOWN_AT_EVALUATION"),
        ("quality", "EOD_QUALITY_LIMITED"),
        ("stale", "EOD_STALE"),
    ],
)
def test_data_qualification(change, reason):
    values = list(prices())
    at = NOW
    if change == "gap":
        values.pop(-4)
    if change == "order":
        values[-2:] = reversed(values[-2:])
    if change == "duplicate":
        values.append(values[-1])
    if change == "missing_adjusted":
        values[-1] = replace(values[-1], adjusted_close=None)
    if change == "currency":
        values[-1] = replace(values[-1], currency="USD")
    if change == "identity":
        values[-1] = replace(values[-1], listing_id=uuid4())
    if change == "future_receipt":
        values[-1] = replace(values[-1], retrieved_at=NOW + timedelta(days=1))
    if change == "quality":
        values[-1] = replace(values[-1], warnings=("suspect",))
    if change == "stale":
        at += timedelta(days=10)
    assert risk_metrics(tuple(values), as_of=at).reason == reason


def test_split_keeps_adjusted_trend_but_suppresses_raw_atr():
    values = list(prices())
    values[-1] = replace(values[-1], open=D(50), high=D(51), low=D(49), close=D(50))
    result = risk_metrics(tuple(values), as_of=NOW)
    assert result.status == "AVAILABLE"
    assert result.realized_volatility20 == 0
    assert result.atr14_relative is None
    assert result.atr_reason == "CORPORATE_ACTION_OR_ADJUSTMENT_CHANGE"


def test_today_is_not_completed_and_future_prices_do_not_enter_metrics():
    values = prices()
    result = risk_metrics(values, as_of=values[-1].retrieved_at)
    assert result.session == values[-2].trading_date
    with pytest.raises(ValueError):
        risk_metrics(values, as_of=NOW.replace(tzinfo=None))


@pytest.mark.parametrize("direction,warning", [("CALL", True), ("PUT", False)])
def test_crossing_requires_distinct_confirmed_sessions_and_is_directional(direction, warning):
    initial = assess(metrics(21), direction=direction)
    assert initial.transition == "INITIALIZED" and initial.trend_triggered is None
    confirming = assess(metrics(22, "-.02"), initial.state, direction)
    assert confirming.transition == "CONFIRMING"
    repeat = assess(metrics(22, "-.03"), confirming.state, direction)
    assert repeat.state.pending_sessions == 1 and repeat.trend_triggered is None
    crossed = assess(metrics(23, "-.02"), repeat.state, direction)
    assert crossed.transition == "CROSSED_BELOW" and crossed.trend_triggered is warning
    continued = assess(metrics(24, "-.02"), crossed.state, direction)
    assert continued.transition == "UNCHANGED"
    assert continued.trend_triggered is warning


def test_gap_freezes_warning_then_recovery_requires_new_confirmation():
    state = assess(metrics(21)).state
    state = assess(metrics(22, "-.02"), state).state
    state = assess(metrics(23, "-.02"), state).state
    gap = assess(RiskMetrics("NOT_EVALUABLE", "EOD_STALE"), state)
    assert gap.state.trend_warning and gap.trend_triggered is None
    first = assess(metrics(25), gap.state)
    assert first.state.trend_warning and first.state.pending_sessions == 1
    recovered = assess(metrics(28), first.state)
    assert recovered.transition == "CROSSED_ABOVE" and recovered.trend_triggered is False


def test_sideways_noise_does_not_cross_and_first_adverse_is_not_break():
    initial = assess(metrics(21, "-.02"))
    assert not initial.state.trend_warning
    for day, value in [(22, ".003"), (23, "-.004"), (24, "0")]:
        initial = assess(metrics(day, value), initial.state)
        assert initial.transition == "UNCHANGED" and not initial.state.trend_warning


def test_volatility_hysteresis_and_unknown_direction_are_independent():
    initial = assess(metrics(21))
    high = assess(metrics(22, volatility=".41"), initial.state, direction=None)
    assert high.volatility_triggered and high.trend_triggered is None
    hold = assess(metrics(23, volatility=".37"), high.state)
    assert hold.volatility_triggered
    reset = assess(metrics(24, volatility=".35"), hold.state)
    assert reset.volatility_triggered is False


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(hysteresis_fraction=D("NaN")),
        dict(confirmation_sessions=0),
        dict(maximum_age_days=11),
        dict(volatility_reset=D(".5")),
        dict(hysteresis_fraction=D(".2")),
    ],
)
def test_invalid_parameters_fail(kwargs):
    with pytest.raises(ValueError):
        RiskParameters(**kwargs)


def pairs(direction="CALL"):
    ids = [uuid4() for _ in range(5)]
    first = SynchronizedPricePair(
        *ids,
        "SYNTHETIC",
        "EUR",
        "EUR",
        NOW - timedelta(days=1),
        NOW - timedelta(days=1),
        NOW - timedelta(days=1),
        D(100),
        D(2),
        D("2.2"),
        D(".1"),
        direction,
    )
    second = replace(
        first,
        underlying_observed_at=NOW,
        warrant_observed_at=NOW,
        received_at=NOW,
        underlying_price=D(101 if direction == "CALL" else 99),
        bid=D("1.8"),
        ask=D(2),
    )
    return first, second


@pytest.mark.parametrize("direction", ["CALL", "PUT"])
def test_synchronous_descriptive_divergence_and_normalization(direction):
    result = compare_product(pairs(direction), as_of=NOW)
    assert result.status == "AVAILABLE" and result.descriptive_divergence
    assert result.warrant_return == D("-.1")
    assert result.direction_adjusted_underlying_return == D(".01")
    assert result.normalized_warrant == (D(100), D(90))
    assert not result.execution_usable


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("warrant_observed_at", NOW - timedelta(minutes=1), "PRICE_INSTANTS_NOT_SYNCHRONOUS"),
        ("received_at", NOW + timedelta(seconds=1), "REPEATED_OUT_OF_ORDER_OR_FUTURE_OBSERVATION"),
        ("retained", True, "QUOTE_RETAINED_OR_QUALITY_LIMITED"),
        ("bid", D(0), "INVALID_PRICE_OR_RATIO"),
        ("ask", D(0), "INVALID_TWO_SIDED_QUOTE"),
        ("quality", "ERROR", "QUOTE_RETAINED_OR_QUALITY_LIMITED"),
        ("underlying_observed_at", NOW.replace(tzinfo=None), "SOURCE_TIME_OR_TIMEZONE_UNKNOWN"),
    ],
)
def test_comparison_fail_closed(field, value, reason):
    first, second = pairs()
    assert compare_product((first, replace(second, **{field: value})), as_of=NOW).reasons == (
        reason,
    )


def test_comparison_fx_split_identity_mid_and_dedup():
    points = pairs()
    assert compare_product(
        tuple(replace(p, warrant_currency="USD") for p in points), as_of=NOW
    ).reasons == ("FX_OR_QUANTO_CONTEXT_UNVERIFIED",)
    assert (
        compare_product((points[0], replace(points[1], ratio=D(".2"))), as_of=NOW).status
        == "NOT_EVALUABLE"
    )
    assert compare_product((points[0], points[0]), as_of=NOW).status == "NOT_EVALUABLE"
    assert compare_product((points[0],), as_of=NOW).status == "NOT_EVALUABLE"
    assert compare_product(
        tuple(replace(p, ask=None) for p in points), as_of=NOW, price_type="MID_INDICATION"
    ).reasons == ("MID_REQUIRES_TWO_SIDED_QUOTE",)
    assert compare_product(points, as_of=NOW, price_type="MID_INDICATION").status == "AVAILABLE"


@pytest.mark.parametrize(
    "mode", ["unknown", "one_sided", "stale", "retained", "future", "no_bid", "two_sided"]
)
def test_quote_quality_never_turns_receipt_into_original_time(mode):
    from app.features.market_data.domain.models import WarrantQuoteSnapshot
    from app.features.market_data.domain.risk_evidence import SavedQuoteEvidence
    from app.features.position_monitoring.domain.quote_quality import qualify_quote

    quote = WarrantQuoteSnapshot(
        uuid4(),
        D(2),
        D("2.2"),
        "EUR",
        "SYNTHETIC",
        "ISSUER",
        NOW,
        max_quote_age_seconds=60,
        bid_volume=0,
        ask_volume=None,
    )
    if mode == "unknown":
        quote = replace(
            quote,
            observed_at=None,
            quote_time_basis="DATE_AND_TIMEZONE_UNKNOWN",
            source_mode="OFFICIAL_ISSUER_INDICATION_TIME_ONLY",
        )
    if mode == "one_sided":
        quote = replace(quote, ask=None)
    if mode == "stale":
        quote = replace(quote, observed_at=NOW - timedelta(minutes=5))
    if mode == "retained":
        quote = replace(quote, retained=True, refresh_error="SYNTHETIC")
    if mode == "future":
        quote = replace(quote, observed_at=NOW + timedelta(minutes=1))
    if mode == "no_bid":
        quote = replace(quote, bid=None)
    result = qualify_quote(SavedQuoteEvidence("SAVED", quote, "SYNTHETIC", NOW), as_of=NOW)
    assert not result.execution_usable and result.status == "LIMITED"
    assert result.observed_at == quote.observed_at and result.received_at == NOW
    assert "BID_VOLUME_ZERO" in result.reasons and "ASK_VOLUME_UNKNOWN" in result.reasons
    if mode == "two_sided":
        assert result.spread_mid_percent == D(".2") / D("2.1") * 100
    if mode == "unknown":
        assert result.age_seconds is None
    if mode == "one_sided":
        assert result.spread_mid_percent is None and "ASK_MISSING" in result.reasons
    if mode == "retained":
        assert "QUOTE_RETAINED_OR_REFRESH_FAILED" in result.reasons
