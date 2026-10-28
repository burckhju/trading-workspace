"""Qualify owner SELL traces and aggregate a complete, immutable read snapshot."""

import hashlib
import json
from collections import defaultdict
from dataclasses import asdict
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_EVEN, Decimal, DecimalException, getcontext, localcontext
from uuid import UUID
from zoneinfo import ZoneInfoNotFoundError

from app.features.performance.domain.models import (
    Confirmation,
    ExcludedTrade,
    ExecutionFact,
    ExecutionSource,
    ItemStatus,
    RealizedGrossReport,
    ReportBasis,
    ReportCounts,
    ReportFilters,
    ReportSnapshot,
    ReportSummary,
    SellItem,
    SummaryStatus,
    TradeFact,
)
from app.features.performance.domain.periods import (
    classify_period,
    execution_time,
    report_interval,
    time_fields,
)
from app.features.trade_position.domain.currency import (
    RESOLVER_VERSION,
    ExecutionCurrencyResolution,
)
from app.features.trade_position.domain.currency_resolution import (
    CurrencyResolutionLimitExceeded,
    resolve_execution_currencies,
)
from app.features.trade_position.domain.projector import PositionProjector, SellProjectionTrace

DEFINITION_VERSION = "realized-gross-sell-v2"
MAX_PROVENANCE_LINKS = 100_000


class ReportLimitExceeded(ValueError):
    """A complete result cannot fit the bounded report; never return truncation."""


def decimal_string(value: Decimal | None) -> str | None:
    return format(value, "f") if value is not None and value.is_finite() else None


def displayed(value: Decimal, minor_unit: int) -> str:
    # A separate display context must not round or mutate owner calculations.
    with localcontext() as context:
        context.prec = max(
            28, len(value.as_tuple().digits) + abs(value.adjusted()) + minor_unit + 4
        )
        rounded = value.quantize(Decimal(1).scaleb(-minor_unit), rounding=ROUND_HALF_EVEN)
    if rounded.is_zero():
        rounded = abs(rounded)
    return format(rounded, f".{minor_unit}f")


def _ordered(executions: list[ExecutionFact]) -> list[ExecutionFact]:
    return sorted(executions, key=lambda e: (e.executed_at, e.recorded_at, e.id))


def _confirmations(
    snapshot: ReportSnapshot,
) -> tuple[dict[UUID, Confirmation], dict[UUID, tuple[Confirmation, ...]]]:
    facts = {execution.id: execution for execution in snapshot.executions}
    histories: dict[UUID, list[Confirmation]] = defaultdict(list)
    for confirmation in snapshot.confirmations:
        execution = facts.get(confirmation.execution_id)
        if (
            execution is not None
            and confirmation.workspace_id == snapshot.workspace_id
            and confirmation.trade_id == execution.trade_id
        ):
            histories[execution.id].append(confirmation)
    current = {}
    immutable_histories = {}
    for execution_id, history in histories.items():
        history.sort(key=lambda c: (c.confirmed_at, c.id))
        immutable_histories[execution_id] = tuple(history)
        superseded = {c.supersedes_confirmation_id for c in history}
        active = [c for c in history if c.id not in superseded]
        if len(active) == 1 and active[0].source == "USER_CONFIRMED":
            current[execution_id] = active[0]
    return current, immutable_histories


def _source(
    execution: ExecutionFact,
    replacements: dict[UUID, UUID],
    current: dict[UUID, Confirmation],
    histories: dict[UUID, tuple[Confirmation, ...]],
    resolutions: dict[UUID, ExecutionCurrencyResolution],
) -> ExecutionSource:
    return ExecutionSource(
        **time_fields(execution),
        execution_id=execution.id,
        trade_id=execution.trade_id,
        product_id=execution.product_id,
        side=execution.side,
        quantity=execution.quantity,
        price_per_unit=decimal_string(execution.price_per_unit),
        recorded_by=execution.recorded_by,
        supersedes_execution_id=execution.supersedes_execution_id,
        superseded_by_execution_id=replacements.get(execution.id),
        is_effective=execution.id not in replacements,
        currency_confirmation=current.get(execution.id),
        currency_history=histories.get(execution.id, ()),
        currency_resolution=resolutions[execution.id],
    )


