"""Independent reference values plus unit, boundary and conditioning tests."""

from dataclasses import replace
from decimal import Decimal as D

import pytest

from app.features.analysis.domain.vanilla_iv import (
    Scenario,
    VanillaInputs,
    fraction,
    local_iv_effect,
    percentage_points,
    price_and_vega,
    revalue,
    solve_iv,
)


def inputs(**changes):
    return replace(
        VanillaInputs(
            "VANILLA_WARRANT",
            "EUROPEAN",
            "CALL",
            D(100),
            D(100),
            D(".1"),
            D(365),
            D(".2"),
            D(".05"),
            D(0),
            "EUR",
            "EUR",
            "EUR",
            False,
            "CONTINUOUS_YIELD",
            "UNDERLYING_UNITS_PER_WARRANT",
        ),
        **changes,
    )


def scenario(**changes):
    return replace(Scenario(D(0), D(-5), D(0), D(100)), **changes)


def test_units_user_example_and_no_double_ratio_or_quantity():
    assert fraction(D(35)) == D(".35")
    change = percentage_points(fraction(D(35)), fraction(D(30)))
    assert change == -5  # Not -14.2857 relative percent, nor -.05 pp.
    assert local_iv_effect(D(".02"), change) == D("-.10")
    assert local_iv_effect(D(".02"), change) * 500 == -50
    with pytest.raises(ValueError):
        fraction(D("NaN"))
    with pytest.raises(ValueError):
        percentage_points(D("Infinity"), D(0))


@pytest.mark.parametrize("vega", [None, D(0), D(-1), D("NaN")])
def test_missing_or_invalid_vega_is_not_zero_risk(vega):
    with pytest.raises(ValueError, match="VEGA_OR_CHANGE_UNAVAILABLE"):
        local_iv_effect(vega, D(-5))


# Independent published fixtures: QuantLib v1.40, test-suite/europeanoption.cpp,
# testValues (Haug 1998). Enter its year fractions directly as 365*t calendar days.
@pytest.mark.parametrize(
    "direction,k,s,q,r,t,vol,expected",
    [
        ("CALL", "65", "60", "0", ".08", ".25", ".30", "2.1334"),
        ("PUT", "95", "100", ".05", ".10", ".50", ".20", "2.4648"),
        ("PUT", "19", "19", ".10", ".10", ".75", ".28", "1.7011"),
        ("CALL", "19", "19", ".10", ".10", ".75", ".28", "1.7011"),
        ("CALL", "1.60", "1.56", ".08", ".06", ".50", ".12", ".0291"),
        ("CALL", "100", "90", ".10", ".10", ".10", ".15", ".0205"),
        ("PUT", "100", "110", ".10", ".10", ".10", ".15", ".0408"),
    ],
)
def test_independent_quantlib_prices(direction, k, s, q, r, t, vol, expected):
    value = inputs(
        direction=direction,
        strike=D(k),
        spot=D(s),
        dividend_yield_decimal=D(q),
        rate_decimal=D(r),
        remaining_days=D(t) * 365,
        iv_decimal=D(vol),
        ratio=D(1),
    )
    assert abs(price_and_vega(value).price - D(expected)) < D(".0001")


def test_reference_greeks_inverse_and_ratio_quantity_scaling():
    # S=K=100, r=5%, q=0, T=1, sigma=20%: standard BSM benchmark.
    value = price_and_vega(inputs())
    assert float(value.price) == pytest.approx(1.045058357218556, abs=1e-12)
    assert float(value.vega_per_warrant_per_pp) == pytest.approx(0.0375240346916938, abs=1e-13)
    assert float(solve_iv(inputs(), D("1.045058357218556"))) == pytest.approx(0.2, abs=1e-12)
    base = revalue(inputs(), scenario())
    doubled_ratio = revalue(inputs(ratio=D(".2")), scenario())
    doubled_quantity = revalue(inputs(), scenario(quantity=D(200)))
    assert float(doubled_ratio.position_change) == pytest.approx(float(base.position_change) * 2)
    assert doubled_quantity.position_change == base.position_change * 2
    assert doubled_quantity.vega_per_warrant_per_pp == base.vega_per_warrant_per_pp
    assert doubled_quantity.position_vega_per_pp == base.position_vega_per_pp * 2
    usd = revalue(
        inputs(currency="USD", underlying_currency="USD", strike_currency="USD"), scenario()
    )
    assert usd.position_change == base.position_change  # No implicit FX conversion.


@pytest.mark.parametrize("direction", ["CALL", "PUT"])
def test_both_vanilla_directions_have_positive_vega_and_iv_effect(direction):
    value = inputs(direction=direction)
    down = revalue(value, scenario())
    up = revalue(value, scenario(iv_change_pp=D(5)))
    assert down.position_change < 0 < up.position_change
    assert down.vega_per_warrant_per_pp > 0
    assert down.isolated_time_change == down.isolated_spot_change == 0
    assert down.change_per_warrant == down.isolated_iv_change
    assert (
        price_and_vega(value).vega_per_warrant_per_pp
        == price_and_vega(inputs()).vega_per_warrant_per_pp
    )


