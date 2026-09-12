import json
from pathlib import Path

import pytest

from app.tools.build_currency_catalog import build_catalog, main

XML = b"""<ISO_4217 Pblshd="2026-01-01"><CcyTbl>
<CcyNtry><CcyNm>Yen</CcyNm><Ccy>JPY</Ccy><CcyNbr>392</CcyNbr><CcyMnrUnts>0</CcyMnrUnts></CcyNtry>
<CcyNtry><CcyNm>Pound Sterling</CcyNm><Ccy>GBP</Ccy>
<CcyNbr>826</CcyNbr><CcyMnrUnts>2</CcyMnrUnts></CcyNtry>
</CcyTbl></ISO_4217>"""


def test_builds_exact_subset_without_hardcoded_minor_unit(tmp_path: Path, capsys):
    catalog = build_catalog(XML, codes={"JPY", "GBP"}, version="TEST-V2")
    assert [e.code for e in catalog.entries] == ["GBP", "JPY"]
    assert catalog.entries[1].minor_unit == 0
    path = tmp_path / "source.xml"
    path.write_bytes(XML)
    assert main(["--source", str(path), "--codes", "JPY", "--version", "TEST-V2"]) == 0
    assert json.loads(capsys.readouterr().out)["entries"][0]["code"] == "JPY"
    assert main(["--source", str(path), "--codes", "ZZZ", "--version", "TEST-V2"]) == 1


@pytest.mark.parametrize(
    "raw,codes",
    [
        (XML, {"ZZZ"}),
        (XML, set()),
        (b"<invalid/>", {"JPY"}),
        (b"<!DOCTYPE x>", {"JPY"}),
        (b"<!ENTITY x>", {"JPY"}),
        ("<!DOCTYPE x>".encode("utf-16"), {"JPY"}),
        (b"<\x00invalid/>", {"JPY"}),
        (b" " + b"x" * 1_000_000, {"JPY"}),
        (XML.replace(b"<CcyNm>Yen", b'<CcyNm IsFund="true">Yen'), {"JPY"}),
    ],
)
def test_rejects_nonmatching_or_unsafe_source(raw, codes):
    with pytest.raises(ValueError):
        build_catalog(raw, codes=codes, version="TEST-V2")
