"""Preview local MUND/EUR originals; --apply records only the reviewed Product evidence."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import stat
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO, NoReturn
from uuid import UUID, uuid4

from sqlalchemy import text

from app.core.config import get_settings
from app.core.exceptions import ApplicationError
from app.database import DatabaseManager
from app.features.product.domain.listing_unit_evidence import (
    VERIFICATION,
    ListingUnitImportCommand,
    ListingUnitRoute,
    ListingUnitRuleOriginal,
    ListingUnitRuleRole,
    QualifiedGettexListingSource,
)
from app.features.product.service.application import WarrantService
from app.features.product.service.listing_unit_evidence import (
    MAX_PRETRADE_BYTES,
    MAX_RULE_DOCUMENT_BYTES,
    ListingUnitImportService,
    qualify_gettex_listing_source,
)
from app.features.product.service.listing_unit_sources import ListingUnitSourceError

ACTOR_ID = UUID("00000000-0000-4000-8000-000000000002")
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


class ListingUnitCliError(ValueError):
    """A bounded diagnostic, never a local path or original-document payload."""


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ListingUnitCliError("LISTING_UNIT_ARGUMENTS_INVALID")


def _local_path(value: str) -> Path:
    if value == "-" or _SCHEME.match(value):
        raise argparse.ArgumentTypeError("A regular local original file is required")
    return Path(value)


def _aware_clock(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("An offset-aware review time is required") from error
    if result.utcoffset() is None:
        raise argparse.ArgumentTypeError("An offset-aware review time is required")
    return result


@contextmanager
def open_regular_original(path: Path, *, maximum_bytes: int) -> Iterator[BinaryIO]:
    """Open each path component without following links, then require a bounded file.

    The descriptor stays open through qualification. Replacing a pathname cannot
    change the original being read. The source qualifier checks the full gzip
    and hashes the compressed bytes before and after scanning.
    """
    if path == Path("-") or _SCHEME.match(str(path)):
        raise ListingUnitCliError("LISTING_UNIT_SOURCE_FILE_INVALID")
    parts = path.absolute().parts
    parent: int | None = None
    descriptor: int | None = None
    try:
        parent = os.open(parts[0], os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        for component in parts[1:-1]:
            next_parent = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=parent,
            )
            os.close(parent)
            parent = next_parent
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise ListingUnitCliError("LISTING_UNIT_SOURCE_FILE_INVALID")
        if not 0 < metadata.st_size <= maximum_bytes:
            raise ListingUnitCliError("LISTING_UNIT_SOURCE_SIZE_INVALID")
        with os.fdopen(descriptor, "rb") as source:
            descriptor = None
            yield source
    except OSError as error:
        raise ListingUnitCliError("LISTING_UNIT_SOURCE_FILE_INVALID") from error
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if parent is not None:
            os.close(parent)


def read_rule_original(path: Path, *, role: ListingUnitRuleRole) -> ListingUnitRuleOriginal:
    with open_regular_original(path, maximum_bytes=MAX_RULE_DOCUMENT_BYTES) as source:
        document = source.read(MAX_RULE_DOCUMENT_BYTES + 1)
    if not 0 < len(document) <= MAX_RULE_DOCUMENT_BYTES:
        raise ListingUnitCliError("LISTING_UNIT_SOURCE_SIZE_INVALID")
    if document.startswith(b"%PDF-"):
        media_type = "application/pdf"
    elif role == "PRODUCT_CLASSIFICATION" and document[:128].lstrip().lower().startswith(
        (b"<!doctype html", b"<html")
    ):
        media_type = "text/html"
    else:
        raise ListingUnitCliError("LISTING_UNIT_RULE_FILE_FORMAT_INVALID")
    # Reading a local file is not evidence of its original download time.
    return ListingUnitRuleOriginal(role, path.name, media_type, document)


def _validate_arguments(args: argparse.Namespace) -> None:
    if args.apply and (
        args.request_id is None
        or not re.fullmatch(r"[0-9a-f]{64}", args.expected_preview_fingerprint or "")
    ):
        raise ListingUnitCliError("LISTING_UNIT_APPLY_CONFIRMATION_REQUIRED")
    if not args.apply and args.expected_preview_fingerprint is not None:
        raise ListingUnitCliError("LISTING_UNIT_APPLY_ARGUMENTS_INVALID")
    if not 3 <= len(args.review_reference.strip()) <= 1000 or "\x00" in args.review_reference:
        raise ListingUnitCliError("LISTING_UNIT_REVIEW_REFERENCE_INVALID")


def _summary(
    source: QualifiedGettexListingSource,
    command: ListingUnitImportCommand,
) -> dict[str, Any]:
    # No product identifiers, quote values, original bytes or local filenames
    # are needed to carry the reviewed fingerprint into the explicit command.
    return {
        "source_fingerprint": source.fingerprint,
        "request_id": str(command.request_id),
        "reviewed_at": command.reviewed_at.isoformat(),
        "rule_set_version": source.rule_set_version,
        "provider": "GETTEX_DELAYED",
        "venue_mic": "MUND",
        "currency": "EUR",
        "unit_to_import": "CURRENCY_PER_WARRANT",
        "verification": VERIFICATION,
    }


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    _validate_arguments(args)
    rules = (
        read_rule_original(args.exchange_rules_file, role="EXCHANGE_RULES"),
        read_rule_original(args.open_market_rules_file, role="OPEN_MARKET_RULES"),
        read_rule_original(args.execution_rules_file, role="EXECUTION_RULES"),
        read_rule_original(args.product_classification_file, role="PRODUCT_CLASSIFICATION"),
    )
    command = ListingUnitImportCommand(
        request_id=args.request_id or uuid4(),
        expected_revision_id=args.previous_revision_id,
        route=ListingUnitRoute(args.listing_id, "GETTEX_DELAYED", "MUND", "EUR"),
        kid_revision_id=args.kid_revision_id,
        reviewed_at=args.reviewed_at,
        review_reference=args.review_reference,
    )
    with open_regular_original(args.pretrade_file, maximum_bytes=MAX_PRETRADE_BYTES) as original:
        settings = get_settings().model_copy(update={"database_echo": False})
        workspace_id = settings.market_data.refresh.workspace_id
        database = DatabaseManager(settings)
        try:
            async with database.session_context() as session:
                try:
                    session.autoflush = False
                    await session.execute(
                        text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                    )
                    await session.execute(text("SET LOCAL statement_timeout = '10000ms'"))
                    warrant = await WarrantService(session).get(workspace_id, args.warrant_id)
                    if warrant.isin is None:
                        raise ListingUnitCliError("LISTING_UNIT_PRODUCT_IDENTITY_MISSING")
                    clock = datetime.now(UTC)
                    source = qualify_gettex_listing_source(
                        source=original,
                        file_name=args.pretrade_file.name,
                        target_isin=warrant.isin,
                        rules=rules,
                        known_at=clock,
                    )
                    if not args.apply:
                        preview = await ListingUnitImportService(session).preview(
                            workspace_id=workspace_id,
                            warrant_id=args.warrant_id,
                            command=command,
                            source=source,
                            now=clock,
                        )
                        return {
                            **_summary(source, command),
                            "outcome": "READY_TO_IMPORT",
                            "operation_status": preview.operation_status,
                            "preview_fingerprint": preview.fingerprint,
                            "next_revision_number": preview.next_revision_number,
                        }
                finally:
                    await session.rollback()
            # The Product owner controls its write transaction, rechecks the
            # preview under lock and commits only the new evidence revision.
            # It also recognizes an already committed request before checking
            # its original predecessor, so a safe retry can reach that replay.
            async with database.session_context() as session:
                try:
                    revision = await ListingUnitImportService(session).record(
                        workspace_id=workspace_id,
                        warrant_id=args.warrant_id,
                        actor_id=ACTOR_ID,
                        command=command,
                        source=source,
                        expected_preview_fingerprint=args.expected_preview_fingerprint,
                    )
                    return {
                        **_summary(source, command),
                        "outcome": "IMPORTED_OR_REUSED",
                        "operation_status": "PRODUCT_EVIDENCE_IMPORT_ONLY",
                        "expected_preview_fingerprint": args.expected_preview_fingerprint,
                        "revision_number": revision.revision_number,
                    }
                finally:
                    await session.rollback()
        finally:
            await database.dispose()


def _failure_code(error: Exception) -> str:
    if isinstance(error, (ApplicationError, ListingUnitSourceError)):
        code = error.code
    elif isinstance(error, ListingUnitCliError):
        code = str(error)
    else:
        code = ""
    return (
        code
        if re.fullmatch(
            r"(?:LISTING_UNIT|GETTEX|PRODUCT_(?:REVIEW|DOCUMENT|PRICE_SCALE))_[A-Z_]{3,96}",
            code,
        )
        else "LISTING_UNIT_IMPORT_FAILED"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _ArgumentParser(description=__doc__)
    for name in ("warrant-id", "listing-id", "kid-revision-id"):
        parser.add_argument(f"--{name}", type=UUID, required=True)
    parser.add_argument("--previous-revision-id", type=UUID)
    for name in (
        "exchange-rules-file",
        "open-market-rules-file",
        "execution-rules-file",
        "product-classification-file",
        "pretrade-file",
    ):
        parser.add_argument(f"--{name}", type=_local_path, required=True)
    parser.add_argument("--reviewed-at", type=_aware_clock, required=True)
    parser.add_argument("--review-reference", required=True)
    parser.add_argument("--request-id", type=UUID)
    parser.add_argument("--expected-preview-fingerprint")
    parser.add_argument("--apply", action="store_true", help="Record the exact reviewed preview")
    try:
        args = parser.parse_args(argv)
        _validate_arguments(args)
        result = asyncio.run(_run(args))
    except Exception as error:
        print(json.dumps({"outcome": "FAILED", "problem": _failure_code(error)}))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
