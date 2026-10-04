"""Versioned descriptive signal state. No trade, stop, order or delivery mutations."""

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

from app.features.analysis.domain.risk_analytics import RiskMetrics, weekday_gap

RISK_POLICY_VERSION = "POSITION_RISK_V1"


@dataclass(frozen=True, slots=True)
class RiskParameters:
    hysteresis_fraction: Decimal = Decimal("0.005")
    confirmation_sessions: int = 2
    volatility_high: Decimal = Decimal("0.40")
    volatility_reset: Decimal = Decimal("0.35")
    maximum_age_days: int = 4

    def __post_init__(self) -> None:
        values = (self.hysteresis_fraction, self.volatility_high, self.volatility_reset)
        if any(not v.is_finite() for v in values):
            raise ValueError("risk parameters must be finite")
        if not Decimal(0) <= self.hysteresis_fraction <= Decimal("0.05"):
            raise ValueError("hysteresis must be between 0 and 0.05")
        if not 1 <= self.confirmation_sessions <= 5 or not 1 <= self.maximum_age_days <= 10:
            raise ValueError("unsupported confirmation/age parameter")
        if not Decimal(0) < self.volatility_reset < self.volatility_high <= Decimal(5):
            raise ValueError("require 0 < volatility reset < high <= 5")


@dataclass(frozen=True, slots=True)
class RiskState:
    session: date | None = None
    trend: str = "UNINITIALIZED"
    pending: str | None = None
    pending_sessions: int = 0
    continuous: bool = False
    # A first adverse snapshot is not a demonstrated crossing.
    trend_warning: bool = False
    volatility_warning: bool = False


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    state: RiskState
    transition: str
    direction: str
    interpretation: str
    trend_triggered: bool | None
    volatility_triggered: bool | None
    reason: str
    policy_version: str = RISK_POLICY_VERSION


def assess_risk(
    metrics: RiskMetrics,
    *,
    direction: str | None,
    parameters: RiskParameters,
    previous: RiskState | None,
) -> RiskAssessment:
    old = previous or RiskState()
    if (
        metrics.status != "AVAILABLE"
        or metrics.session is None
        or metrics.distance_sma20 is None
        or metrics.realized_volatility20 is None
    ):
        return RiskAssessment(
            replace(old, continuous=False, pending=None, pending_sessions=0),
            "NOT_EVALUABLE",
            direction or "UNKNOWN",
            "NOT_EVALUABLE",
            None,
            None,
            metrics.reason,
        )
    if old.session is not None and metrics.session <= old.session:
        return RiskAssessment(
            old,
            "SAME_OR_OLDER_SESSION",
            direction or "UNKNOWN",
            _interpret(old.trend, direction),
            None,
            None,
            "NO_ADDITIONAL_CONFIRMATION_SESSION",
        )
    distance = metrics.distance_sma20
    band = parameters.hysteresis_fraction
    candidate = "ABOVE" if distance > band else "BELOW" if distance < -band else "IN_BAND"
    high_volatility = metrics.realized_volatility20 >= parameters.volatility_high
    low_volatility = metrics.realized_volatility20 <= parameters.volatility_reset
    volatility_warning = high_volatility or (old.volatility_warning and not low_volatility)
    if old.trend == "UNINITIALIZED":
        state = RiskState(
            metrics.session, candidate, continuous=True, volatility_warning=volatility_warning
        )
        return RiskAssessment(
            state,
            "INITIALIZED",
            direction or "UNKNOWN",
            _interpret(candidate, direction),
            None,
            None,
            "FIRST_SNAPSHOT_IS_NOT_A_TREND_BREAK",
        )
    continuous = (
        old.continuous and old.session is not None and not weekday_gap(old.session, metrics.session)
    )
    pending, count = None, 0
    trend, transition = old.trend, "UNCHANGED"
    if candidate not in {old.trend, "IN_BAND"}:
        pending = candidate
        count = old.pending_sessions + 1 if continuous and old.pending == candidate else 1
        transition = "CONFIRMING"
        if count >= parameters.confirmation_sessions:
            trend, pending, count = candidate, None, 0
            transition = "CROSSED_BELOW" if trend == "BELOW" else "CROSSED_ABOVE"
    warning = old.trend_warning
    if transition.startswith("CROSSED_"):
        warning = _interpret(trend, direction) == "UNFAVORABLE"
    state = RiskState(metrics.session, trend, pending, count, True, warning, volatility_warning)
    return RiskAssessment(
        state,
        transition,
        direction or "UNKNOWN",
        _interpret(trend, direction),
        warning if direction in {"CALL", "PUT"} else None,
        volatility_warning,
        "CONFIRMED_SESSION_STATE" if continuous else "CONFIRMATION_RESTARTED_AFTER_GAP",
    )


def _interpret(trend: str, direction: str | None) -> str:
    if direction not in {"CALL", "PUT"}:
        return "DIRECTION_UNKNOWN"
    if trend not in {"ABOVE", "BELOW"}:
        return "NEUTRAL"
    return "FAVORABLE" if ((trend == "ABOVE") == (direction == "CALL")) else "UNFAVORABLE"
