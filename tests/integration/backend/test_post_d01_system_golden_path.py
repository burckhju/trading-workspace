from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from app.features.analysis.domain.calculator import calculate
from app.features.analysis.domain.enums import PriceField
from app.features.analysis.domain.models import AnalysisParameters, SnapshotRow
from app.features.analysis.domain.top_down import (
    TradingDirection,
    calculate_market_context,
    calculate_relative_strength,
)
from app.features.candidate.domain.enums import CandidateQualification
from app.features.candidate.domain.models import CandidateEvaluationInput
from app.features.candidate.domain.qualification import evaluate_candidate


@dataclass(frozen=True, slots=True)
class ReferenceAnalysisPath:
    """Released D01 identity boundary carried into downstream calculations."""

    market_reference_id: UUID
    market_data_instrument_id: UUID
    listing_id: None
    criteria: dict[str, object]
    prices: tuple[Decimal, ...]
    quality_status: object
    volatility: Decimal
    range_position: Decimal


def _snapshot_series(
    symbol: str, *, start: Decimal, daily_step: Decimal
) -> tuple[SnapshotRow, ...]:
    rows: list[SnapshotRow] = []
    current = date(2025, 10, 1)
    for index in range(220):
        while current.weekday() >= 5:
            current += timedelta(days=1)
        close = start + daily_step * Decimal(index)
        rows.append(
            SnapshotRow(
                trading_date=current,
                open=close,
                high=close * Decimal("1.002"),
                low=close * Decimal("0.998"),
                close=close,
                adjusted_close=close,
                volume=Decimal("1000000"),
                currency="USD",
                provider="EODHD",
                provider_symbol=symbol,
                quality_status="GOOD",
                warnings=(),
            )
        )
        current += timedelta(days=1)
    return tuple(rows)


def _analyze(
    symbol: str, *, start: Decimal, daily_step: Decimal
) -> tuple[dict[str, object], tuple[Decimal, ...], object, Decimal, Decimal]:
    rows = _snapshot_series(symbol, start=start, daily_step=daily_step)
    computation = calculate(
        AnalysisParameters(price_field=PriceField.ADJUSTED_CLOSE),
        rows,
    )
    criteria = {item.code: item.classification for item in computation.criteria}
    prices = tuple(item.adjusted_close for item in rows if item.adjusted_close is not None)
    volatility = next(item.value for item in computation.criteria if item.code == "VOLATILITY")
    range_position = next(
        item.value for item in computation.criteria if item.code == "RANGE_POSITION"
    )
    return criteria, prices, computation.quality_status, volatility, range_position


def test_market_reference_mdi_analysis_drives_top_down_candidate_without_listing() -> None:
    market_criteria, market_prices, market_quality, _, _ = _analyze(
        "GSPC.INDX",
        start=Decimal("5000"),
        daily_step=Decimal("5.0"),
    )
    sector_criteria, sector_prices, sector_quality, _, _ = _analyze(
        "TECH.FIXTURE",
        start=Decimal("1000"),
        daily_step=Decimal("2.2"),
    )
    stock_criteria, stock_prices, stock_quality, stock_volatility, stock_range = _analyze(
        "MSFT.US",
        start=Decimal("300"),
        daily_step=Decimal("1.2"),
    )

    market_reference = ReferenceAnalysisPath(
        market_reference_id=uuid4(),
        market_data_instrument_id=uuid4(),
        listing_id=None,
        criteria=market_criteria,
        prices=market_prices,
        quality_status=market_quality,
        volatility=Decimal("0"),
        range_position=Decimal("0"),
    )

    assert market_reference.listing_id is None
    assert market_reference.market_data_instrument_id != market_reference.market_reference_id

    market_context = calculate_market_context(
        direction=TradingDirection.LONG,
        long_trend=market_reference.criteria["LONG_TREND"],
        medium_trend=market_reference.criteria["MEDIUM_TREND"],
        short_trend=market_reference.criteria["SHORT_TREND"],
        quality_status=market_reference.quality_status,
    )
    sector_rs = calculate_relative_strength(sector_prices, market_reference.prices)
    stock_rs = calculate_relative_strength(stock_prices, sector_prices)

    candidate = evaluate_candidate(
        CandidateEvaluationInput(
            direction=TradingDirection.LONG,
            market_context=market_context.classification,
            market_quality=market_context.quality_status,
            sector_trend=sector_criteria["LONG_TREND"],
            sector_relative_strength=sector_rs.classification,
            sector_quality=sector_quality,
            underlying_long_trend=stock_criteria["LONG_TREND"],
            underlying_medium_trend=stock_criteria["MEDIUM_TREND"],
            underlying_short_trend=stock_criteria["SHORT_TREND"],
            underlying_relative_strength=stock_rs.classification,
            underlying_quality=stock_quality,
            momentum=stock_criteria["MOMENTUM_120"],
            volatility=stock_volatility,
            range_position=stock_range,
        )
    )

    assert market_context.classification.value == "FAVORABLE"
    assert sector_rs.classification.value == "POSITIVE"
    assert stock_rs.classification.value == "POSITIVE"
    assert candidate.qualification is CandidateQualification.QUALIFIED
    assert candidate.model_id == "TOP_DOWN_CANDIDATE"
    assert candidate.model_version == "1.0.0"
