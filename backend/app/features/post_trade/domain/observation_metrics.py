"""Deterministic FT-011 observation selection and evidence metrics."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from app.features.post_trade.application.ports import DailyObservation


@dataclass(frozen=True, slots=True)
class ObservedExtreme:
    trading_date: date
    value: Decimal


@dataclass(frozen=True, slots=True)
class LevelCrossing:
    level: Decimal
    crossed: bool
    first_crossed_on: date | None


@dataclass(frozen=True, slots=True)
class ObservationEvidence:
    points: tuple[DailyObservation, ...]
    available_observation_count: int
    target_observation_count: int
    horizon_complete: bool

    highest_high: ObservedExtreme | None
    lowest_low: ObservedExtreme | None
    final_close: ObservedExtreme | None

    target_crossings: tuple[LevelCrossing, ...]
    stop_crossing: LevelCrossing | None


def select_observation_points(
    values: Iterable[DailyObservation],
    *,
    full_exit_at: datetime,
    target_count: int,
) -> tuple[DailyObservation, ...]:
    """Return chronological real EOD observations after the full-exit date.

    Same-day EOD is excluded even when the exit occurred intraday.
    Missing/non-trading dates are not synthesized.
    """
    if target_count <= 0:
        raise ValueError("target_count must be positive")

    eligible = sorted(
        (value for value in values if value.trading_date > full_exit_at.date()),
        key=lambda value: (
            value.trading_date,
            value.listing_id,
        ),
    )

    seen_dates: set[date] = set()
    result: list[DailyObservation] = []

    for value in eligible:
        if value.trading_date in seen_dates:
            raise ValueError("multiple observation points for the same trading_date")
        seen_dates.add(value.trading_date)
        result.append(value)

        if len(result) == target_count:
            break

    return tuple(result)


def build_observation_evidence(
    values: Iterable[DailyObservation],
    *,
    full_exit_at: datetime,
    target_count: int,
    targets: tuple[Decimal, ...] = (),
    stop: Decimal | None = None,
) -> ObservationEvidence:
    points = select_observation_points(
        values,
        full_exit_at=full_exit_at,
        target_count=target_count,
    )

    highest_high = (
        max(
            (
                ObservedExtreme(
                    trading_date=value.trading_date,
                    value=value.high,
                )
                for value in points
            ),
            key=lambda item: (item.value, -item.trading_date.toordinal()),
        )
        if points
        else None
    )

    lowest_low = (
        min(
            (
                ObservedExtreme(
                    trading_date=value.trading_date,
                    value=value.low,
                )
                for value in points
            ),
            key=lambda item: (item.value, item.trading_date),
        )
        if points
        else None
    )

    final_close = (
        ObservedExtreme(
            trading_date=points[-1].trading_date,
            value=points[-1].close,
        )
        if points
        else None
    )

    target_crossings = tuple(_first_high_crossing(points, level) for level in targets)

    stop_crossing = _first_low_crossing(points, stop) if stop is not None else None

    return ObservationEvidence(
        points=points,
        available_observation_count=len(points),
        target_observation_count=target_count,
        horizon_complete=len(points) == target_count,
        highest_high=highest_high,
        lowest_low=lowest_low,
        final_close=final_close,
        target_crossings=target_crossings,
        stop_crossing=stop_crossing,
    )


def _first_high_crossing(
    points: tuple[DailyObservation, ...],
    level: Decimal,
) -> LevelCrossing:
    if level <= 0:
        raise ValueError("target level must be positive")

    first = next(
        (value.trading_date for value in points if value.high >= level),
        None,
    )

    return LevelCrossing(
        level=level,
        crossed=first is not None,
        first_crossed_on=first,
    )


def _first_low_crossing(
    points: tuple[DailyObservation, ...],
    level: Decimal,
) -> LevelCrossing:
    if level <= 0:
        raise ValueError("stop level must be positive")

    first = next(
        (value.trading_date for value in points if value.low <= level),
        None,
    )

    return LevelCrossing(
        level=level,
        crossed=first is not None,
        first_crossed_on=first,
    )
