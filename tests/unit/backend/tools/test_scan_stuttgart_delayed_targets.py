import gzip
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from app.core.config.settings import StuttgartDelayedSettings
from app.tools.scan_stuttgart_delayed_targets import (
    OpenTarget,
    _load_official_payload,
    _render_result,
    scan_target_quotes,
)

TARGET = "DE000MN50FN0"
OTHER = "DE000JE7KTY8"


def _record(
    *,
    isin: str = TARGET,
    mic: str = "XSTU",
    bid: str = "0.41",
    ask: str = "0.43",
    currency: str = "EUR",
    observed_at: str = "2026-09-18T19:45:00Z",
) -> dict[str, str]:
    return {
        "Isin": isin,
        "VenueOfPublication": mic,
        "Bid": bid,
        "Ask": ask,
        "PriceCurrency": currency,
        "TransactionTime": observed_at,
    }


def test_scan_selects_latest_exact_xstu_eur_quote() -> None:
    quotes, rejected = scan_target_quotes(
        [
            _record(bid="9.99", observed_at="2026-09-18T19:30:00Z"),
            _record(bid="0.42"),
            _record(isin=OTHER),
            _record(mic="XETR", bid="7.77"),
        ],
        target_isins={TARGET},
        settings=StuttgartDelayedSettings(),
    )

    assert rejected == {}
    assert quotes[TARGET].bid == Decimal("0.42")
    assert quotes[TARGET].ask == Decimal("0.43")
    assert quotes[TARGET].currency == "EUR"
    assert quotes[TARGET].observed_at == datetime(2026, 9, 18, 19, 45, tzinfo=UTC)


def test_scan_combines_sides_at_same_latest_timestamp_and_reports_rejections() -> None:
    quotes, rejected = scan_target_quotes(
        [
            _record(bid="0.41", ask="0"),
            _record(bid="0", ask="0.43"),
            _record(currency="USD"),
            _record(bid="0", ask="0"),
        ],
        target_isins={TARGET},
        settings=StuttgartDelayedSettings(),
    )

    assert quotes[TARGET].bid == Decimal("0.41")
    assert quotes[TARGET].ask == Decimal("0.43")
    assert rejected == {TARGET: 2}


def test_scan_fails_closed_for_changed_schema_invalid_price_and_crossed_quote() -> None:
    with pytest.raises(ValueError, match="VERIFIED_SCHEMA_REQUIRED"):
        scan_target_quotes(
            [_record()],
            target_isins={TARGET},
            settings=StuttgartDelayedSettings(isin_field="instrument.isin"),
        )

    with pytest.raises(ValueError, match="PRICE_INVALID"):
        scan_target_quotes(
            [_record(bid="NaN")],
            target_isins={TARGET},
            settings=StuttgartDelayedSettings(),
        )

    with pytest.raises(ValueError, match="QUOTE_CROSSED"):
        scan_target_quotes(
            [_record(bid="0.44", ask="0.43")],
            target_isins={TARGET},
            settings=StuttgartDelayedSettings(),
        )


def test_load_requires_official_filename_and_returns_compressed_hash(
    tmp_path: Path,
) -> None:
    path = tmp_path / "XSTU-pretrade-20260918T1945.json.gz"
    compressed = gzip.compress(json.dumps([_record()]).encode())
    path.write_bytes(compressed)

    payload, digest = _load_official_payload(path)

    assert payload == [_record()]
    assert len(digest) == 64

    invalid_name = tmp_path / "download.json.gz"
    invalid_name.write_bytes(compressed)
    with pytest.raises(ValueError, match="FILE_NAME_INVALID"):
        _load_official_payload(invalid_name)


def test_load_rejects_empty_official_payload(tmp_path: Path) -> None:
    path = tmp_path / "XSTU-pretrade-20260918T2153.json.gz"
    path.write_bytes(gzip.compress(b"[]"))

    with pytest.raises(ValueError, match="SOURCE_FILE_EMPTY"):
        _load_official_payload(path)


def test_rendered_result_contains_auditable_identity_without_apply_controls() -> None:
    position_id = UUID("11111111-1111-4111-8111-111111111111")
    warrant_id = UUID("22222222-2222-4222-8222-222222222222")
    selection_id = UUID("33333333-3333-4333-8333-333333333333")
    target = OpenTarget(
        position_id=position_id,
        warrant_id=warrant_id,
        selection_id=selection_id,
        isin=TARGET,
        selection_status="NO_VERIFIED_QUOTE_SOURCE",
        selection_reason="NO_ALLOWED_VERIFIED_QUOTE_SOURCE",
    )
    quotes, rejected = scan_target_quotes(
        [_record()],
        target_isins={TARGET},
        settings=StuttgartDelayedSettings(),
    )

    report = _render_result(
        source_file="XSTU-pretrade-20260918T1945.json.gz",
        source_sha256="a" * 64,
        targets=[target],
        missing_isin_positions=0,
        quotes=quotes,
        rejected_rows=rejected,
        schema_version="xstu-pretrade-flat-2026-09-04",
    )

    assert report["read_only"] is True
    assert report["matched_count"] == 1
    assert report["missing_count"] == 0
    assert report["source_sha256"] == "a" * 64
    assert report["matched"] == [
        {
            "isin": TARGET,
            "position_ids": [str(position_id)],
            "warrant_ids": [str(warrant_id)],
            "selection_ids": [str(selection_id)],
            "selection_statuses": ["NO_VERIFIED_QUOTE_SOURCE"],
            "selection_reasons": ["NO_ALLOWED_VERIFIED_QUOTE_SOURCE"],
            "bid": "0.41",
            "ask": "0.43",
            "currency": "EUR",
            "observed_at": "2026-09-18T19:45:00+00:00",
        }
    ]
    assert "apply" not in report
