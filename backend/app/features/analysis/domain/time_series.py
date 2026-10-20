"""TIME_SERIES_COMPARISON/1.0.0: explicit EOD alignment and Decimal arithmetic.

This descriptive view neither runs nor persists FT-006 analysis models. All
calculation uses full stored resolution; rounding is only at the output boundary
(8 decimal places, HALF_EVEN). Missing observations are never filled.
"""

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from app.features.analysis.domain.enums import PriceField
from app.features.analysis.domain.models import AnalysisParameters
from app.features.market.service.chart_contracts import ChartIdentity
from app.features.market_data.service.time_series import MAX_SERIES_POINTS, SeriesObservation

MAX_SERIES = 4
MODEL_VERSION = "TIME_SERIES_COMPARISON/1.0.0"


@dataclass(frozen=True)
class ChartPoint:
    trading_date: date
    value: Decimal | None
    normalized: Decimal | None
    change_percent: Decimal | None
    provider: str
    provider_symbol: str
    received_at: datetime
    source_updated_at: datetime | None
    quality: str
    warnings: tuple[str, ...]
    gap_before: bool
    observed_at: None = None


@dataclass(frozen=True)
class ChartSeries:
    identity: ChartIdentity
    currency: str | None
    return_basis: str
    points: tuple[ChartPoint, ...]
    first_date: date | None
    last_date: date | None
    observation_count: int
    issues: tuple[str, ...]
    missing_comparison_dates: tuple[date, ...] = ()


@dataclass(frozen=True)
class ChartComparison:
    series: tuple[ChartSeries, ...]
    requested_start: date | None
    requested_end: date
    price_field: PriceField
    common_start: date | None
    common_end: date | None
    comparison_status: str
    issues: tuple[str, ...]
    model_version: str = MODEL_VERSION
    resolution: str = "EOD_FULL"
    fx_adjusted: bool = False
    calendar_verified: bool = False
    max_points_per_series: int = MAX_SERIES_POINTS


def _basis(identity: ChartIdentity, field: PriceField, providers: set[str]) -> str:
    if identity.instrument_type in {"STOCK", "ETF"}:
        if field is PriceField.CLOSE:
            return "UNADJUSTED_PRICE_CHANGE"
        # Adjustment semantics are a provider contract, never inferred from a name.
        return "SPLIT_DIVIDEND_ADJUSTED_CHANGE" if providers == {"EODHD"} else "UNKNOWN"
    if field is not PriceField.CLOSE:
        return "UNKNOWN"
    if identity.return_basis == "PRICE_INDEX" and identity.basis_source:
        return "UNADJUSTED_PRICE_CHANGE"
    if identity.return_basis == "TOTAL_RETURN_INDEX" and identity.basis_source:
        return "INDEX_TOTAL_RETURN"
    return "UNKNOWN"


def _weekday_gap(previous: date | None, current: date) -> bool:
    if previous is None:
        return False
    probe = previous + timedelta(days=1)
    while probe < current:
        if probe.weekday() < 5:
            return True
        probe += timedelta(days=1)
    return False


