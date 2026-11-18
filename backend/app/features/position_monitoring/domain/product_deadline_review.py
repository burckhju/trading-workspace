"""Documented product-date reminders, deliberately short of full B05/B20.

This version has no price or market-status prerequisite. The Product owner
qualifies the term dates and explicit exit listing; the existing calendar
calculation provides the twenty-session boundary and preceding-session warning.
A session's closing time is disclosed as a calendar fact, never as a verified
instrument-specific execution cutoff.
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from app.features.position_monitoring.domain.hebeltrader_deadlines import (
    ProductDeadlineCalculation,
)
from app.features.position_monitoring.domain.product_deadline_days import (
    ProductDeadlineDayCalculation,
)

RULE_VERSION = "product-deadline-review-v1"
RULE_SCOPE = "DOCUMENTED_PRODUCT_DEADLINE_REVIEW_V1"
RULE_KEY = f"{RULE_SCOPE}:{RULE_VERSION}"
ACTIVATION_SCOPE = "INDICATIVE_ENTRY_V2"

type DeadlineOutcome = Literal[
    "CLOSED",
    "UNAVAILABLE",
    "BEFORE_WARNING",
    "WARNING_DUE",
    "EXIT_SESSION_STARTED",
    "CALENDAR_SESSION_ENDED",
    "WARNING_DAY_REACHED",
    "DEADLINE_DAY_REACHED",
    "DEADLINE_DAY_PASSED",
]
type DeadlineEpisodeKind = Literal["DEADLINE_REVIEW", "DATA_UNAVAILABLE"]
EPISODE_KINDS: tuple[DeadlineEpisodeKind, ...] = ("DEADLINE_REVIEW", "DATA_UNAVAILABLE")


@dataclass(frozen=True, slots=True)
class ProductDeadlineDecision:
    outcome: DeadlineOutcome
    reasons: tuple[str, ...]
    calculation: ProductDeadlineCalculation | ProductDeadlineDayCalculation | None
    scheduled_at: datetime | None
    reminder_due: bool | None
    scheduled_on: date | None = None
    qualified_b05: Literal[False] = False
    product_cutoff_status: Literal["UNVERIFIED"] = "UNVERIFIED"
    decision_kind: Literal["POSITION_REVIEW"] = "POSITION_REVIEW"
    scope: str = RULE_SCOPE
    rule_version: str = RULE_VERSION


def decide_product_deadline_review(
    *,
    closed: bool,
    calculation: ProductDeadlineCalculation | ProductDeadlineDayCalculation | None,
    input_problems: tuple[str, ...] = (),
) -> ProductDeadlineDecision:
    """Assess the current stage only; never reconstruct earlier deliveries.

    An absent or withdrawn input does not prove that an earlier deadline event
    ceased to exist. The separate data episode preserves that uncertainty;
    `reminder_due=None` keeps the prior event visible, while delivery validation
    must recheck the premise before any external send.
    """
    if closed:
        return ProductDeadlineDecision("CLOSED", (), None, None, False)
    problems = tuple(
        dict.fromkeys(
            (
                *input_problems,
                *(calculation.reasons if calculation is not None else ()),
            )
        )
    )
    if input_problems or calculation is None or calculation.status == "NOT_ASSESSABLE":
        return ProductDeadlineDecision(
            "UNAVAILABLE",
            problems or ("PRODUCT_DEADLINE_INPUTS_MISSING",),
            calculation,
            None,
            None,
        )
    stage = calculation.stage
    if stage is None:
        # Exactly twenty documented sessions establish the calendar day, but
        # not a B19 warning beforehand. Do not invent a twenty-four-hour offset.
        return ProductDeadlineDecision(
            "UNAVAILABLE",
            problems or ("PREWARNING_PRODUCT_SESSION_MISSING",),
            calculation,
            None,
            None,
        )
    scheduled_at = {
        "BEFORE_WARNING": None,
        "WARNING_DUE": calculation.warning_at,
        "EXIT_SESSION_STARTED": calculation.exit_session_opens_at,
        "CALENDAR_SESSION_ENDED": calculation.calendar_session_closes_at,
        "WARNING_DAY_REACHED": None,
        "DEADLINE_DAY_REACHED": None,
        "DEADLINE_DAY_PASSED": None,
    }[stage]
    return ProductDeadlineDecision(
        stage,
        problems,
        calculation,
        scheduled_at,
        stage != "BEFORE_WARNING",
        scheduled_on=(
            calculation.warning_session_date
            if stage == "WARNING_DAY_REACHED"
            else (
                calculation.exit_session_date
                if stage in {"DEADLINE_DAY_REACHED", "DEADLINE_DAY_PASSED"}
                else None
            )
        ),
    )


def desired_deadline_episode(
    kind: DeadlineEpisodeKind, decision: ProductDeadlineDecision
) -> bool | None:
    if decision.outcome == "CLOSED":
        return False
    if kind == "DATA_UNAVAILABLE":
        return decision.outcome == "UNAVAILABLE"
    return decision.reminder_due
