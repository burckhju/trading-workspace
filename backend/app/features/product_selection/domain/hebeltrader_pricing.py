"""Explicit European-call model scenarios; never executable issuer quotes.

Black-Scholes-Merton with continuous dividend yield, ACT/365, and explicit FX.
Not suitable for American exercise, quanto, barriers, or issuer credit modelling.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from math import erf, exp, log, sqrt

from app.features.trade_plan.domain.hebeltrader import positive


def european_call_scenario(
    *,
    spot: Decimal,
    strike: Decimal,
    ratio: Decimal,
    valuation_date: date,
    exercise_date: date,
    implied_volatility: Decimal,
    risk_free_rate: Decimal,
    dividend_yield: Decimal,
    fx_quote_per_underlying: Decimal,
) -> Decimal:
    """All underlying amounts in the same major currency unit (not mixed GBP/GBp).

    IV is an explicit scenario input, not historical volatility. FX is units of the
    warrant quote currency per ONE unit of the underlying currency. No Omega input.
    """
    for value, name in (
        (spot, "spot"),
        (strike, "strike"),
        (ratio, "ratio"),
        (fx_quote_per_underlying, "fx_quote_per_underlying"),
    ):
        positive(value, name)
        if not Decimal("1e-12") <= value <= Decimal("1e12"):
            raise ValueError(f"{name} outside supported numerical range")
    positive(implied_volatility, "implied_volatility", allow_zero=True)
    if implied_volatility > Decimal("5"):
        raise ValueError("implied_volatility must be a fraction between 0 and 5")
    for value in (risk_free_rate, dividend_yield):
        if not isinstance(value, Decimal) or not value.is_finite() or abs(value) > 1:
            raise ValueError("rates must be finite Decimal fractions between -1 and 1")
    days = (exercise_date - valuation_date).days
    if not 0 <= days <= 365 * 50:
        raise ValueError("valuation must be on/before exercise and within 50 years")
    if days == 0:
        return max(spot - strike, Decimal("0")) * ratio * fx_quote_per_underlying
    time = days / 365
    s, k = float(spot), float(strike)
    r, q, vol = float(risk_free_rate), float(dividend_yield), float(implied_volatility)
    discounted_spot, discounted_strike = s * exp(-q * time), k * exp(-r * time)
    vol_time = vol * sqrt(time)
    if vol_time == 0:
        price = max(discounted_spot - discounted_strike, 0.0)
    else:
        d1 = (log(s / k) + (r - q + vol * vol / 2) * time) / vol_time
        d2 = d1 - vol_time
        n1, n2 = (1 + erf(d1 / sqrt(2))) / 2, (1 + erf(d2 / sqrt(2))) / 2
        price = max(discounted_spot * n1 - discounted_strike * n2, 0.0)
    result = Decimal(str(price)) * ratio * fx_quote_per_underlying
    if not result.is_finite():
        raise ValueError("non-finite theoretical valuation")
    return result
