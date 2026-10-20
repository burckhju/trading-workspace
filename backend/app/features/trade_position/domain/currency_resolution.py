"""Reuse evidenced purchase currencies in the owner's effective execution order.

The resolver consumes immutable facts and current, scoped confirmations. It does
not persist a trade currency, manufacture USER_CONFIRMED rows, or calculate PnL.
Superseded facts can supply an explicit same-side correction ancestor; only
effective BUYs supply a chronological purchase prefix. A later BUY never fills
an earlier gap. Historical superseded rows retain direct/ancestor provenance,
without pretending to reconstruct their former effective purchase prefix.
"""

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.features.trade_position.domain.currency import ExecutionCurrencyResolution
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
    max_provenance_links: int | None = None,
) -> dict[UUID, ExecutionCurrencyResolution]:
    """Resolve each fact without mutating inputs or borrowing cross-scope evidence.

    Priority is own declaration, explicit same-side correction ancestor, then the
    complete earlier effective BUY prefix. All actual BUYs in that prefix must
    resolve to one currency. Earlier SELL proceeds do not enter that decision.
    """
    facts = {execution.id: execution for execution in executions}
    bases: dict[UUID, ExecutionCurrencyResolution] = {}

    def in_scope(execution: CurrencyExecution) -> bool:
        return execution.trade_id == trade.id and execution.product_id == trade.product_id

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

    # Memoized iterative ancestry avoids recursion depth and repeated chain walks.
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
        for item in reversed(path):
            bases[item.id] = (
                ExecutionCurrencyResolution(
                    currency_code=inherited.currency_code,
                    source="REPLACED_EXECUTION",
                    source_execution_ids=inherited.source_execution_ids,
                    confirmation_ids=inherited.confirmation_ids,
                )
                if inherited.currency_code is not None
                else ExecutionCurrencyResolution()
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
    links = 0
    for execution in sorted(executions, key=lambda e: (e.executed_at, e.recorded_at, e.id)):
        resolution = bases[execution.id]
        effective = execution.id not in superseded
        if resolution.currency_code is None and effective and in_scope(execution):
            mixed = has_mixed_buy or len(prior_codes) > 1
            usable = bool(prior_buy_ids) and not has_unknown_buy and not mixed
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
        links += len(resolution.source_execution_ids) + len(resolution.confirmation_ids)
        if max_provenance_links is not None and links > max_provenance_links:
            raise CurrencyResolutionLimitExceeded("Currency provenance exceeds read bound")
        result[execution.id] = resolution
        if effective and in_scope(execution) and execution.side == "BUY":
            prior_buy_ids[execution.id] = None
            prior_buy_ids.update(dict.fromkeys(resolution.source_execution_ids))
            prior_confirmation_ids.update(dict.fromkeys(resolution.confirmation_ids))
            if resolution.currency_code is not None:
                prior_codes.add(resolution.currency_code)
            else:
                has_unknown_buy |= resolution.source == "UNKNOWN"
                has_mixed_buy |= resolution.source == "MIXED"
    return result