def _item(
    execution: ExecutionFact,
    prefix: list[ExecutionFact],
    trade: TradeFact,
    trace: SellProjectionTrace | None,
    resolutions: dict[UUID, ExecutionCurrencyResolution],
    filters: ReportFilters,
    interval: tuple[datetime, datetime],
    minor_unit: int,
) -> SellItem:
    period = classify_period(execution_time(execution), *interval)
    sale_currency = resolutions[execution.id].currency_code
    required = [fact for fact in prefix if fact.side == "BUY"] + [execution]
    available = [resolutions[fact.id] for fact in required]
    currencies = {value.currency_code for value in available if value.currency_code is not None}
    reasons: list[str] = []
    if period != "IN_PERIOD":
        reasons.append(period)
    if sale_currency is not None and sale_currency != filters.report_currency:
        reasons.append("OTHER_CURRENCY")
    if any(
        value.currency_code is None and value.source not in {"MIXED", "CONFLICT"}
        for value in available
    ):
        reasons.append("CURRENCY_UNKNOWN")
    if any(value.source == "CONFLICT" for value in available):
        reasons.append("CURRENCY_CONFLICT")
    if len(currencies) > 1 or any(value.source == "MIXED" for value in available):
        reasons.append("CURRENCY_MIXED")
    if trace is None:
        reasons.append("HISTORY_INVALID")
    status: ItemStatus
    if period == "OUTSIDE_PERIOD" or "OTHER_CURRENCY" in reasons:
        status = "EXCLUDED"
    elif reasons:
        status = "NOT_COMPUTABLE"
    else:
        status = "USABLE"
    qualified = trace if status == "USABLE" else None
    return SellItem(
        **time_fields(execution),
        execution_id=execution.id,
        trade_id=execution.trade_id,
        product_id=execution.product_id,
        product_name=trade.product_name,
        origin=trade.trade.origin.value,
        quantity=execution.quantity,
        price_per_unit=decimal_string(execution.price_per_unit),
        period_status=period,
        status=status,
        reasons=tuple(reasons),
        currency_code=sale_currency,
        average_cost_per_unit=decimal_string(
            qualified.average_cost_per_unit if qualified else None
        ),
        cost_basis_before=decimal_string(qualified.cost_basis_before if qualified else None),
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
        open_quantity_before=trace.open_quantity_before if trace else None,
        open_quantity_after=trace.open_quantity_after if trace else None,
        currency_confirmation_ids=tuple(
            dict.fromkeys(id for value in available for id in value.confirmation_ids)
        ),
        cost_basis_execution_ids=tuple(fact.id for fact in prefix),
    )


def _summary(items: list[SellItem], minor_unit: int) -> ReportSummary:
    usable = [item for item in items if item.status == "USABLE"]
    unresolved = any(item.status == "NOT_COMPUTABLE" for item in items)
    status: SummaryStatus = (
        "PARTIAL"
        if usable and unresolved
        else "NOT_COMPUTABLE" if unresolved else "COMPLETE" if usable else "EMPTY"
    )
    amount = sum((Decimal(item.realized_gross_pnl_delta or "0") for item in usable), Decimal(0))
    amount_display = displayed(amount, minor_unit)
    total = decimal_string(amount) if status in {"EMPTY", "COMPLETE"} else None
    subtotal = decimal_string(amount) if status == "PARTIAL" else None
    difference = (
        Decimal(amount_display)
        - sum(
            (Decimal(item.realized_gross_pnl_delta_display or "0") for item in usable), Decimal(0)
        )
        if usable
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


def _json_value(value: object) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, (UUID, Decimal)):
        return str(value)
    raise TypeError(f"Unsupported report fingerprint value: {type(value).__name__}")


