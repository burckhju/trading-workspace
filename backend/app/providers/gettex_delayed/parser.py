"""Fail-closed parser for official gettex MUND/MUNC delayed pre-trade CSV rows."""

from __future__ import annotations

import csv
import gzip
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from io import TextIOWrapper
from typing import BinaryIO

_FILE_NAME = re.compile(
    r"^pretrade\.(?P<date>\d{8})\.(?P<hour>\d{2})\.(?P<minute>\d{2})\."
    r"(?P<mic>mund|munc)\.csv\.gz$",
    re.IGNORECASE,
)
_ISIN = re.compile(r"^[A-Z0-9]{12}$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")


class GettexPayloadError(ValueError):
    """Raised when a delayed-data filename or row violates the verified contract."""


@dataclass(frozen=True, slots=True)
class GettexFileWindow:
    """Verified 15-minute UTC window encoded by one gettex filename."""

    mic: str
    starts_at: datetime
    ends_at: datetime


@dataclass(frozen=True, slots=True)
class GettexQuoteRow:
    """One exact instrument quote row from a verified gettex file window."""

    isin: str
    observed_at: datetime
    currency: str
    bid: Decimal | None
    ask: Decimal | None
    bid_volume: Decimal | None
    ask_volume: Decimal | None
    mic: str


def parse_file_window(file_name: str) -> GettexFileWindow:
    """Parse the observed 15-minute file-window convention without guessing from content."""

    match = _FILE_NAME.fullmatch(file_name.strip())
    if match is None:
        raise GettexPayloadError("GETTEX_FILE_NAME_INVALID")
    try:
        ends_at = datetime.strptime(
            f"{match.group('date')}{match.group('hour')}{match.group('minute')}",
            "%Y%m%d%H%M",
        ).replace(tzinfo=UTC)
    except ValueError as exc:
        raise GettexPayloadError("GETTEX_FILE_TIMESTAMP_INVALID") from exc
    if ends_at.minute not in {0, 15, 30, 45}:
        raise GettexPayloadError("GETTEX_FILE_WINDOW_NOT_QUARTER_HOUR")
    return GettexFileWindow(
        mic=match.group("mic").upper(),
        starts_at=ends_at - timedelta(minutes=15),
        ends_at=ends_at,
    )


def parse_quote_row(line: str, *, window: GettexFileWindow) -> GettexQuoteRow:
    """Parse one headerless seven-field quote row against its exact file window."""

    try:
        fields = next(csv.reader([line]))
    except (csv.Error, StopIteration) as exc:
        raise GettexPayloadError("GETTEX_ROW_CSV_INVALID") from exc
    if len(fields) != 7:
        raise GettexPayloadError("GETTEX_ROW_FIELD_COUNT_INVALID")

    isin, clock, currency, bid, bid_volume, ask, ask_volume = (
        value.strip() for value in fields
    )
    isin = isin.upper()
    currency = currency.upper()
    if _ISIN.fullmatch(isin) is None:
        raise GettexPayloadError("GETTEX_ROW_ISIN_INVALID")
    if _CURRENCY.fullmatch(currency) is None:
        raise GettexPayloadError("GETTEX_ROW_CURRENCY_INVALID")

    observed_at = _observed_at(clock, window)
    parsed_bid = _positive_decimal(bid, "BID")
    parsed_ask = _positive_decimal(ask, "ASK")
    parsed_bid_volume = _non_negative_decimal(bid_volume, "BID_VOLUME")
    parsed_ask_volume = _non_negative_decimal(ask_volume, "ASK_VOLUME")
    if parsed_bid is None and parsed_ask is None:
        raise GettexPayloadError("GETTEX_ROW_NO_QUOTE_SIDE")
    if parsed_bid is not None and parsed_ask is not None and parsed_ask < parsed_bid:
        raise GettexPayloadError("GETTEX_ROW_CROSSED_QUOTE")

    return GettexQuoteRow(
        isin=isin,
        observed_at=observed_at,
        currency=currency,
        bid=parsed_bid,
        ask=parsed_ask,
        bid_volume=parsed_bid_volume,
        ask_volume=parsed_ask_volume,
        mic=window.mic,
    )


def scan_gzip_quotes(
    source: BinaryIO,
    *,
    file_name: str,
    tracked_isins: set[str],
) -> dict[str, GettexQuoteRow]:
    """Stream a complete gzip file and retain only the newest requested ISIN rows."""

    window = parse_file_window(file_name)
    tracked = {value.strip().upper() for value in tracked_isins}
    if any(_ISIN.fullmatch(value) is None for value in tracked):
        raise GettexPayloadError("GETTEX_TRACKED_ISIN_INVALID")
    if not tracked:
        return {}

    latest: dict[str, GettexQuoteRow] = {}
    try:
        with gzip.GzipFile(fileobj=source, mode="rb") as compressed:
            text = TextIOWrapper(compressed, encoding="utf-8", newline="")
            for raw_line in text:
                candidate = raw_line.partition(",")[0].strip().upper()
                if candidate not in tracked:
                    continue
                row = parse_quote_row(raw_line.rstrip("\r\n"), window=window)
                previous = latest.get(row.isin)
                if previous is None or row.observed_at > previous.observed_at:
                    latest[row.isin] = row
                elif row.observed_at == previous.observed_at and row != previous:
                    raise GettexPayloadError("GETTEX_DUPLICATE_TIMESTAMP_CONFLICT")
    except (EOFError, OSError, UnicodeDecodeError) as exc:
        raise GettexPayloadError("GETTEX_GZIP_INVALID") from exc
    return latest


def _observed_at(clock: str, window: GettexFileWindow) -> datetime:
    try:
        parsed_time = datetime.strptime(clock, "%H:%M:%S.%f").time()
    except ValueError as exc:
        raise GettexPayloadError("GETTEX_ROW_TIME_INVALID") from exc

    candidates = {
        datetime.combine(window.starts_at.date(), parsed_time, tzinfo=UTC),
        datetime.combine(window.ends_at.date(), parsed_time, tzinfo=UTC),
    }
    matching = [
        value for value in candidates if window.starts_at <= value < window.ends_at
    ]
    if len(matching) != 1:
        raise GettexPayloadError("GETTEX_ROW_TIME_OUTSIDE_FILE_WINDOW")
    return matching[0]


def _positive_decimal(value: str, field: str) -> Decimal | None:
    if not value:
        return None
    parsed = _decimal(value, field)
    if parsed <= 0:
        raise GettexPayloadError(f"GETTEX_ROW_{field}_NOT_POSITIVE")
    return parsed


def _non_negative_decimal(value: str, field: str) -> Decimal | None:
    if not value:
        return None
    parsed = _decimal(value, field)
    if parsed < 0:
        raise GettexPayloadError(f"GETTEX_ROW_{field}_NEGATIVE")
    return parsed


def _decimal(value: str, field: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise GettexPayloadError(f"GETTEX_ROW_{field}_INVALID") from exc
    if not parsed.is_finite():
        raise GettexPayloadError(f"GETTEX_ROW_{field}_INVALID")
    return parsed
