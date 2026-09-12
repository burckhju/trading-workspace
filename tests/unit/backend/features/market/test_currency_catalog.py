"""Offline schema, source metadata and CLI safety regressions."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.features.market.api.currency_router import CatalogPreviewRequest, _catalog
from app.features.market.service.currency_administration import currency_audit_id
from app.features.market.service.currency_catalog_contract import (
    MAX_CATALOG_BYTES,
    bundled_catalog,
    parse_catalog,
)
from app.tools.import_currency_catalog import main, read_catalog


def test_bundle_covers_verified_monetary_subset_and_non_two_minor_units():
    catalog = bundled_catalog()
    assert len(catalog.entries) == 38
    entries = {item.code: item for item in catalog.entries}
    assert entries["JPY"].minor_unit == 0
    assert entries["KWD"].minor_unit == 3
    assert entries["USD"].minor_unit == entries["CHF"].minor_unit == 2
    assert entries["GBP"].numeric_code == "826"
    assert parse_catalog(json.dumps(catalog.document())).checksum == catalog.checksum
    doc = catalog.document()
    doc["entries"].reverse()
    assert parse_catalog(json.dumps(doc)).checksum == catalog.checksum
    assert read_catalog(None) == catalog
    assert _catalog(CatalogPreviewRequest()).checksum == catalog.checksum
    assert currency_audit_id("GBP") == currency_audit_id("GBP") != currency_audit_id("JPY")


@pytest.mark.parametrize(
    "field,value",
    [
        ("code", "usd"),
        ("code", "PT"),
        ("code", "XXX"),
        ("code", "XAU"),
        ("code", "CLF"),
        ("minor_unit", True),
        ("minor_unit", -1),
        ("minor_unit", 7),
        ("minor_unit", "2"),
        ("numeric_code", "1"),
        ("name", " Foo"),
        ("name", "Foo\nBar"),
        ("kind", "FUND"),
    ],
)
def test_rejects_bad_entries(field, value):
    doc = bundled_catalog().document()
    doc["entries"][0][field] = value
    with pytest.raises(ValueError):
        parse_catalog(json.dumps(doc))


@pytest.mark.parametrize(
    "mutation", ["empty", "duplicate", "numeric_duplicate", "source", "future", "extra"]
)
def test_rejects_bad_catalog(mutation):
    doc = bundled_catalog().document()
    if mutation == "empty":
        doc["entries"] = []
    if mutation == "duplicate":
        doc["entries"].append(doc["entries"][0])
    if mutation == "numeric_duplicate":
        doc["entries"][1]["numeric_code"] = doc["entries"][0]["numeric_code"]
    if mutation == "source":
        doc["source_url"] = "https://untrusted.example/list.xml"
    if mutation == "future":
        doc["source_published_on"] = "2999-01-01"
    if mutation == "extra":
        doc["activate_all"] = True
    with pytest.raises(ValueError):
        parse_catalog(json.dumps(doc))


@pytest.mark.parametrize(
    "raw", ['{"x":1,"x":2}', '{"x":NaN}', "[]", "{", " " * (MAX_CATALOG_BYTES + 1)]
)
def test_invalid_json(raw):
    with pytest.raises(ValueError):
        parse_catalog(raw)
    with pytest.raises(Exception, match="Ungültiger Katalog"):
        _catalog(CatalogPreviewRequest.model_construct(catalog_json=raw))


def test_file_size_and_cli_are_fail_closed(tmp_path: Path, capsys):
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(bundled_catalog().document()))
    assert read_catalog(path).checksum == bundled_catalog().checksum
    path.write_bytes(b" " * (MAX_CATALOG_BYTES + 1))
    with pytest.raises(ValueError):
        read_catalog(path)
    with pytest.raises(SystemExit):
        main(["--apply"])
    with pytest.raises(SystemExit):
        main(["--actor-name", " "])
    with patch("app.tools.import_currency_catalog._run", new_callable=AsyncMock) as run:
        assert main([]) == 0
        assert run.call_args.args[0].apply is False
        run.side_effect = ValueError("invalid")
        assert main([]) == 1
        assert "Catalog import failed" in capsys.readouterr().out
