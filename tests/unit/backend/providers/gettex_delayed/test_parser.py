import gzip
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO

import pytest

from app.providers.gettex_delayed.parser import (
    GettexPayloadError,
    parse_file_window,
    parse_quote_row,
    scan_gzip_quotes,
)


def test_parse_file_window_uses_quarter_hour_utc_window() -> None:
    window = parse_file_window("pretrade.20260916.21.00.mund.csv.gz")

    assert window.mic == "MUND"
    assert window.starts_at == datetime(2026, 9, 16, 20, 45, tzinfo=UTC)
    assert window.ends_at == datetime(2026, 9, 16, 21, 0, tzinfo=UTC)


def test_parse_mund_row_matches_observed_schema() -> None:
    window = parse_file_window("pretrade.20260916.21.00.mund.csv.gz")

    row = parse_quote_row(
        "IE000HFBJ0U0,20:45:00.014904,EUR,19.128,600,19.682,600",
        window=window,
    )

    assert row.isin == "IE000HFBJ0U0"
    assert row.observed_at == datetime(2026, 9, 16, 20, 45, 0, 14904, tzinfo=UTC)
    assert row.currency == "EUR"
    assert row.bid == Decimal("19.128")
    assert row.ask == Decimal("19.682")
    assert row.bid_volume == Decimal("600")
    assert row.ask_volume == Decimal("600")
    assert row.mic == "MUND"


def test_parse_munc_row_matches_observed_schema() -> None:
    window = parse_file_window("pretrade.20260916.21.00.munc.csv.gz")

    row = parse_quote_row(
        "DE000BYL0FH8,20:45:18.518816,USD,97.318,2000000,97.753,2000000",
        window=window,
    )

    assert row.mic == "MUNC"
    assert row.observed_at == datetime(2026, 9, 16, 20, 45, 18, 518816, tzinfo=UTC)
    assert row.bid == Decimal("97.318")
    assert row.ask == Decimal("97.753")


def test_midnight_file_assigns_previous_day_to_2345_rows() -> None:
    window = parse_file_window("pretrade.20260917.00.00.mund.csv.gz")

    row = parse_quote_row(
        "DE000UN37224,23:59:59.999867,EUR,1.23,100,1.24,100",
        window=window,
    )

    assert row.observed_at == datetime(2026, 9, 16, 23, 59, 59, 999867, tzinfo=UTC)


def test_row_outside_filename_window_is_rejected() -> None:
    window = parse_file_window("pretrade.20260916.21.00.mund.csv.gz")

    with pytest.raises(
        GettexPayloadError,
        match="GETTEX_ROW_TIME_OUTSIDE_FILE_WINDOW",
    ):
        parse_quote_row(
            "DE000UN37224,20:44:59.999999,EUR,1.23,100,1.24,100",
            window=window,
        )


def test_crossed_quote_is_rejected() -> None:
    window = parse_file_window("pretrade.20260916.21.00.mund.csv.gz")

    with pytest.raises(GettexPayloadError, match="GETTEX_ROW_CROSSED_QUOTE"):
        parse_quote_row(
            "DE000UN37224,20:50:00.000001,EUR,1.25,100,1.24,100",
            window=window,
        )


def test_wrong_field_count_is_rejected() -> None:
    window = parse_file_window("pretrade.20260916.21.00.mund.csv.gz")

    with pytest.raises(GettexPayloadError, match="GETTEX_ROW_FIELD_COUNT_INVALID"):
        parse_quote_row("DE000UN37224,20:50:00.000001,EUR,1.25", window=window)


def test_non_quarter_hour_filename_is_rejected() -> None:
    with pytest.raises(
        GettexPayloadError,
        match="GETTEX_FILE_WINDOW_NOT_QUARTER_HOUR",
    ):
        parse_file_window("pretrade.20260916.21.07.mund.csv.gz")


def test_streaming_scan_keeps_only_latest_tracked_rows() -> None:
    content = "\n".join(
        [
            "US17327CAU71,20:45:00.002850,USD,94.544,2000000,95.407,2000000",
            "DE000UN37224,20:46:00.000001,EUR,1.20,100,1.21,100",
            "DE000UN37224,20:58:00.000001,EUR,1.23,120,1.24,110",
            "IE000HFBJ0U0,20:59:00.000001,EUR,19.128,600,19.682,600",
        ]
    ).encode()
    source = BytesIO(gzip.compress(content))

    quotes = scan_gzip_quotes(
        source,
        file_name="pretrade.20260916.21.00.mund.csv.gz",
        tracked_isins={"DE000UN37224"},
    )

    assert set(quotes) == {"DE000UN37224"}
    assert quotes["DE000UN37224"].observed_at == datetime(2026, 9, 16, 20, 58, 0, 1, tzinfo=UTC)
    assert quotes["DE000UN37224"].bid == Decimal("1.23")


def test_streaming_scan_rejects_conflicting_duplicate_timestamp() -> None:
    content = "\n".join(
        [
            "DE000UN37224,20:58:00.000001,EUR,1.23,120,1.24,110",
            "DE000UN37224,20:58:00.000001,EUR,1.22,120,1.24,110",
        ]
    ).encode()

    with pytest.raises(
        GettexPayloadError,
        match="GETTEX_DUPLICATE_TIMESTAMP_CONFLICT",
    ):
        scan_gzip_quotes(
            BytesIO(gzip.compress(content)),
            file_name="pretrade.20260916.21.00.mund.csv.gz",
            tracked_isins={"DE000UN37224"},
        )


def test_streaming_scan_rejects_truncated_gzip() -> None:
    content = b"DE000UN37224,20:58:00.000001,EUR,1.23,120,1.24,110\n"
    compressed = gzip.compress(content)

    with pytest.raises(GettexPayloadError, match="GETTEX_GZIP_INVALID"):
        scan_gzip_quotes(
            BytesIO(compressed[:-8]),
            file_name="pretrade.20260916.21.00.mund.csv.gz",
            tracked_isins={"DE000UN37224"},
        )
