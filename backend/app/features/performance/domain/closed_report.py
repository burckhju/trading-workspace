"""Qualify full trade results by their current actual closing SELL.

The trade-position owner alone calculates costs and realized P&L. This consumer
selects complete owner projections, qualifies their entire monetary provenance,
and keeps unresolved histories visible in a disjoint coverage partition.
"""

import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import asdict, replace
from datetime import UTC, datetime
from decimal import Decimal, DecimalException, getcontext
from uuid import UUID
from zoneinfo import ZoneInfoNotFoundError

from app.features.performance.domain.closed_models import (
    ClosedTradeCounts,
    ClosedTradeGroup,
    ClosedTradeItem,
    ClosedTradeReport,
    ClosedTradeSellContribution,
    TradeClassification,
)
from app.features.performance.domain.models import (
    ExecutionFact,
    ExecutionSource,
    ItemStatus,
    PeriodStatus,
    ReportBasis,
    ReportFilters,
    ReportSnapshot,
    ReportSummary,
    SummaryStatus,
    TradeFact,
)
from app.features.performance.domain.periods import (
    classify_period,
    execution_time,
    report_interval,
    time_fields,
)
from app.features.performance.domain.report import (
    MAX_PROVENANCE_LINKS,
    ReportLimitExceeded,
    _confirmations,
    _json_value,
    _ordered,
    _source,
    decimal_string,
    displayed,
)
from app.features.trade_position.domain.currency import ExecutionCurrencyResolution
from app.features.trade_position.domain.currency_resolution import (
    CurrencyResolutionLimitExceeded,
    resolve_execution_currencies,
)
from app.features.trade_position.domain.projector import (
    PositionProjectionTrace,
    PositionProjector,
)

DEFINITION_VERSION = "closed-trade-gross-v1"


def _account(links: int, additional: int) -> int:
    result = links + additional
    if result > MAX_PROVENANCE_LINKS:
        raise ReportLimitExceeded("Report exceeds the complete provenance limit")
    return result


def _valid_supersessions(trade: TradeFact, history: list[ExecutionFact]) -> bool:
    """An ambiguous replacement graph cannot prove an effective full exit."""
    facts = {fact.id: fact for fact in history}
    if len(facts) != len(history):
        return False
    replaced: set[UUID] = set()
    for fact in history:
        predecessor_id = fact.supersedes_execution_id
        if predecessor_id is None:
            continue
        predecessor = facts.get(predecessor_id)
        if (
            predecessor is None
            or predecessor_id in replaced
            or fact.trade_id != trade.trade.id
            or predecessor.trade_id != trade.trade.id
            or fact.product_id != trade.trade.product_id
            or predecessor.product_id != trade.trade.product_id
        ):
            return False
        replaced.add(predecessor_id)
    checked: set[UUID] = set()
    for fact in history:
        path: set[UUID] = set()
        cursor: UUID | None = fact.id
        while cursor is not None and cursor not in checked:
            if cursor in path:
                return False
            path.add(cursor)
            cursor = facts[cursor].supersedes_execution_id
        checked.update(path)
    return True


def _project(
    trade: TradeFact, history: list[ExecutionFact], effective: list[ExecutionFact]
) -> PositionProjectionTrace | None:
    if trade.position_id is None or not effective or not _valid_supersessions(trade, history):
        return None
    try:
        owner = PositionProjector.project_with_trace(
            id=trade.position_id,
            trade=trade.trade,
            executions=[fact.to_domain() for fact in effective],
        )
        if not owner.position.realized_gross_pnl.is_finite():
            return None
        return owner
    except (ValueError, DecimalException, ZoneInfoNotFoundError):
        return None


def _currency(
    facts: list[ExecutionFact], resolutions: dict[UUID, ExecutionCurrencyResolution]
) -> tuple[str | None, tuple[str, ...], tuple[UUID, ...]]:
    values = [resolutions[fact.id] for fact in facts]
    codes = {value.currency_code for value in values if value.currency_code is not None}
    reasons = []
    if any(value.source == "UNKNOWN" for value in values):
        reasons.append("CURRENCY_UNKNOWN")
    if len(codes) > 1 or any(value.source == "MIXED" for value in values):
        reasons.append("CURRENCY_MIXED")
    code = next(iter(codes)) if len(codes) == 1 and not reasons else None
    confirmation_ids = tuple(dict.fromkeys(id for value in values for id in value.confirmation_ids))
    return code, tuple(reasons), confirmation_ids


