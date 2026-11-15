"""A passive consumer of execution-owned entry and document-backed session facts."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal
from uuid import UUID

from app.features.market_data.domain.session_evidence import SessionDay, SessionEvidenceCurrent
from app.features.position_monitoring.domain.hebeltrader_sessions import (
    CompletedSessionCount,
    SessionEntry,
)


@dataclass(frozen=True, slots=True)
class SessionIssue:
    code: str
    detail: str


@dataclass(frozen=True, slots=True)
class SessionPeriodView:
    start_date: date | None
    end_date: date | None
    status: Literal[
        "COMPLETE", "INCOMPLETE", "MISSING", "UNSUITABLE", "LIMIT_EXCEEDED", "NOT_REQUESTED"
    ]
    fingerprint: str | None
    missing_dates: tuple[date, ...]
    days: tuple[SessionDay, ...]


@dataclass(frozen=True, slots=True)
class HebeltraderSessionsReport:
    trade_id: UUID
    position_id: UUID
    product_id: UUID
    underlying_id: UUID
    position_state: Literal["OPEN", "CLOSED", "CANCELLED"]
    basis_id: str
    read_started_at: datetime
    read_completed_at: datetime
    evaluated_at: datetime
    entry: SessionEntry | None
    calendar: SessionEvidenceCurrent
    period: SessionPeriodView
    count: CompletedSessionCount
    issues: tuple[SessionIssue, ...]
    notices: tuple[str, ...]
    definition_version: Literal["hebeltrader-sessions-v1"] = "hebeltrader-sessions-v1"
    baseline_id: Literal["HEBELTRADER_CONFIRMED_BASELINE"] = "HEBELTRADER_CONFIRMED_BASELINE"
    baseline_version: Literal["1.0.0"] = "1.0.0"
    implementation_status: Literal["F207_3_SESSION_EVIDENCE_AND_COUNT_ONLY"] = (
        "F207_3_SESSION_EVIDENCE_AND_COUNT_ONLY"
    )
    rule_evaluation_status: Literal["B04_B05_B06_B58_NOT_EVALUATED"] = (
        "B04_B05_B06_B58_NOT_EVALUATED"
    )
    operation_status: Literal["NOT_ACTIVATED"] = "NOT_ACTIVATED"
    read_status: Literal["READ_ONLY"] = "READ_ONLY"