def build_report(snapshot: ReportSnapshot, filters: ReportFilters) -> RealizedGrossReport:
    interval = report_interval(filters)
    if snapshot.currency.code != filters.report_currency:
        raise ValueError("Requested currency does not match the snapshot")
    current, histories = _confirmations(snapshot)
    by_trade: dict[UUID, list[ExecutionFact]] = defaultdict(list)
    for execution in snapshot.executions:
        by_trade[execution.trade_id].append(execution)
    items: list[SellItem] = []
    sources: list[ExecutionSource] = []
    excluded_trades = []
    links = 0
    for trade in snapshot.trades:
        history = _ordered(by_trade.get(trade.trade.id, []))
        replacements = {
            e.supersedes_execution_id: e.id for e in history if e.supersedes_execution_id
        }
        try:
            resolutions = resolve_execution_currencies(
                trade=trade.trade,
                executions=history,
                current=current,
                evidence=snapshot.currency_evidence,
                max_provenance_links=MAX_PROVENANCE_LINKS - links,
            )
        except CurrencyResolutionLimitExceeded as error:
            raise ReportLimitExceeded("Report exceeds the complete provenance limit") from error
        links += sum(value.provenance_links for value in resolutions.values())
        sources.extend(_source(e, replacements, current, histories, resolutions) for e in history)
        if trade.trade.cancelled_at is not None:
            excluded_trades.append(
                ExcludedTrade(
                    trade_id=trade.trade.id,
                    product_id=trade.trade.product_id,
                    product_name=trade.product_name,
                    origin=trade.trade.origin.value,
                    reason="TRADE_CANCELLED",
                    execution_ids=tuple(e.id for e in history),
                )
            )
            continue
        effective = [e for e in history if e.id not in replacements]
        sell_traces = {}
        if effective and trade.position_id is not None:
            try:
                owner = PositionProjector.project_with_trace(
                    id=trade.position_id,
                    trade=trade.trade,
                    executions=[e.to_domain() for e in effective],
                )
                sell_traces = {
                    owner.ordered_executions[s.execution_index].id: s for s in owner.sells
                }
            except (ValueError, DecimalException, ZoneInfoNotFoundError):
                # Invalid source history is a data gap, not a fabricated zero.
                pass
        for index, execution in enumerate(effective):
            if execution.side != "SELL":
                continue
            links += index
            if links > MAX_PROVENANCE_LINKS:
                raise ReportLimitExceeded("Report exceeds the complete provenance limit")
            items.append(
                _item(
                    execution,
                    effective[:index],
                    trade,
                    sell_traces.get(execution.id),
                    resolutions,
                    filters,
                    interval,
                    snapshot.currency.minor_unit,
                )
            )
    ordering = {e.id: (e.executed_at, e.recorded_at, e.id) for e in snapshot.executions}
    items.sort(key=lambda item: ordering[item.execution_id])
    sources.sort(key=lambda source: ordering[source.execution_id])
    counts = ReportCounts(
        examined=len(items),
        in_period=sum(item.period_status == "IN_PERIOD" for item in items),
        outside_period=sum(item.period_status == "OUTSIDE_PERIOD" for item in items),
        period_ambiguous=sum(item.period_status == "PERIOD_AMBIGUOUS" for item in items),
        period_unknown=sum(item.period_status == "PERIOD_UNKNOWN" for item in items),
        candidates=sum(item.status != "EXCLUDED" for item in items),
        usable=sum(item.status == "USABLE" for item in items),
        unresolved=sum(item.status == "NOT_COMPUTABLE" for item in items),
        excluded=sum(item.status == "EXCLUDED" for item in items),
        cancelled=len(excluded_trades),
    )
    material = asdict(snapshot)
    del material["read_started_at"], material["read_completed_at"]
    # Empty new provenance preserves existing historical source fingerprints.
    # Evidence-backed reports explicitly bind the source resolver definition.
    if not snapshot.currency_evidence:
        del material["currency_evidence"]
    else:
        material["currency_evidence"] = [
            asdict(item) for item in sorted(snapshot.currency_evidence, key=lambda item: item.id)
        ]
    canonical = {
        "definition": DEFINITION_VERSION,
        "filters": asdict(filters),
        "interval": interval,
        "snapshot": material,
        "source_time_intervals": [asdict(execution_time(e)) for e in snapshot.executions],
        "decimal_context": [getcontext().prec, getcontext().rounding],
        **({"currency_resolver": RESOLVER_VERSION} if snapshot.currency_evidence else {}),
    }
    fingerprint = hashlib.sha256(
        json.dumps(
            canonical,
            default=_json_value,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    return RealizedGrossReport(
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
        counts=counts,
        items=tuple(items),
        sources=tuple(sources),
        excluded_trades=tuple(excluded_trades),
    )
