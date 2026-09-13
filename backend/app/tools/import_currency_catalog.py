"""Read-only catalog preview by default; explicit, fingerprint-bound import on request."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Sequence
from contextlib import aclosing
from pathlib import Path

from app.core.config import get_settings
from app.database import DatabaseManager
from app.features.market.service.currency_administration import (
    CurrencyAdministrationService,
)
from app.features.market.service.currency_catalog_contract import (
    MAX_CATALOG_BYTES,
    CurrencyCatalog,
    bundled_catalog,
    parse_catalog,
)
from app.features.market.service.types import Actor


def read_catalog(path: Path | None) -> CurrencyCatalog:
    if path is None:
        return bundled_catalog()
    with path.open("rb") as source:
        raw = source.read(MAX_CATALOG_BYTES + 1)
    if len(raw) > MAX_CATALOG_BYTES:
        raise ValueError("Catalog exceeds 256000 bytes")
    return parse_catalog(raw.decode("utf-8"))


async def _run(args: argparse.Namespace) -> None:
    catalog = read_catalog(args.file)
    database = DatabaseManager(get_settings())
    try:
        async with aclosing(database.session()) as sessions:
            async for session in sessions:
                service = CurrencyAdministrationService(session)
                if args.apply:
                    result = await service.import_catalog(
                        catalog,
                        expected_preview_token=args.expected_preview_token,
                        reviewed=args.reviewed,
                        actor=Actor(id=None, display_name=args.actor_name),
                    )
                else:
                    result = await service.preview(catalog)
                print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        await database.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, help="Reviewed JSON file; defaults to bundled catalog")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Import catalog only, never enable currencies",
    )
    parser.add_argument("--expected-preview-token", help="Token from a previously reviewed preview")
    parser.add_argument(
        "--reviewed",
        action="store_true",
        help="Confirm external source and diff review",
    )
    parser.add_argument("--actor-name", help="Operator name for the audit trail")
    args = parser.parse_args(argv)
    if args.apply and (not args.reviewed or not args.expected_preview_token or not args.actor_name):
        parser.error("--apply requires --reviewed, --expected-preview-token and --actor-name")
    if args.actor_name and (not args.actor_name.strip() or len(args.actor_name) > 200):
        parser.error("--actor-name must be between 1 and 200 non-blank characters")
    try:
        asyncio.run(_run(args))
    except Exception as exc:
        # Do not dump connection URLs or credential-bearing SQL/driver errors.
        print(f"Catalog import failed: {type(exc).__name__}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
