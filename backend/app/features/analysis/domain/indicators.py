"""Numerical kernels shared by versioned analysis policies.

These preserve the released EOD_TREND_MOMENTUM 1.0.0 arithmetic, including
its float logarithm/statistics step. Prices and ratios remain Decimal.
"""

from decimal import Decimal, localcontext
from math import log, sqrt


def simple_average(values: list[Decimal], window: int) -> Decimal:
    return sum(values[-window:], Decimal(0)) / Decimal(window)


def realized_volatility(
    values: list[Decimal], window: int, annualization_factor: Decimal
) -> Decimal:
    returns = [
        log(float(values[i] / values[i - 1])) for i in range(len(values) - window, len(values))
    ]
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / max(len(returns) - 1, 1)
    with localcontext() as context:
        context.prec = 28
        return Decimal(str(sqrt(variance))) * annualization_factor.sqrt()
