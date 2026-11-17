"""Compose existing economic, route, product and session facts for review only."""

from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ApplicationError
from app.features.market_data.domain.risk_evidence import SavedQuoteEvidence
from app.features.market_data.domain.status_observations import (
    StatusEvidenceRead,
    StatusRouteBinding,
)
from app.features.market_data.persistence.models import (
    PositionQuoteSourceSelectionModel,
)
from app.features.market_data.service.risk_read import RiskMarketDataReader
from app.features.market_data.service.session_evidence import SessionEvidenceReader
from app.features.market_data.service.status_observations import MarketStatusReader
from app.features.position_monitoring.domain.hebeltrader_product_price_scale import (
    PurchaseScaleInput,
    assess_product_price_scale,
)
from app.features.position_monitoring.domain.hebeltrader_sessions import (
    CompletedSessionCount,
    SessionEntry,
    count_completed_sessions,
    session_anchor,
    unavailable_session_count,
)
from app.features.position_monitoring.domain.indicative_entry import (
    IndicativeQuote,
    qualify_review_quote,
)
from app.features.position_monitoring.service.hebeltrader_original_bid_sessions import (
    current_calendar,
    empty_period,
    read_period,
)
from app.features.product.domain.price_scale_evidence import ProductPriceScaleCurrent
from app.features.product.service.application import WarrantService
from app.features.product.service.price_scale_evidence import (
    ProductPriceScaleEvidenceReader,
)
from app.features.trade_position.domain.enums import ExecutionSide
from app.features.trade_position.persistence.repositories import (
    SqlAlchemyPositionRepository,
    SqlAlchemyReadOnlyTradeRepository,
)
from app.features.trade_position.service.valuation_basis import (
    PositionExecutionBasis,
    read_position_execution_basis,
)

JSON_VALUE = TypeAdapter(dict[str, Any])


def status_point_context(material: dict[str, Any]) -> dict[str, str | None]:
    """Expose last received source points with clocks, never current validity."""
    status = material.get("status_observations") or {}
    observations = [item for item in status.get("latest_observations", ()) if item.get("original")]
    captured = status.get("latest_capture")
    if captured and captured.get("original"):
        observations.append(captured)
    latest = max(
        (datetime.fromisoformat(item["captured_at"]) for item in observations),
        default=None,
    )
    points = [
        item for item in observations if datetime.fromisoformat(item["captured_at"]) == latest
    ]
    return {
        "source_status_point": ",".join(sorted({item["original"]["status"] for item in points}))
        or None,
        "source_status_observed_at": ",".join(
            sorted({item["original"]["observed_at"] for item in points})
        )
        or None,
        "source_status_captured_at": latest.isoformat() if latest else None,
        "status_validity": "NOT_ESTABLISHED",
    }


@dataclass(frozen=True, slots=True)
class IndicativeInputs:
    workspace_id: UUID
    trade_id: UUID
    position_id: UUID
    owner_basis_id: str
    closed: bool
    saved: SavedQuoteEvidence
    quote: IndicativeQuote
    review_count: CompletedSessionCount | None
    comparison_count: CompletedSessionCount | None
    material: dict[str, Any]
    problems: tuple[str, ...]


