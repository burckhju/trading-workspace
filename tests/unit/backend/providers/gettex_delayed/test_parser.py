import gzip
from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO

import pytest

from app.providers.gettex_delayed.parser import (
    GettexPayloadError,
    parse_file_window,
    parse_quote_row,
    scan_gzip_quote_batch,
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


@pytest.mark.parametrize(
    ("bad_row", "reason"),
    [
        ("20:50:00.000001,EUR,1.23,100,0,100", "GETTEX_ROW_ASK_NOT_POSITIVE"),
        ("20:50:00.000001,EUR,0,100,1.24,100", "GETTEX_ROW_BID_NOT_POSITIVE"),
        ("20:50:00.000001,EUR,1.23,100,-1,100", "GETTEX_ROW_ASK_NOT_POSITIVE"),
        ("20:50:00.000001,EUR,1.23,100,NaN,100", "GETTEX_ROW_ASK_INVALID"),
        ("20:50:00.000001,EUR,1.25,100,1.24,100", "GETTEX_ROW_CROSSED_QUOTE"),
        ("20:50:00.000001,EUR,1.23", "GETTEX_ROW_FIELD_COUNT_INVALID"),
        ("20:44:59.000001,EUR,1.23,100,1.24,100", "GETTEX_ROW_TIME_OUTSIDE_FILE_WINDOW"),
    ],
)
def test_batch_isolates_invalid_product_without_promoting_its_other_rows(
    bad_row: str, reason: str
) -> None:
    content = "\n".join(
        [
            "DE000UN37224,20:46:00.000001,EUR,1.20,100,1.21,100",
            f"DE000UN37224,{bad_row}",
            "IE000HFBJ0U0,20:55:00.000001,EUR,19.128,600,19.682,600",
            "DE000UN37224,20:58:00.000001,EUR,1.23,120,1.24,110",
        ]
    ).encode()
    batch = scan_gzip_quote_batch(
        BytesIO(gzip.compress(content)),
        file_name="pretrade.20260916.21.00.mund.csv.gz",
        tracked_isins={"DE000UN37224", "IE000HFBJ0U0"},
    )

    assert batch.errors == {"DE000UN37224": reason}
    assert set(batch.quotes) == {"IE000HFBJ0U0"}
    assert batch.quotes["IE000HFBJ0U0"].bid == Decimal("19.128")
    assert batch.quotes["IE000HFBJ0U0"].observed_at == datetime(
        2026, 9, 16, 20, 55, 0, 1, tzinfo=UTC
    )


def test_batch_conflicting_timestamp_excludes_only_affected_isin() -> None:
    content = "\n".join(
        [
            "DE000UN37224,20:58:00.000001,EUR,1.23,120,1.24,110",
            "IE000HFBJ0U0,20:59:00.000001,EUR,19.128,600,19.682,600",
            "DE000UN37224,20:58:00.000001,EUR,1.22,120,1.24,110",
        ]
    ).encode()
    batch = scan_gzip_quote_batch(
        BytesIO(gzip.compress(content)),
        file_name="pretrade.20260916.21.00.mund.csv.gz",
        tracked_isins={"DE000UN37224", "IE000HFBJ0U0"},
    )

    assert batch.errors == {"DE000UN37224": "GETTEX_DUPLICATE_TIMESTAMP_CONFLICT"}
    assert set(batch.quotes) == {"IE000HFBJ0U0"}


def test_batch_checks_gzip_integrity_even_after_an_isolated_row_failure() -> None:
    content = (
        b"DE000UN37224,20:50:00.000001,EUR,1.23,100,0,100\n"
        b"IE000HFBJ0U0,20:59:00.000001,EUR,19.128,600,19.682,600\n"
    )
    with pytest.raises(GettexPayloadError, match="GETTEX_GZIP_INVALID"):
        scan_gzip_quote_batch(
            BytesIO(gzip.compress(content)[:-8]),
            file_name="pretrade.20260916.21.00.mund.csv.gz",
            tracked_isins={"DE000UN37224", "IE000HFBJ0U0"},
        )


def test_batch_ignores_untracked_invalid_quotes() -> None:
    content = (
        b"DE000UN37224,20:50:00.000001,EUR,1.23,100,0,100\n"
        b"IE000HFBJ0U0,20:59:00.000001,EUR,19.128,600,19.682,600\n"
    )
    batch = scan_gzip_quote_batch(
        BytesIO(gzip.compress(content)),
        file_name="pretrade.20260916.21.00.mund.csv.gz",
        tracked_isins={"IE000HFBJ0U0"},
    )
    assert not batch.errors
    assert set(batch.quotes) == {"IE000HFBJ0U0"}
