import argparse
import csv
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.config.frankfurt import FrankfurtSourceMode
from app.providers.frankfurt_quotes import probe
from app.providers.frankfurt_quotes.public import FrankfurtPublicPrice
from app.providers.frankfurt_quotes.schema import FrankfurtSnapshot, FrankfurtSourceError
from tests.unit.backend.providers.frankfurt_quotes.test_public import public_settings, wire
from tests.unit.backend.providers.frankfurt_quotes.test_schema import NOW, payload


def arguments(tmp_path):
    source = tmp_path / "input.csv"
    source.write_text("ISIN;WKN\nDE000VH2LU21;VH2LU2\n;UNKNOWN\n", encoding="utf-8")
    return argparse.Namespace(
        input=source,
        output=tmp_path / "result.csv",
        delimiter=";",
        isin_column="ISIN",
        wkn_column="WKN",
        currency="EUR",
    )


@pytest.mark.asyncio
async def test_probe_fetches_once_and_does_not_guess_or_modify_input(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, "utc_now", lambda: NOW)
    args = arguments(tmp_path)
    original = args.input.read_bytes()
    client = SimpleNamespace(
        load=AsyncMock(return_value=(FrankfurtSnapshot.model_validate(payload()), NOW, False)),
        settings=SimpleNamespace(
            source_name="test-vendor",
            max_quote_age_seconds=900,
            source_mode=FrankfurtSourceMode.HTTPS_JSON,
        ),
    )
    counts = await probe.run(args, client)
    assert counts == {"AVAILABLE": 1, "UNAVAILABLE": 1}
    client.load.assert_awaited_once()
    assert args.input.read_bytes() == original
    with args.output.open(encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle, delimiter=";"))
    assert rows[0]["bid"] == "0.32"
    assert rows[0]["execution_usable"] == "false"
    assert rows[1]["reason"] == "ISIN_REQUIRED_NO_WKN_GUESSING"
    saved = args.output.read_bytes()
    with pytest.raises(FileExistsError):
        await probe.run(args, client)
    assert args.output.read_bytes() == saved


@pytest.mark.asyncio
async def test_probe_unavailable_source_is_not_coverage_evidence(tmp_path):
    args = arguments(tmp_path)
    client = SimpleNamespace(
        load=AsyncMock(side_effect=FrankfurtSourceError("FRANKFURT_DISABLED")),
        settings=SimpleNamespace(source_name=None, source_mode=FrankfurtSourceMode.HTTPS_JSON),
    )
    assert await probe.run(args, client) == {"UNAVAILABLE": 2}
    assert "FRANKFURT_DISABLED" in args.output.read_text(encoding="utf-8-sig")


@pytest.mark.asyncio
async def test_public_csv_reports_last_separately_and_waits_for_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(probe, "utc_now", lambda: NOW)
    sleep = AsyncMock()
    monkeypatch.setattr(probe.asyncio, "sleep", sleep)
    args = arguments(tmp_path)
    args.input.write_text("ISIN;WKN\nDE000VH2LU21;VH2LU2\nDE000VH7S657;VH7S65\n")
    client = SimpleNamespace(
        settings=public_settings(),
        load=AsyncMock(),
        load_public=AsyncMock(
            side_effect=[
                (FrankfurtPublicPrice.model_validate(wire()), NOW, False),
                FrankfurtSourceError("FRANKFURT_REQUEST_THROTTLED"),
                (FrankfurtPublicPrice.model_validate(wire(isin="DE000VH7S657")), NOW, False),
            ]
        ),
    )
    assert await probe.run(args, client) == {"INSUFFICIENT": 2}
    sleep.assert_awaited_once_with(15)
    client.load.assert_not_awaited()
    with args.output.open(encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle, delimiter=";"))
    assert rows[0]["last_price"] == "0.231"
    assert rows[0]["bid"] == rows[0]["ask"] == rows[0]["delay_seconds"] == ""
    assert rows[0]["provider_exchange_code"] == "XSC"
    assert rows[0]["source_mode"] == "OFFICIAL_WEBSITE_LAST_TRADE"
    assert rows[1]["isin"] == "DE000VH7S657"


@pytest.mark.asyncio
async def test_public_csv_empty_response_is_not_success(tmp_path):
    args = arguments(tmp_path)
    client = SimpleNamespace(
        settings=public_settings(),
        load_public=AsyncMock(side_effect=FrankfurtSourceError("FRANKFURT_PUBLIC_EMPTY_RESPONSE")),
    )
    assert await probe.run(args, client) == {"ERROR": 1, "UNAVAILABLE": 1}
    assert "FRANKFURT_PUBLIC_EMPTY_RESPONSE" in args.output.read_text(encoding="utf-8-sig")
