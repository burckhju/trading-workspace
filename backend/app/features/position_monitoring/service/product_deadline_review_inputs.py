"""Price-independent composition of the economic, Product and calendar owners."""

from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ApplicationError
from app.features.market_data.domain.session_evidence import MAX_SESSION_DAYS, SessionEvidenceRead
from app.features.market_data.service.session_evidence import SessionEvidenceReader
from app.features.position_monitoring.domain.hebeltrader_deadlines import (
    ProductDeadlineCalculation,
    calculate_product_deadline,
)
from app.features.position_monitoring.domain.product_deadline_days import (
    ProductDeadlineDayCalculation,
    calculate_product_day_deadline,
)
from app.features.position_monitoring.service.hebeltrader_original_bid_sessions import (
    current_calendar,
    read_period,
)
from app.features.product.domain.review_evidence import ProductDeadlineEvidence
from app.features.product.service.application import WarrantService
from app.features.product.service.review_evidence import ProductReviewEvidenceReader
from app.features.trade_position.persistence.repositories import (
    SqlAlchemyPositionRepository,
    SqlAlchemyReadOnlyTradeRepository,
)
from app.features.trade_position.service.valuation_basis import read_position_execution_basis

JSON_VALUE = TypeAdapter(dict[str, Any])


@dataclass(frozen=True, slots=True)
class ProductDeadlineInputs:
    workspace_id: UUID
    trade_id: UUID
    position_id: UUID
    warrant_id: UUID
    owner_basis_id: str
    closed: bool
    calculation: ProductDeadlineCalculation | ProductDeadlineDayCalculation | None
    material: dict[str, Any]
    problems: tuple[str, ...]


def product_deadline_evidence_problems(
    evidence: ProductDeadlineEvidence,
    *,
    workspace_id: UUID,
    warrant_id: UUID,
    now: datetime,
) -> tuple[str, ...]:
    """Validate owner scope and provenance without claiming independent review."""
    if evidence.workspace_id != workspace_id or evidence.warrant_id != warrant_id:
        return ("PRODUCT_DEADLINE_OWNER_SCOPE_MISMATCH",)
    problems = list(evidence.reasons)
    if evidence.status != "AVAILABLE":
        problems.append("PRODUCT_DEADLINE_EVIDENCE_UNAVAILABLE")
    if (
        evidence.known_at.utcoffset() is None
        or evidence.known_at != now
        or evidence.recorded_at is None
        or evidence.recorded_at.utcoffset() is None
        or evidence.recorded_at.astimezone(UTC) > now.astimezone(UTC)
    ):
        problems.append("PRODUCT_DEADLINE_KNOWLEDGE_TIME_INVALID")
    if (
        evidence.revision_id is None
        or not evidence.fingerprint
        or evidence.terms_id is None
        or not evidence.source_reference
        or not evidence.verification
    ):
        problems.append("PRODUCT_DEADLINE_PROVENANCE_MISSING")
    if evidence.maturity_on is None:
        problems.append("PRODUCT_MATURITY_EVIDENCE_MISSING")
    if evidence.last_trading_on is None:
        problems.append("PRODUCT_LAST_TRADING_DAY_EVIDENCE_MISSING")
    if evidence.exit_listing_id is None or not evidence.exit_venue_mic:
        problems.append("PRODUCT_EXIT_LISTING_MISSING")
    return tuple(dict.fromkeys(problems))


async def _calendar(
    reader: SessionEvidenceReader,
    evidence: ProductDeadlineEvidence,
    *,
    now: datetime,
) -> tuple[SessionEvidenceRead | None, dict[str, Any], tuple[str, ...]]:
    """Read an exact documented range; never derive an exit listing or days."""
    assert evidence.exit_listing_id is not None
    assert evidence.maturity_on is not None and evidence.last_trading_on is not None
    current = await current_calendar(
        reader,
        workspace_id=evidence.workspace_id,
        kind="WARRANT",
        instrument_id=evidence.warrant_id,
        now=now,
        listing_id=evidence.exit_listing_id,
    )
    material: dict[str, Any] = {"current": asdict(current), "period": None}
    if current.status != "AVAILABLE" or current.binding is None:
        return (
            None,
            material,
            ("PRODUCT_SESSION_EVIDENCE_UNSUITABLE", *current.reasons),
        )
    if current.binding.venue_mic != evidence.exit_venue_mic:
        return None, material, ("PRODUCT_EXIT_CALENDAR_VENUE_MISMATCH",)
    terminal = min(evidence.maturity_on, evidence.last_trading_on)
    if terminal == date.min:
        return None, material, ("PRODUCT_DATE_HAS_NO_PRECEDING_SESSION_RANGE",)
    end = terminal - timedelta(days=1)
    start = current.coverage_start
    if start is None or start > end:
        return None, material, ("PRODUCT_SESSION_RANGE_INCOMPLETE",)
    if (end - start).days >= MAX_SESSION_DAYS:
        return None, material, ("PRODUCT_SESSION_RANGE_LIMIT",)
    period, read = await read_period(reader, current, start=start, end=end)
    material["period"] = asdict(period)
    return read, material, ()