def _contributions(
    owner: PositionProjectionTrace,
    effective: list[ExecutionFact],
    resolutions: dict[UUID, ExecutionCurrencyResolution],
    filters: ReportFilters,
    interval: tuple[datetime, datetime],
    minor_unit: int,
    links: int,
) -> tuple[tuple[ClosedTradeSellContribution, ...], int]:
    result = []
    for trace in owner.sells:
        index = trace.execution_index
        execution = effective[index]
        # Count every repeated source edge before materializing that prefix.
        links = _account(links, index + 1)
        prefix = effective[:index]
        required = [fact for fact in prefix if fact.side == "BUY"] + [execution]
        currency_code, currency_reasons, confirmation_ids = _currency(required, resolutions)
        links = _account(links, len(confirmation_ids))
        other_currency = currency_code is not None and currency_code != filters.report_currency
        reasons = (*currency_reasons, *(("OTHER_CURRENCY",) if other_currency else ()))
        status: ItemStatus = (
            "EXCLUDED" if other_currency else "NOT_COMPUTABLE" if reasons else "USABLE"
        )
        qualified = trace if status == "USABLE" else None
        result.append(
            ClosedTradeSellContribution(
                **time_fields(execution),
                execution_id=execution.id,
                quantity=execution.quantity,
                price_per_unit=decimal_string(execution.price_per_unit),
                is_closing=trace.open_quantity_before > 0 and trace.open_quantity_after == 0,
                period_status=classify_period(execution_time(execution), *interval),
                status=status,
                reasons=reasons,
                currency_code=resolutions[execution.id].currency_code,
                average_cost_per_unit=decimal_string(
                    qualified.average_cost_per_unit if qualified else None
                ),
                cost_basis_before=decimal_string(
                    qualified.cost_basis_before if qualified else None
                ),
                cost_basis_after=decimal_string(qualified.cost_basis_after if qualified else None),
                realized_gross_pnl_delta=decimal_string(
                    qualified.realized_gross_pnl_delta if qualified else None
                ),
                realized_gross_pnl_delta_display=(
                    displayed(qualified.realized_gross_pnl_delta, minor_unit) if qualified else None
                ),
                cost_basis_before_close_reset=decimal_string(
                    qualified.cost_basis_before_close_reset if qualified else None
                ),
                open_quantity_before=trace.open_quantity_before,
                open_quantity_after=trace.open_quantity_after,
                currency_confirmation_ids=confirmation_ids,
                cost_basis_execution_ids=tuple(fact.id for fact in prefix),
            )
        )
    return tuple(result), links


def _group(
    trade: TradeFact,
    owner: PositionProjectionTrace | None,
    period: PeriodStatus | None,
    currency_code: str | None,
    currency_reasons: tuple[str, ...],
    filters: ReportFilters,
) -> tuple[ClosedTradeGroup, ItemStatus, tuple[str, ...]]:
    # First match wins. In particular, an old-looking invalid stream is still a
    # relevant gap, whereas a proved outside-period exit cannot affect this sum.
    if trade.trade.cancelled_at is not None:
        return "CANCELLED", "EXCLUDED", ("TRADE_CANCELLED",)
    if owner is None:
        return "HISTORY_UNRESOLVED", "NOT_COMPUTABLE", ("HISTORY_INVALID",)
    if owner.position.open_quantity > 0:
        return "OPEN", "EXCLUDED", ("TRADE_OPEN",)
    if period is None:
        return "HISTORY_UNRESOLVED", "NOT_COMPUTABLE", ("HISTORY_INVALID",)
    if period == "OUTSIDE_PERIOD":
        return "OUTSIDE_PERIOD", "EXCLUDED", ("OUTSIDE_PERIOD", *currency_reasons)
    if currency_code is not None and currency_code != filters.report_currency:
        return "OTHER_CURRENCY", "EXCLUDED", ("OTHER_CURRENCY",)
    if period != "IN_PERIOD":
        return "PERIOD_UNRESOLVED", "NOT_COMPUTABLE", (period, *currency_reasons)
    if currency_reasons or currency_code is None:
        return "MONETARY_UNRESOLVED", "NOT_COMPUTABLE", currency_reasons or ("CURRENCY_UNKNOWN",)
    return "QUALIFIED", "USABLE", ()