async def _sessions(
    reader: SessionEvidenceReader,
    *,
    workspace_id: UUID,
    underlying_id: UUID,
    entry: SessionEntry | None,
    now: datetime,
    event_at: datetime,
) -> tuple[CompletedSessionCount, dict[str, Any]]:
    current = await current_calendar(
        reader,
        workspace_id=workspace_id,
        kind="UNDERLYING",
        instrument_id=underlying_id,
        now=now,
    )
    anchor = session_anchor(entry, current.binding, event_at=event_at)
    problems = tuple(dict.fromkeys((*current.reasons, *anchor.reasons)))
    period = empty_period()
    if current.status != "AVAILABLE" or current.binding is None or problems:
        count = unavailable_session_count(
            event_at=event_at,
            anchor_date=anchor.day,
            reasons=problems or ("SESSION_BINDING_MISSING",),
        )
    else:
        assert anchor.day is not None
        end = event_at.astimezone(ZoneInfo(current.binding.timezone)).date()
        if end > anchor.day:
            period, evidence = await read_period(
                reader, current, start=anchor.day + timedelta(days=1), end=end
            )
            problems = evidence.reasons
            if evidence.status != "COMPLETE" and not problems:
                problems = ("SESSION_DAYS_MISSING",)
        count = (
            unavailable_session_count(event_at=event_at, anchor_date=anchor.day, reasons=problems)
            if problems
            else count_completed_sessions(
                entry=entry,
                binding=current.binding,
                days=period.days,
                event_at=event_at,
            )
        )
    return count, {
        "calendar": asdict(current),
        "period": asdict(period),
        "count": asdict(count),
    }