def test_large_and_combined_scenario_uses_full_repricing_and_payoff_at_expiry():
    large = revalue(
        inputs(),
        scenario(iv_change_pp=D(-15), underlying_change_percent=D(-10), elapsed_days=D(365)),
    )
    assert large.local_iv_change is None
    assert large.scenario_price == 0
    assert large.position_change == -large.baseline_price * 100
    assert "LARGE_IV_CHANGE_FULL_REVALUATION_ONLY" in large.warnings
    # A small absolute pp change can still be very large relative to starting IV.
    low_iv = revalue(inputs(iv_decimal=D(".01")), scenario(iv_change_pp=D(1)))
    assert low_iv.local_iv_change is None
    put = revalue(
        inputs(direction="PUT"),
        scenario(iv_change_pp=D(0), underlying_change_percent=D(-10), elapsed_days=D(365)),
    )
    assert put.scenario_price == 1  # Max(100-90,0)*0.1, no BSM dependency.
    combined = revalue(inputs(), scenario(underlying_change_percent=D(-5), elapsed_days=D(10)))
    assert (
        combined.change_per_warrant
        != combined.isolated_iv_change
        + combined.isolated_spot_change
        + combined.isolated_time_change
    )
    unchanged = revalue(inputs(), scenario(iv_change_pp=D(0)))
    assert unchanged.change_per_warrant == 0


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("product_type", "TURBO", "UNSUPPORTED_PRODUCT"),
        ("product_type", "INLINE", "UNSUPPORTED_PRODUCT"),
        ("product_type", "DISCOUNT", "UNSUPPORTED_PRODUCT"),
        ("exercise_style", "AMERICAN", "UNSUPPORTED_PRODUCT"),
        ("exercise_style", "UNKNOWN", "UNSUPPORTED_PRODUCT"),
        ("direction", "LONG", "UNSUPPORTED_DIRECTION"),
        ("quanto", True, "FX_OR_QUANTO"),
        ("underlying_currency", "USD", "FX_OR_QUANTO"),
        ("strike_currency", "USD", "FX_OR_QUANTO"),
        ("currency", "eur", "FX_OR_QUANTO"),
        ("dividend_model", "DISCRETE", "DISCRETE_DIVIDENDS"),
        ("ratio_convention", "WARRANTS_PER_UNDERLYING", "RATIO_CONVENTION"),
        ("spot", D("NaN"), "OUT_OF_RANGE"),
        ("strike", D(0), "OUT_OF_RANGE"),
        ("ratio", D(-1), "OUT_OF_RANGE"),
        ("iv_decimal", D(0), "OUT_OF_RANGE"),
        ("iv_decimal", D("Infinity"), "OUT_OF_RANGE"),
        ("remaining_days", D(-1), "OUT_OF_RANGE"),
    ],
)
def test_unsupported_cases_fail_closed(field, value, reason):
    with pytest.raises(ValueError, match=reason):
        inputs(**{field: value})


@pytest.mark.parametrize(
    "price,reason",
    [
        (D(0), "INVALID"),
        (D(-1), "INVALID"),
        (D("NaN"), "INVALID"),
        (D(10), "BOUNDS"),
        (D("1e-12"), "BOUNDS"),
    ],
)
def test_invalid_or_model_violating_prices(price, reason):
    with pytest.raises(ValueError, match=reason):
        solve_iv(inputs(), price)


def test_expiry_low_time_value_small_vega_no_solution_and_numerical_extremes():
    with pytest.raises(ValueError, match="INVALID"):
        solve_iv(inputs(remaining_days=D(0)), D(1))
    with pytest.raises(ValueError, match="TIME_VALUE_TOO_SMALL"):
        solve_iv(inputs(rate_decimal=D(0)), D("1e-12"))
    with pytest.raises(ValueError, match="IV_NOT_BRACKETED"):
        solve_iv(inputs(remaining_days=D(1)), D(9))
    with pytest.raises(ValueError, match="VEGA_TOO_SMALL"):
        solve_iv(inputs(ratio=D("1e-8")), D("1.045058357218556e-7"))
    tiny = revalue(inputs(spot=D(1), remaining_days=D(".01")), scenario(elapsed_days=D(0)))
    assert tiny.vega_per_warrant_per_pp is None and tiny.local_iv_change is None
    assert "SHORT_MATURITY_MODEL_SENSITIVE" in tiny.warnings
    assert tiny.baseline_price.is_finite() and tiny.scenario_price >= 0
    for s in (D(".00000001"), D("1e8")):
        assert price_and_vega(inputs(spot=s)).price.is_finite()
    with pytest.raises(ValueError, match="SCENARIO_HORIZON"):
        revalue(inputs(), scenario(elapsed_days=D(366)))
    with pytest.raises(ValueError, match="OUT_OF_RANGE"):
        scenario(quantity=D(0))
    with pytest.raises(ValueError, match="OUT_OF_RANGE"):
        revalue(inputs(), scenario(iv_change_pp=D(-20)))
