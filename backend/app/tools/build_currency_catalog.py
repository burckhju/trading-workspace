"""Build an operator-selected monetary subset from a local SIX List One XML file.

No network or database access. The operator verifies the source before import.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from pathlib import Path

from app.features.market.service.currency_catalog_contract import (
    SOURCE_URL,
    CatalogEntry,
    CurrencyCatalog,
)


def build_catalog(raw: bytes, *, codes: set[str], version: str) -> CurrencyCatalog:
    if not raw or len(raw) > 1_000_000 or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("Invalid or oversized XML; DTD/entities are not supported")
    # Refuse alternate encodings that could hide DTD/entity declarations.
    decoded = raw.decode("utf-8-sig")
    if "\x00" in decoded:
        raise ValueError("Only UTF-8 XML is supported")
    root = ET.fromstring(decoded)
    if root.tag != "ISO_4217" or not codes:
        raise ValueError("Expected SIX ISO_4217 XML and explicit monetary codes")
    entries: dict[str, CatalogEntry] = {}
    for row in root.findall("CcyTbl/CcyNtry"):
        code = row.findtext("Ccy")
        if code not in codes:
            continue
        name = row.find("CcyNm")
        if name is None or name.get("IsFund", "false").lower() == "true":
            raise ValueError("Fund codes are not supported")
        entry = CatalogEntry(
            code=code,
            name=(name.text or "").strip(),
            numeric_code=row.findtext("CcyNbr") or "",
            minor_unit=int(row.findtext("CcyMnrUnts") or ""),
            kind="CURRENCY",
        )
        if code in entries and entries[code] != entry:
            raise ValueError("Conflicting entity rows for the same code")
        entries[code] = entry
    if entries.keys() != codes:
        raise ValueError("One or more requested codes are missing from the current source")
    return CurrencyCatalog.model_validate(
        {
            "schema_version": 1,
            "version": version,
            "source_url": SOURCE_URL,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "source_published_on": root.get("Pblshd"),
            "scope": (
                "Operator-selected monetary subset from SIX List One; "
                "not a complete ISO catalog."
            ),
            "entries": [entries[code].model_dump() for code in sorted(entries)],
        }
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument(
        "--codes",
        nargs="+",
        required=True,
        help="Full desired subset, not just additions",
    )
    parser.add_argument("--version", required=True, help="New unique catalog version")
    args = parser.parse_args(argv)
    try:
        with args.source.open("rb") as source:
            raw = source.read(1_000_001)
        catalog = build_catalog(raw, codes=set(args.codes), version=args.version)
    except (OSError, ValueError, ET.ParseError) as exc:
        print(f"Catalog build failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(json.dumps(catalog.document(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