async def read_product_deadline_inputs(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    trade_id: UUID,
    position_id: UUID,
    now: datetime,
) -> ProductDeadlineInputs:
    """Read existing owner facts inside the caller's consistent snapshot.

    No quote, target evidence, cost-basis currency or price-scale prerequisite is
    introduced for a price-independent date reminder. The existing execution
    owner alone determines whether the position remains open.
    """
    trade = await SqlAlchemyReadOnlyTradeRepository(session).get(workspace_id, trade_id)
    saved_position = await SqlAlchemyPositionRepository(session).get_for_trade(
        workspace_id, trade_id
    )
    if trade is None or saved_position is None or saved_position.id != position_id:
        raise ApplicationError(
            code="PRODUCT_DEADLINE_POSITION_NOT_FOUND",
            message="Position nicht gefunden.",
            status_code=404,
        )
    basis = await read_position_execution_basis(session, trade=trade, position_id=position_id)
    economic = basis.valuation_basis
    position = economic.position
    closed = position.is_closed or position.is_cancelled or trade.cancelled_at is not None
    warrant = await WarrantService(session).get(workspace_id, trade.product_id)
    material: dict[str, Any] = {
        "economic_basis": asdict(economic),
        "effective_execution_ids": [str(fact.id) for fact in basis.effective_executions],
        "warrant_id": str(trade.product_id),
        "warrant_name": warrant.display_name,
        "warrant_isin": warrant.isin,
        "warrant_wkn": warrant.wkn,
    }
    calculation: ProductDeadlineCalculation | ProductDeadlineDayCalculation | None = None
    problems: list[str] = []
    if not closed:
        evidence = await ProductReviewEvidenceReader(session).deadline_for_review(
            workspace_id=workspace_id, warrant_id=trade.product_id, known_at=now
        )
        material["product_evidence"] = asdict(evidence)
        problems.extend(
            product_deadline_evidence_problems(
                evidence, workspace_id=workspace_id, warrant_id=trade.product_id, now=now
            )
        )
        if not problems:
            calendar, calendar_material, calendar_problems = await _calendar(
                SessionEvidenceReader(session), evidence, now=now
            )
            material["product_calendar"] = calendar_material
            current = calendar_material["current"]
            if (
                current["status"] == "MISSING"
                and current.get("revision_id") is None
                and tuple(current.get("reasons", ())) == ("SESSION_EVIDENCE_MISSING",)
            ):
                # A separate owner supplies explicit original session dates.
                # This cannot bypass withdrawn/conflicting timed evidence or
                # manufacture instrument hours from a venue-wide timetable.
                from app.features.market_data.service.review_calendars import (
                    read_review_deadline_calendar,
                )

                assert evidence.exit_listing_id is not None
                assert evidence.exit_venue_mic is not None
                day_calendar = await read_review_deadline_calendar(
                    session,
                    workspace_id=workspace_id,
                    warrant_id=trade.product_id,
                    listing_id=evidence.exit_listing_id,
                    venue_mic=evidence.exit_venue_mic,
                    known_at=now,
                )
                material["product_day_calendar"] = asdict(day_calendar)
                if day_calendar.known_at != now:
                    problems.append("PRODUCT_DAY_CALENDAR_SNAPSHOT_INCONSISTENT")
                calculation = calculate_product_day_deadline(
                    workspace_id=workspace_id,
                    warrant_id=trade.product_id,
                    exit_listing_id=evidence.exit_listing_id,
                    exit_venue_mic=evidence.exit_venue_mic,
                    maturity_on=evidence.maturity_on,
                    last_trading_on=evidence.last_trading_on,
                    calendar=day_calendar,
                    event_at=now,
                )
            else:
                problems.extend(calendar_problems)
                calculation = calculate_product_deadline(
                    workspace_id=workspace_id,
                    warrant_id=trade.product_id,
                    exit_listing_id=evidence.exit_listing_id,
                    maturity_on=evidence.maturity_on,
                    last_trading_on=evidence.last_trading_on,
                    calendar=calendar,
                    event_at=now,
                )
        clocks = (trade.created_at, *(fact.recorded_at for fact in basis.history))
        if any(clock.utcoffset() is None or clock.astimezone(UTC) > now for clock in clocks):
            problems.append("PRODUCT_DEADLINE_OWNER_FACT_AFTER_EVALUATION")
    return ProductDeadlineInputs(
        workspace_id,
        trade_id,
        position_id,
        trade.product_id,
        economic.basis_id,
        closed,
        calculation,
        JSON_VALUE.dump_python(material, mode="json"),
        tuple(dict.fromkeys(problems)),
    )
