"""Contract tests for versioned EODHD daily-price fixtures."""

import json
from pathlib import Path

from app.providers.eodhd.dto import EodhdDailyPriceDto

FIXTURE = Path(__file__).with_name("fixtures") / "daily_prices.v1.json"


def test_versioned_daily_price_fixture_matches_transport_contract() -> None:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rows = tuple(EodhdDailyPriceDto.model_validate(item) for item in payload)
    assert len(rows) == 2
    assert rows[0].date.isoformat() == "2026-08-01"
    assert rows[1].volume is None
