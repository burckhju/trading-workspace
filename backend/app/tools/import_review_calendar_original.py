"""Preview an existing local XSTU 2026 original; --apply imports only that evidence."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import stat
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.core.config import get_settings
from app.database import DatabaseManager
from app.features.market_data.service.review_calendars import (
    MAX_BYTES,
    import_xstu_day_calendar_original,
)


def read_original(path: Path) -> bytes:
    """Read bounded local bytes, never URLs, symlinks or special files."""
    if path == Path("-"):
        document = sys.stdin.buffer.read(MAX_BYTES + 1)
    else:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise ValueError("REVIEW_CALENDAR_SOURCE_FILE_INVALID")
            document = source.read(MAX_BYTES + 1)
    if not 0 < len(document) <= MAX_BYTES:
        raise ValueError("REVIEW_CALENDAR_SOURCE_SIZE_INVALID")
    return document


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    document = read_original(args.file)
    # Keep SQL parameters and local original bytes out of terminal output even
    # when the application's saved development configuration enables SQL echo.
    settings = get_settings().model_copy(update={"database_echo": False})
    database = DatabaseManager(settings)
    try:
        async with database.session_context() as session:
            try:
                mode = "READ COMMITTED" if args.apply else "REPEATABLE READ READ ONLY"
                await session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {mode}"))
                await session.execute(text("SET LOCAL statement_timeout = '10000ms'"))
                result = await import_xstu_day_calendar_original(
                    session,
                    workspace_id=settings.market_data.refresh.workspace_id,
                    document=document,
                    now=datetime.now(UTC),
                    apply=args.apply,
                )
                if args.apply:
                    await session.commit()
                return result
            finally:
                await session.rollback()
    finally:
        await database.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file", type=Path, required=True, help="Local original PDF, or - for stdin"
    )
    parser.add_argument("--apply", action="store_true", help="Import the exact reviewed original")
    args = parser.parse_args(argv)
    try:
        result = asyncio.run(_run(args))
    except Exception as error:
        value = str(error) if isinstance(error, ValueError) else ""
        code = (
            value
            if re.fullmatch(r"REVIEW_CALENDAR_[A-Z0-9_]{3,80}", value)
            else "REVIEW_CALENDAR_IMPORT_FAILED"
        )
        print(json.dumps({"outcome": "FAILED", "problem": code}))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
