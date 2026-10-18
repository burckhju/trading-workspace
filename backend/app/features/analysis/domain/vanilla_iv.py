"""European same-currency vanilla model. All inputs are explicit assumptions.

No provider access, trade recommendation, execution price or alert state.
See docs/features/IMPLIED_VOLATILITY.md for units, bounds and primary sources.
"""

import math
from dataclasses import dataclass, replace
from decimal import Decimal

D = Decimal
MODEL_VERSION = "BSM_CONTINUOUS_YIELD_ACT365_V1"


def fraction(percent: Decimal) -> Decimal:
    if not percent.is_finite():
        raise ValueError("NON_FINITE_INPUT")
    return percent / 100


def percentage_points(before: Decimal, after: Decimal) -> Decimal:
    """IV inputs are decimal fractions; return percentage points, not relative %."""
    if not before.is_finite() or not after.is_finite():
        raise ValueError("NON_FINITE_INPUT")
    return (after - before) * 100


def local_iv_effect(vega_per_warrant_per_pp: Decimal | None, change_pp: Decimal) -> Decimal:
    """Ratio already included in vega; quantity is intentionally not included."""
    if (
        vega_per_warrant_per_pp is None
        or not vega_per_warrant_per_pp.is_finite()
        or vega_per_warrant_per_pp <= 0
        or not change_pp.is_finite()
    ):
        raise ValueError("VEGA_OR_CHANGE_UNAVAILABLE")
    return vega_per_warrant_per_pp * change_pp


@dataclass(frozen=True, slots=True)
class VanillaInputs:
    product_type: str
    exercise_style: str
    direction: str
    spot: Decimal
    strike: Decimal
    ratio: Decimal
    remaining_days: Decimal
    iv_decimal: Decimal
    rate_decimal: Decimal
    dividend_yield_decimal: Decimal
    currency: str
    underlying_currency: str
    strike_currency: str
    quanto: bool
    dividend_model: str
    ratio_convention: str

    def __post_init__(self) -> None:
        if self.product_type != "VANILLA_WARRANT" or self.exercise_style != "EUROPEAN":
            raise ValueError("UNSUPPORTED_PRODUCT_OR_EXERCISE")
        if self.direction not in {"CALL", "PUT"}:
            raise ValueError("UNSUPPORTED_DIRECTION")
        if self.quanto is not False or not (
            self.currency == self.underlying_currency == self.strike_currency
            and len(self.currency) == 3
            and self.currency.isascii()
            and self.currency.isalpha()
            and self.currency.isupper()
        ):
            raise ValueError("FX_OR_QUANTO_UNSUPPORTED")
        if self.dividend_model != "CONTINUOUS_YIELD":
            raise ValueError("DISCRETE_DIVIDENDS_UNSUPPORTED")
        if self.ratio_convention != "UNDERLYING_UNITS_PER_WARRANT":
            raise ValueError("RATIO_CONVENTION_UNSUPPORTED")
        # Numerical scope, not empirical risk or trading thresholds.
        bounds = (
            (self.spot, D("0.00000001"), D("1e8")),
            (self.strike, D("0.00000001"), D("1e8")),
            (self.ratio, D("0.00000001"), D("1e4")),
            (self.remaining_days, D(0), D(3650)),
            (self.iv_decimal, D("0.000001"), D(5)),
            (self.rate_decimal, D("-.2"), D(1)),
            (self.dividend_yield_decimal, D(0), D(1)),
        )
        if any(not v.is_finite() or not lo <= v <= hi for v, lo, hi in bounds):
            raise ValueError("MODEL_INPUT_OUT_OF_RANGE")


@dataclass(frozen=True, slots=True)
class ModelValue:
    price: Decimal
    vega_per_warrant_per_pp: Decimal | None


def price_and_vega(inputs: VanillaInputs) -> ModelValue:
    s, k, ratio = float(inputs.spot), float(inputs.strike), float(inputs.ratio)
    t = float(inputs.remaining_days / 365)
    if t == 0:
        payoff = max(s - k if inputs.direction == "CALL" else k - s, 0) * ratio
        return ModelValue(D(str(payoff)), None)
    r, q, sigma = map(
        float, (inputs.rate_decimal, inputs.dividend_yield_decimal, inputs.iv_decimal)
    )
    sd, kd = s * math.exp(-q * t), k * math.exp(-r * t)
    d1 = (math.log(s / k) + (r - q + sigma * sigma / 2) * t) / (sigma * math.sqrt(t))
    d2 = d1 - sigma * math.sqrt(t)

    def cdf(x: float) -> float:
        # erfc retains accuracy in the negative tail, unlike 1 + erf(x).
        return math.erfc(-x / math.sqrt(2)) / 2

    # Price the OTM leg directly, then use parity for the ITM leg.
    if sd <= kd:
        call = max(0.0, sd * cdf(d1) - kd * cdf(d2))
        put = call + kd - sd
    else:
        put = max(0.0, kd * cdf(-d2) - sd * cdf(-d1))
        call = put + sd - kd
    vega = sd * math.exp(-d1 * d1 / 2) / math.sqrt(2 * math.pi) * math.sqrt(t) * ratio / 100
    return ModelValue(
        D(str((call if inputs.direction == "CALL" else put) * ratio)),
        D(str(vega)),
    )