def _trade_item(
    trade: TradeFact,
    history: list[ExecutionFact],
    effective: list[ExecutionFact],
    resolutions: dict[UUID, ExecutionCurrencyResolution],
    filters: ReportFilters,
    interval: tuple[datetime, datetime],
    minor_unit: int,
    links: int,
) -> tuple[ClosedTradeItem, int]:
    owner = _project(trade, history, effective) if trade.trade.cancelled_at is None else None
    currency_code, currency_reasons, confirmation_ids = _currency(effective, resolutions)
    closing = None
    if owner is not None:
        closing = next(
            (
                effective[trace.execution_index]
                for trace in owner.sells
                if trace.open_quantity_before > 0 and trace.open_quantity_after == 0
            ),
            None,
        )
    period = classify_period(execution_time(closing), *interval) if closing else None
    group, status, reasons = _group(trade, owner, period, currency_code, currency_reasons, filters)
    links = _account(
        links, len(history) + len(effective) + len(confirmation_ids) + int(closing is not None)
    )
    contributions: tuple[ClosedTradeSellContribution, ...] = ()
    if owner is not None:
        contributions, links = _contributions(
            owner, effective, resolutions, filters, interval, minor_unit, links
        )
    amount = owner.position.realized_gross_pnl if owner and group == "QUALIFIED" else None
    classification: TradeClassification | None = (
        None
        if amount is None
        else "POSITIVE" if amount > 0 else "NEGATIVE" if amount < 0 else "NEUTRAL"
    )
    return (
        ClosedTradeItem(
            trade_id=trade.trade.id,
            product_id=trade.trade.product_id,
            product_name=trade.product_name,
            origin=trade.trade.origin.value,
            group=group,
            status=status,
            reasons=reasons,
            period_status=period,
            closing_execution_id=closing.id if closing else None,
            closing_time=execution_time(closing) if closing else None,
            currency_code=currency_code,
            realized_gross_pnl=decimal_string(amount),
            realized_gross_pnl_display=(
                displayed(amount, minor_unit) if amount is not None else None
            ),
            classification=classification,
            execution_ids=tuple(fact.id for fact in history),
            effective_execution_ids=tuple(fact.id for fact in effective),
            currency_confirmation_ids=confirmation_ids,
            sell_contributions=contributions,
        ),
        links,
    )


def _counts(items: list[ClosedTradeItem]) -> ClosedTradeCounts:
    groups = Counter(item.group for item in items)
    return ClosedTradeCounts(
        examined=len(items),
        cancelled=groups["CANCELLED"],
        history_unresolved=groups["HISTORY_UNRESOLVED"],
        open=groups["OPEN"],
        outside_period=groups["OUTSIDE_PERIOD"],
        other_currency=groups["OTHER_CURRENCY"],
        period_unresolved=groups["PERIOD_UNRESOLVED"],
        monetary_unresolved=groups["MONETARY_UNRESOLVED"],
        qualified=groups["QUALIFIED"],
        in_period=groups["MONETARY_UNRESOLVED"] + groups["QUALIFIED"],
        unresolved=(
            groups["HISTORY_UNRESOLVED"]
            + groups["PERIOD_UNRESOLVED"]
            + groups["MONETARY_UNRESOLVED"]
        ),
        positive=sum(item.classification == "POSITIVE" for item in items),
        negative=sum(item.classification == "NEGATIVE" for item in items),
        neutral=sum(item.classification == "NEUTRAL" for item in items),
    )


