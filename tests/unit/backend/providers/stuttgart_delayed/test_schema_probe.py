import gzip
import json
from pathlib import Path

from app.providers.stuttgart_delayed.schema_probe import (
    candidate_field_hints,
    discover_record_arrays,
    load_gzipped_json,
    render_report,
)


def _payload():
    return {
        "meta": {"generated": "2026-09-04T21:53:00Z"},
        "records": [
            {
                "instrument": {"isin": "DE000TEST123"},
                "venue": {"mic": "XSTU"},
                "quote": {
                    "side": "BID",
                    "price": 2.42,
                    "currency": "EUR",
                    "observed_at": "2026-09-04T21:53:00Z",
                },
            },
            {
                "instrument": {"isin": "DE000TEST123"},
                "venue": {"mic": "XSTU"},
                "quote": {
                    "side": "ASK",
                    "price": 2.47,
                    "currency": "EUR",
                    "observed_at": "2026-09-04T21:53:00Z",
                },
            },
        ],
    }


def test_discovers_structural_record_array_without_values() -> None:
    candidates = discover_record_arrays(_payload())

    records = next(candidate for candidate in candidates if candidate.path == "records")
    assert records.item_count == 2
    assert records.object_count == 2
    assert "instrument.isin" in records.leaf_paths
    assert "quote.price" in records.leaf_paths
    assert ("quote.price", ("number",)) in records.leaf_types


def test_field_hints_are_name_based_only() -> None:
    records = next(
        candidate for candidate in discover_record_arrays(_payload()) if candidate.path == "records"
    )

    hints = candidate_field_hints(records)

    assert hints["isin"] == ("instrument.isin",)
    assert "venue.mic" in hints["mic"]
    assert "quote.side" in hints["side"]
    assert "quote.price" in hints["price"]
    assert "quote.currency" in hints["currency"]
    assert "quote.observed_at" in hints["timestamp"]


def test_report_does_not_emit_market_data_values() -> None:
    report = render_report(_payload())

    assert "candidate[1]" in report
    assert "instrument.isin" in report
    assert "quote.price" in report
    assert "DE000TEST123" not in report
    assert "2.42" not in report
    assert "EUR" not in report


def test_loads_gzipped_json(tmp_path: Path) -> None:
    path = tmp_path / "XSTU-pretrade-fixture.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        json.dump(_payload(), handle)

    assert load_gzipped_json(path) == _payload()
