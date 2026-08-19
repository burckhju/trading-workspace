"""Deterministic FT-011 review-input fingerprint."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.features.post_trade.application.ports import (
    PlanningContext,
    TradeExitContext,
)
from app.features.post_trade.domain.observation_metrics import (
    ObservationEvidence,
)


@dataclass(frozen=True, slots=True)
class ExitReviewFingerprintInput:
    trade: TradeExitContext
    planning: PlanningContext
    evidence: ObservationEvidence


def build_exit_review_input_fingerprint(
    *,
    trade: TradeExitContext,
    planning: PlanningContext,
    evidence: ObservationEvidence,
) -> str:
    payload = ExitReviewFingerprintInput(
        trade=trade,
        planning=planning,
        evidence=evidence,
    )

    normalized = _normalize(asdict(payload))

    encoded = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(encoded).hexdigest()


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _normalize(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }

    if isinstance(value, (tuple, list)):
        return [_normalize(item) for item in value]

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, Decimal):
        return format(value, "f")

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, bool) or value is None:
        return value

    if isinstance(value, (str, int, float)):
        return value

    raise TypeError(f"unsupported fingerprint value type: {type(value).__name__}")
