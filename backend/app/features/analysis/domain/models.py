"""Immutable domain values for transparent, reproducible analysis."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from hashlib import sha256
from typing import Any

from app.features.analysis.domain.enums import (
    AnalysisQualityStatus,
    CriterionClassification,
    PriceField,
)
from app.features.analysis.domain.errors import InvalidAnalysisParameters


@dataclass(frozen=True, slots=True)
class AnalysisParameters:
    price_field: PriceField = PriceField.ADJUSTED_CLOSE
    short_window: int = 20
    medium_window: int = 50
    long_window: int = 200
    momentum_windows: tuple[int, ...] = (20, 60, 120)
    volatility_window: int = 20
    range_window: int = 52
    minimum_required_observations: int = 200
    maximum_data_age_days: int = 7
    annualization_factor: Decimal = Decimal("252")
    rounding_scale: int = 6

    def __post_init__(self) -> None:
        windows = (
            self.short_window,
            self.medium_window,
            self.long_window,
            self.volatility_window,
            self.range_window,
            self.minimum_required_observations,
            *self.momentum_windows,
        )
        if any(value <= 0 for value in windows):
            raise InvalidAnalysisParameters("all windows must be positive")
        if not self.short_window < self.medium_window < self.long_window:
            raise InvalidAnalysisParameters(
                "short_window < medium_window < long_window is required"
            )
        if tuple(sorted(set(self.momentum_windows))) != self.momentum_windows:
            raise InvalidAnalysisParameters("momentum_windows must be unique and sorted")
        if self.maximum_data_age_days < 0 or self.rounding_scale < 0 or self.rounding_scale > 12:
            raise InvalidAnalysisParameters("invalid age or rounding scale")
        if self.annualization_factor <= 0:
            raise InvalidAnalysisParameters("annualization_factor must be positive")

    def as_dict(self) -> dict[str, Any]:
        return {
            "price_field": self.price_field.value,
            "short_window": self.short_window,
            "medium_window": self.medium_window,
            "long_window": self.long_window,
            "momentum_windows": list(self.momentum_windows),
            "volatility_window": self.volatility_window,
            "range_window": self.range_window,
            "minimum_required_observations": self.minimum_required_observations,
            "maximum_data_age_days": self.maximum_data_age_days,
            "annualization_factor": str(self.annualization_factor),
            "rounding_scale": self.rounding_scale,
        }


@dataclass(frozen=True, slots=True)
class SnapshotRow:
    trading_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adjusted_close: Decimal | None
    volume: Decimal | None
    currency: str
    provider: str
    provider_symbol: str
    quality_status: str
    warnings: tuple[str, ...]

    def canonical(self) -> dict[str, Any]:
        return {
            "trading_date": self.trading_date.isoformat(),
            "open": str(self.open),
            "high": str(self.high),
            "low": str(self.low),
            "close": str(self.close),
            "adjusted_close": (None if self.adjusted_close is None else str(self.adjusted_close)),
            "volume": None if self.volume is None else str(self.volume),
            "currency": self.currency,
            "provider": self.provider,
            "provider_symbol": self.provider_symbol,
            "quality_status": self.quality_status,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class CriterionResult:
    code: str
    classification: CriterionClassification
    value: Decimal | None
    explanation: str


@dataclass(frozen=True, slots=True)
class AnalysisComputation:
    metrics: dict[str, str | None]
    criteria: tuple[CriterionResult, ...]
    notes: tuple[str, ...]
    quality_status: AnalysisQualityStatus


def calculate_input_hash(
    model_id: str,
    model_version: str,
    parameters: AnalysisParameters,
    rows: tuple[SnapshotRow, ...],
) -> str:
    payload = {
        "model_id": model_id,
        "model_version": model_version,
        "parameters": parameters.as_dict(),
        "rows": [row.canonical() for row in rows],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return sha256(encoded).hexdigest()