def prepare_series(
    identity: ChartIdentity,
    rows: tuple[SeriesObservation, ...],
    field: PriceField,
    start: date | None,
    end: date,
) -> ChartSeries:
    selected = tuple(
        sorted(
            (
                row
                for row in rows
                if (start is None or row.trading_date >= start) and row.trading_date <= end
            ),
            key=lambda row: row.trading_date,
        )
    )
    issues: list[str] = []
    if not identity.active:
        issues.append("INACTIVE_INSTRUMENT")
    if identity.instrument_id is None:
        issues.append("NO_MARKET_DATA_INSTRUMENT")
    if identity.mapping_status != "ACTIVE":
        issues.append("MAPPING_NOT_ACTIVE")
    if len(selected) > MAX_SERIES_POINTS:
        return ChartSeries(
            identity,
            identity.currency,
            "UNKNOWN",
            (),
            None,
            None,
            len(selected),
            (*issues, "POINT_LIMIT_EXCEEDED"),
        )
    currencies = {row.currency for row in selected}
    currency = next(iter(currencies)) if len(currencies) == 1 else identity.currency
    if len(currencies) > 1 or (
        currencies and identity.currency and currencies != {identity.currency}
    ):
        issues.append("CURRENCY_CONFLICT")
    if len({row.trading_date for row in selected}) != len(selected):
        issues.append("DUPLICATE_DATE")
    basis = _basis(identity, field, {row.provider for row in selected})
    if basis == "UNKNOWN":
        issues.append("RETURN_BASIS_UNKNOWN")
    if not selected:
        issues.append("NO_HISTORY")
    elif (end - selected[-1].trading_date).days > AnalysisParameters().maximum_data_age_days:
        issues.append("STALE_HISTORY")
    if len(selected) == 1:
        issues.append("INSUFFICIENT_HISTORY")
    if field is PriceField.CLOSE and identity.instrument_type in {"STOCK", "ETF"}:
        issues.append("UNADJUSTED_SPLITS_AND_DIVIDENDS")
    points: list[ChartPoint] = []
    previous: date | None = None
    for row in selected:
        value = row.close if field is PriceField.CLOSE else row.adjusted_close
        warnings = list(row.warnings)
        if value is None:
            warnings.append("PRICE_FIELD_MISSING")
        elif not value.is_finite() or value <= 0:
            warnings.append("NON_POSITIVE_PRICE")
            value = None
        if row.quality not in {"VALID", "INCOMPLETE"}:
            warnings.append("PRICE_QUALITY_UNUSABLE")
            value = None
        if identity.provider_identity:
            provider, _, symbol_exchange = identity.provider_identity.partition(":")
            symbol = symbol_exchange.rpartition(".")[0]
            if row.provider != provider or row.provider_symbol != symbol:
                warnings.append("PROVIDER_IDENTITY_CONFLICT")
                value = None
        if "CURRENCY_CONFLICT" in issues or "DUPLICATE_DATE" in issues:
            value = None
        gap = _weekday_gap(previous, row.trading_date)
        if gap and "UNOBSERVED_WEEKDAYS" not in issues:
            issues.append("UNOBSERVED_WEEKDAYS")
        points.append(
            ChartPoint(
                row.trading_date,
                value,
                None,
                None,
                row.provider,
                row.provider_symbol,
                row.received_at,
                row.source_updated_at,
                row.quality,
                tuple(warnings),
                gap,
            )
        )
        previous = row.trading_date
    return ChartSeries(
        identity,
        currency,
        basis,
        tuple(points),
        selected[0].trading_date if selected else None,
        selected[-1].trading_date if selected else None,
        len(selected),
        tuple(issues),
    )


def compare_series(
    series: tuple[ChartSeries, ...], start: date | None, end: date, field: PriceField
) -> ChartComparison:
    if not 1 <= len(series) <= MAX_SERIES:
        raise ValueError("one to four series required")
    issues: list[str] = []
    status = "READY"
    common_start: date | None = None
    common_end: date | None = None
    dates = [{point.trading_date for point in item.points} for item in series]
    common = set.intersection(*dates)
    if any(not item.points for item in series):
        status = "SERIES_UNAVAILABLE"
    elif not common:
        status = "NO_COMMON_DATE"
    elif len({item.return_basis for item in series}) != 1:
        status = "INCOMPATIBLE_RETURN_BASIS"
    elif series[0].return_basis == "UNKNOWN":
        status = "RETURN_BASIS_UNKNOWN"
    else:
        common_start, common_end = min(common), max(common)
        bases = [
            next(point.value for point in item.points if point.trading_date == common_start)
            for item in series
        ]
        if any(value is None or value <= 0 for value in bases):
            status = "INVALID_START_VALUE"
        elif common_start == common_end:
            status = "INSUFFICIENT_COMMON_HISTORY"
        else:
            union = set.union(*dates)
            aligned: list[ChartSeries] = []
            for item, base, item_dates in zip(series, bases, dates, strict=True):
                assert base is not None
                aligned_points: list[ChartPoint] = []
                for point in item.points:
                    if point.value is not None and common_start <= point.trading_date <= common_end:
                        with localcontext() as context:
                            context.prec = 40
                            normalized = point.value / base * Decimal(100)
                            change = normalized - Decimal(100)
                            scale = Decimal("0.00000001")
                            point = replace(
                                point,
                                normalized=normalized.quantize(scale, rounding=ROUND_HALF_EVEN),
                                change_percent=change.quantize(scale, rounding=ROUND_HALF_EVEN),
                            )
                    aligned_points.append(point)
                missing = tuple(
                    sorted(
                        day
                        for day in union
                        if common_start <= day <= common_end and day not in item_dates
                    )
                )
                aligned.append(
                    replace(item, points=tuple(aligned_points), missing_comparison_dates=missing)
                )
            series = tuple(aligned)
    if len({item.currency for item in series}) > 1:
        issues.append("LOCAL_CURRENCY_NO_FX")
    if common_start and start and common_start != start:
        issues.append("START_MOVED_TO_COMMON_OBSERVATION")
    return ChartComparison(
        series, start, end, field, common_start, common_end, status, tuple(issues)
    )
