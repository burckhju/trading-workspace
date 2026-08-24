from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.features.learning.application.execute_as_trade_service import (
    request_fingerprint,
)


def test_request_fingerprint_is_deterministic() -> None:
    observation_id = uuid4()
    executed_at = datetime(2026, 8, 23, tzinfo=UTC)

    first = request_fingerprint(
        observation_id=observation_id,
        quantity=2,
        price_per_unit=Decimal("12.50"),
        executed_at=executed_at,
    )
    second = request_fingerprint(
        observation_id=observation_id,
        quantity=2,
        price_per_unit=Decimal("12.50"),
        executed_at=executed_at,
    )

    assert first == second
    assert len(first) == 64