def _summary(items: list[ClosedTradeItem], minor_unit: int) -> ReportSummary:
    qualified = [item for item in items if item.group == "QUALIFIED"]
    unresolved = any(item.status == "NOT_COMPUTABLE" for item in items)
    status: SummaryStatus = (
        "PARTIAL"
        if qualified and unresolved
        else "NOT_COMPUTABLE" if unresolved else "COMPLETE" if qualified else "EMPTY"
    )
    amount = sum((Decimal(item.realized_gross_pnl or "0") for item in qualified), Decimal(0))
    amount_display = displayed(amount, minor_unit)
    total = decimal_string(amount) if status in {"EMPTY", "COMPLETE"} else None
    subtotal = decimal_string(amount) if status == "PARTIAL" else None
    difference = (
        Decimal(amount_display)
        - sum((Decimal(item.realized_gross_pnl_display or "0") for item in qualified), Decimal(0))
        if qualified
        else None
    )
    return ReportSummary(
        status=status,
        total=total,
        total_display=amount_display if total is not None else None,
        subtotal=subtotal,
        subtotal_display=amount_display if subtotal is not None else None,
        rounding_difference=decimal_string(difference),
        rounding_difference_display=(
            displayed(difference, minor_unit) if difference is not None else None
        ),
    )


def build_closed_report(snapshot: ReportSnapshot, filters: ReportFilters) -> ClosedTradeReport:
    interval = report_interval(filters)
    if snapshot.currency.code != filters.report_currency:
        raise ValueError("Requested currency does not match the snapshot")
    # The reader already scopes these facts. Keep this pure consumer scoped too,
    # and deduplicate identity rather than allowing display/learning multiplicity.
    scoped_trades = {
        trade.trade.id: trade
        for trade in snapshot.trades
        if trade.trade.workspace_id == snapshot.workspace_id
    }
    snapshot = replace(
        snapshot,
        trades=tuple(scoped_trades[id] for id in sorted(scoped_trades)),
        executions=tuple(
            _ordered([fact for fact in snapshot.executions if fact.trade_id in scoped_trades])
        ),
        confirmations=tuple(
            fact
            for fact in snapshot.confirmations
            if fact.workspace_id == snapshot.workspace_id and fact.trade_id in scoped_trades
        ),
    )
    current, histories = _confirmations(snapshot)
    by_trade: dict[UUID, list[ExecutionFact]] = defaultdict(list)
    for execution in snapshot.executions:
        by_trade[execution.trade_id].append(execution)
    items = []
    sources: list[ExecutionSource] = []
    links = 0
    for trade in snapshot.trades:
        history = by_trade[trade.trade.id]
        replacements = {
            fact.supersedes_execution_id: fact.id
            for fact in history
            if fact.supersedes_execution_id
        }
        try:
            resolutions = resolve_execution_currencies(
                trade=trade.trade,
                executions=history,
                current=current,
                max_provenance_links=MAX_PROVENANCE_LINKS - links,
            )
        except CurrencyResolutionLimitExceeded as error:
            raise ReportLimitExceeded("Report exceeds the complete provenance limit") from error
        links = _account(
            links,
            sum(
                len(value.source_execution_ids) + len(value.confirmation_ids)
                for value in resolutions.values()
            ),
        )
        sources.extend(
            _source(fact, replacements, current, histories, resolutions) for fact in history
        )
        effective = [fact for fact in history if fact.id not in replacements]
        item, links = _trade_item(
            trade,
            history,
            effective,
            resolutions,
            filters,
            interval,
            snapshot.currency.minor_unit,
            links,
        )
        items.append(item)
    order = {fact.id: index for index, fact in enumerate(snapshot.executions)}
    sources.sort(key=lambda source: order[source.execution_id])
    material = asdict(snapshot)
    del material["read_started_at"], material["read_completed_at"]
    canonical = {
        "definition": DEFINITION_VERSION,
        "filters": asdict(filters),
        "interval": interval,
        "snapshot": material,
        "source_time_intervals": [asdict(execution_time(fact)) for fact in snapshot.executions],
        "decimal_context": [getcontext().prec, getcontext().rounding],
    }
    fingerprint = hashlib.sha256(
        json.dumps(canonical, default=_json_value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return ClosedTradeReport(
        definition_version=DEFINITION_VERSION,
        filters=filters,
        interval_start_at=interval[0],
        interval_end_at=interval[1],
        basis=ReportBasis(
            id=fingerprint,
            read_started_at=snapshot.read_started_at,
            read_completed_at=snapshot.read_completed_at,
            calculated_at=datetime.now(UTC),
        ),
        currency=snapshot.currency,
        summary=_summary(items, snapshot.currency.minor_unit),
        counts=_counts(items),
        items=tuple(items),
        sources=tuple(sources),
    )