def solve_iv(inputs: VanillaInputs, price_per_warrant: Decimal) -> Decimal:
    """Bounded bisection on [0.000001, 5]; fail instead of returning fake zero IV.

    Used only for explicitly hypothetical price calibration in this release.
    A real quote integration additionally requires the evidence gates in the concept.
    """
    if not price_per_warrant.is_finite() or price_per_warrant <= 0 or inputs.remaining_days <= 0:
        raise ValueError("IV_PRICE_OR_MATURITY_INVALID")
    t = float(inputs.remaining_days / 365)
    sd = float(inputs.spot) * math.exp(-float(inputs.dividend_yield_decimal) * t)
    kd = float(inputs.strike) * math.exp(-float(inputs.rate_decimal) * t)
    lower = max(sd - kd if inputs.direction == "CALL" else kd - sd, 0) * float(inputs.ratio)
    upper = (sd if inputs.direction == "CALL" else kd) * float(inputs.ratio)
    target = float(price_per_warrant)
    # Near a model bound, minute price errors imply huge/indeterminate IV errors.
    tolerance = max(1e-12, upper * 1e-10)
    if target < lower or target >= upper:
        raise ValueError("PRICE_OUTSIDE_MODEL_BOUNDS")
    if target - lower <= tolerance or upper - target <= tolerance:
        raise ValueError("TIME_VALUE_TOO_SMALL")
    lo, hi = D("0.000001"), D(5)
    if not (
        price_and_vega(replace(inputs, iv_decimal=lo)).price
        <= price_per_warrant
        <= price_and_vega(replace(inputs, iv_decimal=hi)).price
    ):
        raise ValueError("IV_NOT_BRACKETED")
    for _ in range(64):
        mid = (lo + hi) / 2
        value = price_and_vega(replace(inputs, iv_decimal=mid))
        if value.price < price_per_warrant:
            lo = mid
        else:
            hi = mid
    result = (lo + hi) / 2
    value = price_and_vega(replace(inputs, iv_decimal=result))
    if value.vega_per_warrant_per_pp is None or value.vega_per_warrant_per_pp <= D("1e-8"):
        raise ValueError("VEGA_TOO_SMALL")
    if abs(float(value.price) - target) > tolerance:
        raise ValueError("IV_SOLVER_RESIDUAL_TOO_LARGE")
    return result


@dataclass(frozen=True, slots=True)
class Scenario:
    underlying_change_percent: Decimal
    iv_change_pp: Decimal
    elapsed_days: Decimal
    quantity: Decimal

    def __post_init__(self) -> None:
        bounds = (
            (self.underlying_change_percent, D(-99), D(500)),
            (self.iv_change_pp, D(-500), D(500)),
            (self.elapsed_days, D(0), D(3650)),
            (self.quantity, D("0.00000001"), D("1e9")),
        )
        if any(not v.is_finite() or not lo <= v <= hi for v, lo, hi in bounds):
            raise ValueError("SCENARIO_INPUT_OUT_OF_RANGE")


@dataclass(frozen=True, slots=True)
class ScenarioValue:
    inputs: VanillaInputs
    scenario: Scenario
    baseline_price: Decimal
    scenario_price: Decimal
    change_per_warrant: Decimal
    position_change: Decimal
    vega_per_warrant_per_pp: Decimal | None
    position_vega_per_pp: Decimal | None
    local_iv_change: Decimal | None
    isolated_iv_change: Decimal
    isolated_spot_change: Decimal
    isolated_time_change: Decimal
    warnings: tuple[str, ...]
    iv_origin: str = "USER_ASSUMPTION"
    model_version: str = MODEL_VERSION
    status: str = "HYPOTHETICAL"
    execution_usable: bool = False


def revalue(inputs: VanillaInputs, scenario: Scenario) -> ScenarioValue:
    if inputs.remaining_days <= 0 or scenario.elapsed_days > inputs.remaining_days:
        raise ValueError("SCENARIO_HORIZON_INVALID")
    spot = inputs.spot * (1 + fraction(scenario.underlying_change_percent))
    iv = inputs.iv_decimal + fraction(scenario.iv_change_pp)
    days = inputs.remaining_days - scenario.elapsed_days
    base = price_and_vega(inputs)
    combined = price_and_vega(replace(inputs, spot=spot, iv_decimal=iv, remaining_days=days))
    warnings = []
    vega = base.vega_per_warrant_per_pp
    if vega is None or vega <= D("1e-8"):
        warnings.append("VEGA_TOO_SMALL")
        vega = None
    if inputs.remaining_days < 7:
        warnings.append("SHORT_MATURITY_MODEL_SENSITIVE")
    # Suppress local linear extrapolation for larger changes. Full repricing always used.
    local = None
    if (
        abs(scenario.iv_change_pp) > 5
        or abs(fraction(scenario.iv_change_pp)) > inputs.iv_decimal / 4
    ):
        warnings.append("LARGE_IV_CHANGE_FULL_REVALUATION_ONLY")
    elif vega is not None:
        local = local_iv_effect(vega, scenario.iv_change_pp)
    return ScenarioValue(
        inputs,
        scenario,
        base.price,
        combined.price,
        combined.price - base.price,
        (combined.price - base.price) * scenario.quantity,
        vega,
        vega * scenario.quantity if vega is not None else None,
        local,
        price_and_vega(replace(inputs, iv_decimal=iv)).price - base.price,
        price_and_vega(replace(inputs, spot=spot)).price - base.price,
        price_and_vega(replace(inputs, remaining_days=days)).price - base.price,
        tuple(warnings),
    )
