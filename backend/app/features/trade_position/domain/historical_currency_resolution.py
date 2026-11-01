"""Resolve reviewed sources without treating present-day listings as history.

A listing source describes an explicit bounded interval and, when claimed, the
complete relevant venue set. A date-only execution needs coverage of its whole
possible day. Partial or conflicting sources cannot disappear through filtering.
"""

from collections.abc import Sequence
from datetime import UTC, date, datetime, time, timedelta
from typing import Protocol
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.features.trade_position.domain.currency import (
    CurrencyEvidenceReference,
    CurrencyResolutionSource,
    CurrencyTradeScope,
    ExecutionCurrencyResolution,
)
from app.features.trade_position.domain.currency_evidence import CurrencyEvidence


class HistoricalCurrencyExecution(Protocol):
    @property
    def id(self) -> UUID: ...

    @property
    def trade_id(self) -> UUID: ...

    @property
    def product_id(self) -> UUID: ...

    @property
    def executed_at(self) -> datetime: ...

    @property
    def executed_on(self) -> date | None: ...

    @property
    def execution_timezone(self) -> str | None: ...


def _result(
    records: Sequence[CurrencyEvidence],
    *,
    currency: str | None = None,
    source: CurrencyResolutionSource = "UNKNOWN",
    reason: str | None = None,
) -> ExecutionCurrencyResolution:
    ordered = sorted({item.id: item for item in records}.values(), key=lambda item: item.id)
    return ExecutionCurrencyResolution(
        currency_code=currency,
        source=source,
        evidence_ids=tuple(item.id for item in ordered),
        evidence=tuple(
            CurrencyEvidenceReference(
                id=item.id,
                kind=item.kind,
                source_reference=item.source_reference,
                recorded_at=item.recorded_at,
                valid_from=item.valid_from,
                valid_to=item.valid_to,
                source_fingerprint=item.request_fingerprint,
                verification=item.verification,
            )
            for item in ordered
        ),
        reason=reason,
    )


def _scope(item: CurrencyEvidence) -> tuple[object, ...]:
    return item.workspace_id, item.product_id, item.kind, item.trade_id, item.execution_id


def _current(
    records: Sequence[CurrencyEvidence],
) -> tuple[list[CurrencyEvidence], bool]:
    facts = {item.id: item for item in records}
    if len(facts) != len(records):
        return [], False
    superseded: set[UUID] = set()
    for item in records:
        predecessor = item.supersedes_evidence_id
        if predecessor is None:
            continue
        old = facts.get(predecessor)
        if (
            old is None
            or _scope(old) != _scope(item)
            or old.recorded_at > item.recorded_at
            or predecessor in superseded
        ):
            return [], False
        superseded.add(predecessor)
    # Iterative walk catches cycles without assuming source recording times are unique.
    checked: set[UUID] = set()
    for item in records:
        path: set[UUID] = set()
        cursor: UUID | None = item.id
        while cursor is not None and cursor not in checked:
            if cursor in path:
                return [], False
            path.add(cursor)
            cursor = facts[cursor].supersedes_evidence_id
        checked.update(path)
    return [item for item in records if item.id not in superseded and not item.revoked], True


def _midnight(day: date, zone: ZoneInfo) -> datetime:
    naive = datetime.combine(day, time.min)
    candidates = {
        aware.astimezone(UTC)
        for fold in (0, 1)
        if (aware := naive.replace(tzinfo=zone, fold=fold))
        .astimezone(UTC)
        .astimezone(zone)
        .replace(tzinfo=None)
        == naive
    }
    if len(candidates) != 1:
        raise ValueError("Unknown local day boundary")
    return candidates.pop()


def _window(execution: HistoricalCurrencyExecution) -> tuple[datetime, datetime] | None:
    day, zone_name = execution.executed_on, execution.execution_timezone
    if day is None and zone_name is None:
        instant = execution.executed_at
        return (instant, instant) if instant.utcoffset() is not None else None
    if day is None or zone_name is None:
        return None
    try:
        zone = ZoneInfo(zone_name)
        start, end = _midnight(day, zone), _midnight(day + timedelta(days=1), zone)
        if execution.executed_at != start or end <= start:
            return None
        return start, end
    except (ValueError, OverflowError, ZoneInfoNotFoundError):
        return None