def _scale(
    basis: PositionExecutionBasis,
    evidence: ProductPriceScaleCurrent,
    quote: IndicativeQuote,
    *,
    isin: str | None,
    underlying_id: UUID,
    now: datetime,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Reuse owner BUY contributions; never recalculate remaining cost or units.

    Unknown original time cannot establish price-scale coverage at that time.
    For issuer review, explicitly check the current documented period and BUY
    contributions instead, and retain ORIGINAL_BID_TIME_UNKNOWN in the record.
    """
    economic = basis.valuation_basis
    if (
        evidence.workspace_id != basis.trade.workspace_id
        or evidence.warrant_id != basis.trade.product_id
        or evidence.known_at != now
        or (evidence.recorded_at is not None and evidence.recorded_at > now)
        or (evidence.binding is not None and evidence.binding.underlying_id != underlying_id)
    ):
        raise ValueError("REVIEW_PRODUCT_SCALE_OWNER_MISMATCH")
    contributions = {item.execution_id: item for item in basis.buy_contributions}
    currencies = {item.execution_id: item for item in economic.buy_currency_evidence}
    purchases = tuple(
        PurchaseScaleInput(
            fact.id,
            fact.supersedes_execution_id,
            contributions[fact.id].original_quantity,
            contributions[fact.id].remaining_quantity,
            fact.price_per_unit,
            fact.executed_at,
            fact.executed_on,
            fact.execution_timezone,
            fact.recorded_at,
            currencies[fact.id].currency_code,
        )
        for fact in basis.effective_executions
        if fact.side is ExecutionSide.BUY
    )
    scale = assess_product_price_scale(
        evidence=evidence,
        execution_basis_id=economic.basis_id,
        purchases=purchases,
        bid_at=quote.original_bid_at,
        bid_currency=quote.currency,
        bid_isin=isin,
        bid_available=quote.usable and quote.original_bid_at is not None,
        applicable=True,
    )
    material: dict[str, Any] = {
        "owner_assessment": asdict(scale),
        "coverage_basis": "ORIGINAL_BID_TIME",
        "comparison_covered": scale.status == "DOCUMENTED",
    }
    if quote.evaluation_mode != "INDICATIVE_ISSUER":
        return material, scale.reasons if scale.status != "DOCUMENTED" else ()
    manifest = evidence.manifest
    problems = [reason for purchase in scale.purchases for reason in purchase.reasons]
    # A fully sold purchase contributes no units and needs no current coverage.
    problems = [reason for reason in problems if reason != "BUY_NO_REMAINING_CONTRIBUTION"]
    if evidence.status != "AVAILABLE" or manifest is None:
        problems.extend(evidence.reasons or ("PRODUCT_PRICE_SCALE_EVIDENCE_MISSING",))
    elif manifest.currency != quote.currency or manifest.binding.isin != isin:
        problems.append("PRODUCT_SCALE_INDICATION_BINDING_MISMATCH")
    elif not manifest.valid_from <= now < manifest.valid_until:
        problems.append("PRODUCT_SCALE_REVIEW_OUTSIDE_DOCUMENTED_PERIOD")
    if not any(item.remaining_quantity > 0 for item in purchases):
        problems.append("PRODUCT_SCALE_CONTRIBUTING_BUYS_MISSING")
    material.update(
        coverage_basis="REVIEW_TIME_ORIGINAL_BID_TIME_UNKNOWN",
        review_at=now,
        comparison_covered=not problems,
    )
    return material, tuple(dict.fromkeys(problems))


def supply_problems(
    saved: SavedQuoteEvidence, quote: IndicativeQuote, status: StatusEvidenceRead | None
) -> tuple[str, ...]:
    if status is None or saved.retrieved_at is None:
        return ()
    problems: list[str] = []
    gap = status.latest_gap
    if (
        gap is not None
        and gap.reason != "ORIGINAL_MARKET_STATUS_NOT_DELIVERED"
        and gap.captured_at >= saved.retrieved_at
    ):
        problems.append("REVIEW_PRICE_SUPPLY_INTERRUPTED")
    # A later negative source point is disclosed as contradictory price supply,
    # never extended into an invented CLOSED interval or OPEN requirement.
    observations = list(status.latest_observations)
    if status.latest_capture is not None and status.latest_capture.original is not None:
        observations.append(status.latest_capture)
    points = [item.original for item in observations if item.original is not None]
    relevant = [
        item
        for item in points
        if quote.original_bid_at is not None and item.observed_at >= quote.original_bid_at
    ]
    if len({item.status for item in relevant}) > 1:
        problems.append("REVIEW_SOURCE_STATUS_CONFLICT")
    if any(item.status in {"CLOSED", "SUSPENDED"} for item in relevant):
        problems.append("REVIEW_LATER_NEGATIVE_STATUS_OBSERVED")
    if quote.evaluation_mode == "INDICATIVE_ISSUER" and any(
        item.original is not None
        and item.original.status in {"CLOSED", "SUSPENDED"}
        and item.captured_at >= saved.retrieved_at
        for item in observations
    ):
        problems.append("REVIEW_NEGATIVE_STATUS_RECEIVED_AFTER_INDICATION")
    return tuple(problems)


async def read_indicative_inputs(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    trade_id: UUID,
    position_id: UUID,
    now: datetime,
) -> IndicativeInputs:
    """Pure read inside one snapshot taken after the existing economic owner lock."""
    trade = await SqlAlchemyReadOnlyTradeRepository(session).get(workspace_id, trade_id)
    position = await SqlAlchemyPositionRepository(session).get_for_trade(workspace_id, trade_id)
    if trade is None or position is None or position.id != position_id:
        raise ApplicationError(
            code="REVIEW_POSITION_NOT_FOUND",
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
        "effective_execution_ids": [str(item.id) for item in basis.effective_executions],
        "warrant_name": warrant.display_name,
        "warrant_isin": warrant.isin,
        "warrant_wkn": warrant.wkn,
    }
    if closed:
        saved = SavedQuoteEvidence("POSITION_CLOSED_OR_CANCELLED")
        return IndicativeInputs(
            workspace_id,
            trade_id,
            position_id,
            economic.basis_id,
            True,
            saved,
            qualify_review_quote(saved, now=now, selection_policy=None),
            None,
            None,
            JSON_VALUE.dump_python(material, mode="json"),
            (),
        )
    saved = await RiskMarketDataReader(session).saved_quote(
        workspace_id=workspace_id,
        position_id=position_id,
        as_of=now,
        expected_warrant_id=trade.product_id,
    )
    selection = (
        await session.get(PositionQuoteSourceSelectionModel, saved.route.selection_id)
        if saved.route
        else None
    )
    quote = qualify_review_quote(
        saved, now=now, selection_policy=selection.policy_version if selection else None
    )
    first = next(
        (item for item in basis.effective_executions if item.side is ExecutionSide.BUY),
        None,
    )
    entry = (
        SessionEntry(
            first.id,
            first.executed_at if first.executed_on is None else None,
            first.executed_on,
            first.execution_timezone,
            "EXACT" if first.executed_on is None else "DATE_ONLY",
        )
        if first
        else None
    )
    reader = SessionEvidenceReader(session)
    review_count, review_sessions = await _sessions(
        reader,
        workspace_id=workspace_id,
        underlying_id=warrant.underlying_id,
        entry=entry,
        now=now,
        event_at=now,
    )
    comparison_count, comparison_sessions = review_count, review_sessions
    if quote.evaluation_mode == "SOURCE_BID":
        comparison_count, comparison_sessions = await _sessions(
            reader,
            workspace_id=workspace_id,
            underlying_id=warrant.underlying_id,
            entry=entry,
            now=now,
            event_at=quote.session_event_at,
        )
    scale, scale_problems = _scale(
        basis,
        await ProductPriceScaleEvidenceReader(session).current(
            workspace_id=workspace_id, warrant_id=trade.product_id, known_at=now
        ),
        quote,
        isin=warrant.isin,
        underlying_id=warrant.underlying_id,
        now=now,
    )
    status = None
    if saved.route is not None and saved.provider is not None and warrant.isin is not None:
        route = saved.route
        status = await MarketStatusReader(session).read(
            route=StatusRouteBinding(
                workspace_id,
                trade.product_id,
                route.warrant_listing_id,
                saved.provider,
                route.identity_key,
                warrant.isin,
                route.venue_mic,
            ),
            event_at=now,
            known_at=now,
        )
    problems = [
        *scale_problems,
        *comparison_count.reasons,
        *supply_problems(saved, quote, status),
    ]
    if economic.currency_status != "KNOWN" or economic.cost_basis_currency is None:
        problems.append("EXECUTION_CURRENCY_UNQUALIFIED")
    elif quote.currency is not None and economic.cost_basis_currency != quote.currency:
        problems.append("EXECUTION_BID_CURRENCY_MISMATCH")
    clocks = [trade.created_at, *(fact.recorded_at for fact in basis.history)]
    clocks.extend(
        fact.currency_confirmation.confirmed_at
        for fact in basis.history
        if fact.currency_confirmation is not None
    )
    clocks.extend(
        item.recorded_at for buy in economic.buy_currency_evidence for item in buy.evidence
    )
    if any(clock.utcoffset() is None or clock.astimezone(UTC) > now for clock in clocks):
        problems.append("REVIEW_OWNER_FACT_AFTER_EVALUATION")
        review_count = replace(
            review_count,
            status="NOT_ASSESSABLE",
            completed_sessions=None,
            threshold_reached=None,
            reasons=("REVIEW_OWNER_FACT_AFTER_EVALUATION",),
        )
        comparison_count = replace(
            comparison_count,
            status="NOT_ASSESSABLE",
            completed_sessions=None,
            threshold_reached=None,
            reasons=("REVIEW_OWNER_FACT_AFTER_EVALUATION",),
        )
        review_sessions = {**review_sessions, "count": asdict(review_count)}
        comparison_sessions = {**comparison_sessions, "count": asdict(comparison_count)}
    material.update(
        entry=asdict(entry) if entry else None,
        saved_quote=asdict(saved),
        quote=asdict(quote),
        selection_policy=selection.policy_version if selection else None,
        review_sessions=review_sessions,
        comparison_sessions=comparison_sessions,
        product_scale=scale,
        status_observations=asdict(status) if status else None,
    )
    return IndicativeInputs(
        workspace_id,
        trade_id,
        position_id,
        economic.basis_id,
        False,
        saved,
        quote,
        review_count,
        comparison_count,
        JSON_VALUE.dump_python(material, mode="json"),
        tuple(dict.fromkeys(problems)),
    )
