"""Descriptive returns: no invented starts, prices, timestamps or FX."""

from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.features.analysis.domain.enums import PriceField
from app.features.analysis.domain.time_series import compare_series, prepare_series
from app.features.market.service.chart_contracts import ChartIdentity
from app.features.market_data.service.time_series import MAX_SERIES_POINTS, SeriesObservation

DAY = date(2026, 9, 1)
END = date(2026, 10, 1)
NOW = datetime(2026, 10, 2, 12, tzinfo=UTC)


def identity(kind="STOCK", **kwargs):
    return ChartIdentity(f"listing:{uuid4()}", "Fixture", uuid4(), kind, **kwargs)


def observation(offset=0, close="100", adjusted="100", **kwargs):
    value = SeriesObservation(
        DAY + timedelta(days=offset),
        Decimal(close),
        Decimal(adjusted) if adjusted is not None else None,
        "USD",
        "EODHD",
        "TEST",
        NOW,
        None,
        "VALID",
        (),
    )
    return replace(value, **kwargs)


def prepared(rows, *, kind="STOCK", field=PriceField.CLOSE, **kwargs):
    return prepare_series(identity(kind, **kwargs), tuple(rows), field, DAY, END)


def compare(*series, field=PriceField.CLOSE):
    return compare_series(tuple(series), DAY, END, field)


def test_common_observed_start_end_decimal_and_unfilled_gaps():
    first = prepared(
        [
            observation(0, "80"),
            observation(1, "100"),
            observation(2, "110"),
            observation(3, "120"),
            observation(6, "130"),
        ]
    )
    second = prepared([observation(1, "200"), observation(3, "180")])
    result = compare(first, second)
    assert (result.common_start, result.common_end) == (
        DAY + timedelta(days=1),
        DAY + timedelta(days=3),
    )
    assert result.comparison_status == "READY"
    assert [p.normalized for p in result.series[0].points] == [
        None,
        Decimal(100),
        Decimal(110),
        Decimal(120),
        None,
    ]
    assert result.series[1].points[-1].change_percent == Decimal(-10)
    assert result.series[1].missing_comparison_dates == (DAY + timedelta(days=2),)
    assert result.series[1].points[-1].gap_before
    assert "START_MOVED_TO_COMMON_OBSERVATION" in result.issues
    assert all(p.observed_at is None and p.received_at == NOW for p in result.series[0].points)


@pytest.mark.parametrize("close", ["0", "-1", "NaN", "Infinity"])
def test_invalid_first_common_value_is_not_skipped(close):
    result = compare(prepared([observation(0, close), observation(1), observation(2)]))
    assert result.comparison_status == "INVALID_START_VALUE"
    assert result.common_start == DAY
    assert all(p.normalized is None for p in result.series[0].points)


def test_split_and_dividend_adjusted_values_never_fall_back_to_raw_close():
    raw = [observation(0, "200", "98"), observation(1, "100", "100")]
    result = compare(
        prepared(raw, kind="ETF", field=PriceField.ADJUSTED_CLOSE), field=PriceField.ADJUSTED_CLOSE
    )
    assert result.series[0].points[-1].change_percent == Decimal("2.04081633")
    raw_result = compare(prepared(raw, kind="ETF"))
    assert raw_result.series[0].points[-1].change_percent == Decimal(-50)
    assert "UNADJUSTED_SPLITS_AND_DIVIDENDS" in raw_result.series[0].issues
    missing = compare(
        prepared([observation(adjusted=None), observation(1)], field=PriceField.ADJUSTED_CLOSE),
        field=PriceField.ADJUSTED_CLOSE,
    )
    assert missing.comparison_status == "INVALID_START_VALUE"
    assert missing.series[0].points[0].value is None
    assert "PRICE_FIELD_MISSING" in missing.series[0].points[0].warnings


