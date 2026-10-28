"""Reuse evidenced purchase currencies in the owner's effective execution order.

The resolver consumes immutable facts and current, scoped confirmations. It does
not persist a trade currency, manufacture USER_CONFIRMED rows, or calculate PnL.
Superseded facts can supply an explicit same-side correction ancestor; only
effective BUYs supply a chronological purchase prefix. A later BUY never fills
an earlier gap. Historical superseded rows retain direct/ancestor provenance,
without pretending to reconstruct their former effective purchase prefix.
"""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from app.features.trade_position.domain.currency import ExecutionCurrencyResolution
from app.features.trade_position.domain.currency_evidence import (
    CurrencyEvidence as ReviewedCurrencyEvidence,
)
from app.features.trade_position.domain.historical_currency_resolution import (
    resolve_historical_currency,
)
from app.features.trade_position.domain.models import Trade


class CurrencyExecution(Protocol):
    @property
    def id(self) -> UUID: ...

    @property
    def trade_id(self) -> UUID: ...

    @property
    def product_id(self) -> UUID: ...

    @property
    def side(self) -> str: ...

    @property
    def executed_at(self) -> datetime: ...

    @property
    def recorded_at(self) -> datetime: ...

    @property
    def executed_on(self) -> date | None: ...

    @property
    def execution_timezone(self) -> str | None: ...

    @property
    def supersedes_execution_id(self) -> UUID | None: ...


class CurrencyEvidence(Protocol):
    @property
    def id(self) -> UUID: ...

    @property
    def workspace_id(self) -> UUID: ...

    @property
    def trade_id(self) -> UUID: ...

    @property
    def execution_id(self) -> UUID: ...

    @property
    def currency_code(self) -> str: ...

    @property
    def source(self) -> str: ...


class CurrencyResolutionLimitExceeded(ValueError):
    """The requested complete provenance exceeds the caller's read bound."""