def _covers(records: Sequence[CurrencyEvidence], start: datetime, end: datetime) -> bool:
    """Union explicitly evidenced intervals; never bridge an unevidenced gap."""
    cursor = start
    intervals = sorted(
        (item.valid_from, item.valid_to)
        for item in records
        if item.valid_from is not None and item.valid_to is not None
    )
    for beginning, ending in intervals:
        if beginning > cursor:
            return False
        if ending > cursor:
            cursor = ending
            if cursor > end or (start != end and cursor == end):
                return True
    return False


def resolve_historical_currency(
    *,
    trade: CurrencyTradeScope,
    execution: HistoricalCurrencyExecution,
    evidence: Sequence[CurrencyEvidence],
) -> ExecutionCurrencyResolution:
    """Exact document, known venue, then complete historical venue unanimity.

    The caller handles explicit execution confirmations first. No source from a
    correction's predecessor is attached to the replacement execution here.
    """
    if execution.trade_id != trade.id or execution.product_id != trade.product_id:
        return ExecutionCurrencyResolution()
    scoped = [
        item
        for item in evidence
        if item.workspace_id == trade.workspace_id
        and item.product_id == trade.product_id
        and (
            item.kind == "HISTORICAL_LISTINGS"
            or (item.trade_id == trade.id and item.execution_id == execution.id)
        )
    ]
    current, valid = _current(scoped)
    if not valid:
        return _result(scoped, source="CONFLICT", reason="EVIDENCE_HISTORY_INVALID")
    documents = [item for item in current if item.kind == "EXECUTION_DOCUMENT"]
    currencies = {item.currency_code for item in documents if item.currency_code is not None}
    venues = {item.trading_venue_id for item in documents if item.trading_venue_id is not None}
    if len(currencies) > 1 or len(venues) > 1:
        return _result(documents, source="CONFLICT", reason="DOCUMENT_CONFLICT")
    if currencies:
        return _result(documents, currency=next(iter(currencies)), source="EXECUTION_DOCUMENT")
    historical = [item for item in current if item.kind == "HISTORICAL_LISTINGS"]
    if not historical:
        return _result(documents, reason="NO_HISTORICAL_EVIDENCE")
    window = _window(execution)
    if window is None:
        return _result(documents + historical, reason="EXECUTION_TIME_UNKNOWN")
    start, end = window
    overlapping = [
        item
        for item in historical
        if item.valid_from is not None
        and item.valid_to is not None
        and item.valid_to > start
        and (item.valid_from <= start if start == end else item.valid_from < end)
    ]
    if not overlapping:
        return _result(documents, reason="NO_HISTORICAL_EVIDENCE")
    venue = next(iter(venues)) if venues else None
    relevant = [
        item
        for item in overlapping
        if venue is None
        or item.complete_listing_set
        or any(entry.trading_venue_id == venue for entry in item.listings)
    ]
    used = documents + relevant
    entries = [
        entry
        for item in relevant
        for entry in item.listings
        if venue is None or entry.trading_venue_id == venue
    ]
    by_venue: dict[UUID, set[str]] = {}
    for entry in entries:
        if entry.currency_code is not None:
            by_venue.setdefault(entry.trading_venue_id, set()).add(entry.currency_code)
    if any(len(codes) > 1 for codes in by_venue.values()):
        return _result(used, source="CONFLICT", reason="LISTING_CONFLICT")
    codes = {entry.currency_code for entry in entries if entry.currency_code is not None}
    if len(codes) > 1:
        return _result(used, source="MIXED", reason="MULTIPLE_LISTING_CURRENCIES")
    coverage = [
        item
        for item in relevant
        if (
            item.complete_listing_set
            if venue is None
            else any(entry.trading_venue_id == venue for entry in item.listings)
        )
    ]
    missing_venue = venue is not None and any(
        item.complete_listing_set
        and all(entry.trading_venue_id != venue for entry in item.listings)
        for item in relevant
    )
    if (
        not _covers(coverage, start, end)
        or not codes
        or any(entry.currency_code is None for entry in entries)
        or missing_venue
    ):
        return _result(used, reason="LISTING_HISTORY_INCOMPLETE")
    return _result(
        used,
        currency=next(iter(codes)),
        source="HISTORICAL_LISTING" if venue is not None else "HISTORICAL_LISTINGS",
    )