def test_price_index_and_total_return_and_adjusted_etf_are_distinct():
    rows = [observation(), observation(1, "101")]
    index = prepared(
        rows, kind="INDEX", return_basis="PRICE_INDEX", basis_source="https://example.test/index"
    )
    total = prepared(
        rows,
        kind="INDEX",
        return_basis="TOTAL_RETURN_INDEX",
        basis_source="https://example.test/total",
    )
    adjusted = prepared(rows, kind="ETF", field=PriceField.ADJUSTED_CLOSE)
    assert compare(index, prepared(rows)).comparison_status == "READY"
    assert compare(index, total).comparison_status == "INCOMPATIBLE_RETURN_BASIS"
    assert compare(index, adjusted).comparison_status == "INCOMPATIBLE_RETURN_BASIS"
    assert compare(prepared(rows, kind="INDEX")).comparison_status == "RETURN_BASIS_UNKNOWN"
    assert prepared(rows, kind="INDEX", field=PriceField.ADJUSTED_CLOSE).return_basis == "UNKNOWN"
    assert (
        prepared(
            [replace(row, provider="OTHER") for row in rows], field=PriceField.ADJUSTED_CLOSE
        ).return_basis
        == "UNKNOWN"
    )


def test_local_currencies_differ_but_fx_is_never_implied():
    usd = prepared([observation(), observation(1, "110")], currency="USD")
    eur = prepared(
        [observation(currency="EUR"), observation(1, "110", currency="EUR")], currency="EUR"
    )
    result = compare(usd, eur)
    assert result.comparison_status == "READY"
    assert result.fx_adjusted is False
    assert result.issues == ("LOCAL_CURRENCY_NO_FX",)
    conflict = prepared([observation(), observation(1, currency="EUR")])
    assert "CURRENCY_CONFLICT" in conflict.issues
    assert all(point.value is None for point in conflict.points)
    assert compare(conflict).comparison_status == "INVALID_START_VALUE"


def test_bounds_staleness_empty_and_point_limit_are_explicit():
    values = prepare_series(
        identity(),
        (observation(-1), observation(), observation(1), observation(40)),
        PriceField.CLOSE,
        DAY,
        END,
    )
    assert [p.trading_date for p in values.points] == [DAY, DAY + timedelta(days=1)]
    assert "STALE_HISTORY" in values.issues
    empty = prepare_series(identity(active=False), (), PriceField.CLOSE, None, END)
    assert {"NO_HISTORY", "INACTIVE_INSTRUMENT", "MAPPING_NOT_ACTIVE"} <= set(empty.issues)
    assert compare(empty).comparison_status == "SERIES_UNAVAILABLE"
    missing_owner = prepare_series(
        replace(identity(), instrument_id=None), (), PriceField.CLOSE, None, END
    )
    assert "NO_MARKET_DATA_INSTRUMENT" in missing_owner.issues
    many = tuple(observation(0) for _ in range(MAX_SERIES_POINTS + 1))
    limit = prepared(many)
    assert limit.points == () and "POINT_LIMIT_EXCEEDED" in limit.issues


def test_no_common_date_one_day_duplicates_quality_and_provider_conflict():
    assert (
        compare(prepared([observation()]), prepared([observation(1)])).comparison_status
        == "NO_COMMON_DATE"
    )
    assert compare(prepared([observation()])).comparison_status == "INSUFFICIENT_COMMON_HISTORY"
    duplicate = prepared([observation(), observation()])
    assert "DUPLICATE_DATE" in duplicate.issues and duplicate.points[0].value is None
    suspect = prepared([observation(quality="SUSPICIOUS")])
    assert "PRICE_QUALITY_UNUSABLE" in suspect.points[0].warnings
    conflict = prepared([observation()], provider_identity="EODHD:DIFFERENT.US")
    assert conflict.points[0].value is None
    assert "PROVIDER_IDENTITY_CONFLICT" in conflict.points[0].warnings
    valid = prepared([observation()], mapping_status="ACTIVE", provider_identity="EODHD:TEST.US")
    assert valid.points[0].value == Decimal(100)
    assert "MAPPING_NOT_ACTIVE" not in valid.issues


def test_weekend_is_not_fabricated_missing_observation():
    values = prepared([observation(3), observation(6)])  # Friday to Monday
    assert not values.points[1].gap_before
    assert "UNOBSERVED_WEEKDAYS" not in values.issues
    with pytest.raises(ValueError, match="one to four"):
        compare()
    with pytest.raises(ValueError, match="one to four"):
        compare(*[values] * 5)