def resolve_execution_currencies(
    *,
    trade: Trade,
    executions: Sequence[CurrencyExecution],
    current: Mapping[UUID, CurrencyEvidence],
    evidence: Sequence[ReviewedCurrencyEvidence] = (),
    max_provenance_links: int | None = None,
) -> dict[UUID, ExecutionCurrencyResolution]:
    """Resolve each fact without mutating inputs or borrowing cross-scope evidence.

    Priority is own declaration, exact execution document, evidenced venue, then
    complete historical listings. Existing same-side confirmation ancestry and
    confirmed-BUY reuse apply only without a competing source. A historical
    derivation never seeds reuse outside its evidenced interval.
    """
    facts = {execution.id: execution for execution in executions}
    bases: dict[UUID, ExecutionCurrencyResolution] = {}
    historical = []
    documents: dict[UUID, list[ReviewedCurrencyEvidence]] = {}
    for source_fact in evidence:
        if (
            source_fact.workspace_id != trade.workspace_id
            or source_fact.product_id != trade.product_id
        ):
            continue
        if source_fact.kind == "HISTORICAL_LISTINGS":
            historical.append(source_fact)
        elif source_fact.trade_id == trade.id and source_fact.execution_id is not None:
            documents.setdefault(source_fact.execution_id, []).append(source_fact)

    def in_scope(execution: CurrencyExecution) -> bool:
        return execution.trade_id == trade.id and execution.product_id == trade.product_id

    source_checks = 0
    for execution in executions:
        confirmation = current.get(execution.id)
        if (
            in_scope(execution)
            and confirmation is not None
            and confirmation.execution_id == execution.id
            and confirmation.trade_id == trade.id
            and confirmation.workspace_id == trade.workspace_id
            and confirmation.source == "USER_CONFIRMED"
        ):
            bases[execution.id] = ExecutionCurrencyResolution(
                currency_code=confirmation.currency_code,
                source="USER_CONFIRMED",
                source_execution_ids=(execution.id,),
                confirmation_ids=(confirmation.id,),
            )
            continue
        if in_scope(execution):
            sources = [*historical, *documents.get(execution.id, ())]
            source_checks += len(sources)
            if max_provenance_links is not None and source_checks > max_provenance_links:
                raise CurrencyResolutionLimitExceeded("Currency source checks exceed read bound")
            automatic = resolve_historical_currency(
                trade=trade, execution=execution, evidence=sources
            )
            if (
                automatic.currency_code is not None
                or automatic.source in {"CONFLICT", "MIXED"}
                or automatic.evidence_ids
                or automatic.reason not in {None, "NO_HISTORICAL_EVIDENCE"}
            ):
                bases[execution.id] = automatic

    # Memoized iterative ancestry avoids recursion depth and repeated chain walks.
    # Every own source is known first: a later replacement cannot skip a reviewed
    # source on its predecessor to resurrect an older, superseded declaration.
    for execution in executions:
        path: list[CurrencyExecution] = []
        visited: set[UUID] = set()
        cursor = execution
        while cursor.id not in bases and cursor.id not in visited:
            path.append(cursor)
            visited.add(cursor.id)
            predecessor = (
                facts.get(cursor.supersedes_execution_id)
                if cursor.supersedes_execution_id is not None
                else None
            )
            if (
                predecessor is None
                or not in_scope(cursor)
                or not in_scope(predecessor)
                or predecessor.side != cursor.side
            ):
                break
            cursor = predecessor
        inherited = bases.get(cursor.id, ExecutionCurrencyResolution())
        reusable = inherited.currency_code is not None and inherited.source in {
            "USER_CONFIRMED",
            "REPLACED_EXECUTION",
        }
        blocked = (
            replace(
                inherited,
                currency_code=None,
                source="UNKNOWN",
                source_execution_ids=tuple(
                    dict.fromkeys((cursor.id, *inherited.source_execution_ids))
                ),
                reason="CORRECTION_SOURCE_REVIEW_REQUIRED",
            )
            if not reusable and (inherited.evidence_ids or inherited.reason is not None)
            else ExecutionCurrencyResolution()
        )
        for item in reversed(path):
            bases[item.id] = (
                ExecutionCurrencyResolution(
                    currency_code=inherited.currency_code,
                    source="REPLACED_EXECUTION",
                    source_execution_ids=inherited.source_execution_ids,
                    confirmation_ids=inherited.confirmation_ids,
                )
                if reusable
                else blocked
            )

    superseded = {
        execution.supersedes_execution_id for execution in executions if in_scope(execution)
    }
    result: dict[UUID, ExecutionCurrencyResolution] = {}
    prior_buy_ids: dict[UUID, None] = {}
    prior_confirmation_ids: dict[UUID, None] = {}
    prior_codes: set[str] = set()
    has_unknown_buy = False
    has_mixed_buy = False
    reusable_buy_prefix = True
    links = 0
    for execution in sorted(executions, key=lambda e: (e.executed_at, e.recorded_at, e.id)):
        resolution = bases[execution.id]
        effective = execution.id not in superseded
        if (
            resolution.currency_code is None
            and resolution.source == "UNKNOWN"
            and not resolution.evidence_ids
            and resolution.reason in {None, "NO_HISTORICAL_EVIDENCE"}
            and effective
            and in_scope(execution)
        ):
            mixed = has_mixed_buy or len(prior_codes) > 1
            usable = (
                bool(prior_buy_ids) and not has_unknown_buy and not mixed and reusable_buy_prefix
            )
            # Check before copying a potentially large repeated provenance prefix.
            size = len(prior_buy_ids) + len(prior_confirmation_ids)
            if max_provenance_links is not None and links + size > max_provenance_links:
                raise CurrencyResolutionLimitExceeded("Currency provenance exceeds read bound")
            resolution = ExecutionCurrencyResolution(
                currency_code=next(iter(prior_codes)) if usable else None,
                source="PRIOR_BUYS" if usable else "MIXED" if mixed else "UNKNOWN",
                source_execution_ids=tuple(prior_buy_ids),
                confirmation_ids=tuple(prior_confirmation_ids),
            )
        links += resolution.provenance_links
        if max_provenance_links is not None and links > max_provenance_links:
            raise CurrencyResolutionLimitExceeded("Currency provenance exceeds read bound")
        result[execution.id] = resolution
        if effective and in_scope(execution) and execution.side == "BUY":
            prior_buy_ids[execution.id] = None
            prior_buy_ids.update(dict.fromkeys(resolution.source_execution_ids))
            prior_confirmation_ids.update(dict.fromkeys(resolution.confirmation_ids))
            reusable_buy_prefix &= resolution.source in {
                "USER_CONFIRMED",
                "REPLACED_EXECUTION",
                "PRIOR_BUYS",
            }
            if resolution.currency_code is not None:
                prior_codes.add(resolution.currency_code)
            else:
                has_unknown_buy |= resolution.source in {"UNKNOWN", "CONFLICT"}
                has_mixed_buy |= resolution.source == "MIXED"
    return result
