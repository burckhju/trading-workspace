"""Versioned B04/B57 decisions; never a portfolio calculator or trading command."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

RULE_VERSION = "hebeltrader-b04-b57-v1"
RULE_SCOPE = "B04_B57_WITH_B58_INPUTS"
RULE_KEY = f"{RULE_SCOPE}:{RULE_VERSION}"
BASELINE_ID = "HEBELTRADER_CONFIRMED_BASELINE"
BASELINE_VERSION = "1.0.0"
MISSING_RULES = ("B05", "B06", "F207_2_PROTECTION", "F207_5_LIFECYCLE_ACCEPTANCE")


@dataclass(frozen=True, slots=True)
class LossDecision:
    outcome: Literal["LOSS", "RECOVERED", "NOT_ASSESSABLE", "NOT_REACHED", "CLOSED"]
    reasons: tuple[str, ...]
    bid: Decimal | None
    gross_entry: Decimal
    bid_at: datetime | None
    remaining_quantity: int
    completed_sessions_at_bid: int | None


def decide_loss(
    *,
    closed: bool,
    bid: Decimal | None,
    gross_entry: Decimal,
    bid_at: datetime | None,
    remaining_quantity: int,
    completed_sessions_at_bid: int | None,
    input_problems: tuple[str, ...],
) -> LossDecision:
    """Consume already qualified owner inputs, without adding target prerequisites.

    Unknown data is deliberately distinct from recovery. Only a qualified BID
    at or above the existing gross entry can end the loss condition.
    """
    outcome: Literal["LOSS", "RECOVERED", "NOT_ASSESSABLE", "NOT_REACHED", "CLOSED"]
    reasons: tuple[str, ...]
    if closed or remaining_quantity == 0:
        outcome, reasons = "CLOSED", ("POSITION_CLOSED_OR_CANCELLED",)
    elif input_problems:
        outcome, reasons = "NOT_ASSESSABLE", tuple(dict.fromkeys(input_problems))
    elif bid is None or bid_at is None or completed_sessions_at_bid is None:
        outcome, reasons = "NOT_ASSESSABLE", ("B04_REQUIRED_INPUT_MISSING",)
    elif completed_sessions_at_bid < 20:
        outcome, reasons = "NOT_REACHED", ("TWENTIETH_SESSION_NOT_COMPLETED_AT_BID",)
    elif not bid.is_finite() or bid < 0 or not gross_entry.is_finite() or gross_entry <= 0:
        outcome, reasons = "NOT_ASSESSABLE", ("B04_PRICE_INVALID",)
    elif bid < gross_entry:
        outcome, reasons = "LOSS", ("B04_BID_BELOW_GROSS_ENTRY",)
    else:
        outcome, reasons = "RECOVERED", ("B57_QUALIFIED_BID_AT_OR_ABOVE_ENTRY",)
    return LossDecision(
        outcome,
        reasons,
        bid,
        gross_entry,
        bid_at,
        remaining_quantity,
        completed_sessions_at_bid,
    )
