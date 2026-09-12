"""HEBELTRADER_RECONSTRUCTED_V1: deterministic, product-neutral plan calculations.

This is a reconstruction, not the publisher's undisclosed pricing algorithm.
All public prices are Decimal. No market-data access, persistence or execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal

POLICY_ID = "HEBELTRADER_RECONSTRUCTED_V1"
ZERO = Decimal("0")
ONE = Decimal("1")
HALF = Decimal("0.5")
MIN_STOCK_STOP_DISTANCE = Decimal("0.02")


def positive(value: Decimal, name: str, *, allow_zero: bool = False) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError(f"{name} must be a finite Decimal")
    if value < ZERO or (value == ZERO and not allow_zero):
        raise ValueError(f"{name} must be {'non-negative' if allow_zero else 'positive'}")


def round_down(value: Decimal, tick: Decimal) -> Decimal:
    """Round to an actual tick multiple, not just a number of decimal places."""
    positive(value, "price", allow_zero=True)
    positive(tick, "tick")
    return (value / tick).to_integral_value(rounding=ROUND_FLOOR) * tick


@dataclass(frozen=True, slots=True)
class Levels:
    entry: Decimal
    stop: Decimal
    target1: Decimal
    target2: Decimal

    def __post_init__(self) -> None:
        for name in ("entry", "stop", "target1", "target2"):
            positive(getattr(self, name), name)
        if not self.stop < self.entry < self.target1 < self.target2:
            raise ValueError("LONG levels require 0 < stop < entry < target1 < target2")

    @property
    def reward_risk(self) -> Decimal:
        return ((self.target1 + self.target2) / 2 - self.entry) / (self.entry - self.stop)


@dataclass(frozen=True, slots=True)
class BandDiagnostic:
    implied_base: Decimal
    relative_deviation: Decimal
    status: str


def diagnose_bands(levels: Levels, gd200: Decimal) -> BandDiagnostic:
    positive(gd200, "gd200")
    implied = 2 * levels.target1 - levels.target2
    deviation = abs(implied - gd200) / gd200
    status = "WITHIN_2_PERCENT" if deviation <= Decimal("0.02") else "REVIEW"
    return BandDiagnostic(implied, deviation, status)


def build_levels(
    *,
    entry: Decimal,
    gd200: Decimal,
    band_width: Decimal,
    support: Decimal,
    buffer_fraction: Decimal,
    tick: Decimal,
) -> Levels:
    """B and support are explicit reviewed inputs; never inferred from Omega.

    Buffer and rounding are implementation choices, not recovered publisher rules.
    """
    for value, name in (
        (entry, "entry"),
        (gd200, "gd200"),
        (band_width, "band_width"),
        (support, "support"),
    ):
        positive(value, name)
    positive(buffer_fraction, "buffer_fraction", allow_zero=True)
    if buffer_fraction >= ONE:
        raise ValueError("buffer_fraction must be below 1")
    if support >= entry:
        raise ValueError("support must be below entry")
    return Levels(
        entry=entry,
        stop=round_down(support * (ONE - buffer_fraction), tick),
        target1=round_down(gd200 + band_width, tick),
        target2=round_down(gd200 + 2 * band_width, tick),
    )


@dataclass(frozen=True, slots=True)
class EntryAssessment:
    eligible: bool
    reasons: tuple[str, ...]
    allocation_fraction: Decimal
    effective_stop: Decimal
    stock_stop_distance: Decimal
    reward_risk: Decimal | None
    late_entry: bool


def assess_entry(
    *,
    levels: Levels,
    stock_levels: Levels,
    stock_price: Decimal,
    gd200: Decimal,
    fundamental_ok: bool,
    bid: Decimal,
    ask: Decimal,
    target1_seen: bool = False,
    target2_seen: bool = False,
) -> EntryAssessment:
    """Bid triggers; ask is the prospective purchase price, in the same instrument.

    Historical target flags must come from the caller, not an invented price path.
    The 2% rule is ALWAYS measured on the underlying, never the warrant premium.
    """
    for value, name in (
        (stock_price, "stock_price"),
        (gd200, "gd200"),
        (bid, "bid"),
        (ask, "ask"),
    ):
        positive(value, name, allow_zero=name == "bid")
    if bid > ask:
        raise ValueError("bid must not exceed ask")
    if target2_seen and not target1_seen:
        raise ValueError("target2_seen requires target1_seen")
    late = target1_seen or bid >= levels.target1
    stop = max(levels.stop, levels.entry) if late else levels.stop
    stock_stop = max(stock_levels.stop, stock_levels.entry) if late else stock_levels.stop
    distance = (stock_price - stock_stop) / stock_price
    reasons: list[str] = []
    if not fundamental_ok:
        reasons.append("FUNDAMENTAL_REVIEW_REQUIRED")
    if stock_price <= gd200:
        reasons.append("STOCK_NOT_ABOVE_GD200")
    if distance < MIN_STOCK_STOP_DISTANCE:
        reasons.append("STOCK_STOP_DISTANCE_BELOW_2_PERCENT")
    if bid <= stop:
        reasons.append("STOP_ALREADY_REACHED")
    if target2_seen or ask >= levels.target2:
        reasons.append("TARGET2_ALREADY_REACHED_OR_NOT_ABOVE_ASK")
    if not late and ask >= levels.target1:
        reasons.append("SPREAD_CROSSES_TARGET1")
    risk = ask - stop
    reward = (levels.target2 if late else (levels.target1 + levels.target2) / 2) - ask
    rr = reward / risk if risk > ZERO and reward > ZERO else None
    if rr is None:
        reasons.append("NON_POSITIVE_REWARD_OR_RISK")
    return EntryAssessment(
        eligible=not reasons,
        reasons=tuple(reasons),
        allocation_fraction=ZERO if reasons else (HALF if late else ONE),
        effective_stop=stop,
        stock_stop_distance=distance,
        reward_risk=rr,
        late_entry=late,
    )
