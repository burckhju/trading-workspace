#!/usr/bin/env python3
"""Read one archived P01 binding on the installed v1.5.55 PC, without application writes.

Run outside the managed checkout. The original private diagnostic archive stays
local; only its validated P01 reference enters the backend. This is neither a
mapping/import preview nor a provider/consumer or scheduler acceptance test.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import tempfile
from pathlib import Path

EXPECTED_COMMIT = "eb7f89a30a1772f2c140c5a11cdfb0284d80fc3c"
EXPECTED_VERSION = "1.5.55"
EXPECTED_SCHEMA = ["20261124_0061"]
COLLECTOR_SHA256 = "229c966063ca245f40fe492b14438c4c132fcb5d3fe75458ef20c0efbdd2688e"

# This extension runs inside the existing collector's bounded read-only snapshot.
# It does not invoke that collector's HTTP coverage or full-inventory entry points.
OWNER_EXTENSION = r"""
import asyncio
import json
import logging
from dataclasses import asdict
from uuid import UUID

helpers = {"__name__": "p01_passive_helpers"}
exec(COLLECTOR_PAYLOAD, helpers)
original_read = helpers["read_bound_position"]


def fields(value, names):
    return {name: getattr(value, name) for name in names.split()}


def selected_settings(settings):
    return {
        "scope": "RUNTIME_CONFIGURATION_NOT_SCHEDULER_OR_CACHE_OPERATION_PROOF",
        "gettex": fields(settings.market_data.gettex_delayed,
            "enabled private_use_confirmed timeout_seconds max_download_bytes "
            "fallback_windows unavailable_retry_seconds feed_delay_seconds"),
        "refresh": fields(settings.market_data.refresh,
            "workspace_id enabled warrants_interval_seconds auto_configure "
            "auto_select_position_sources"),
        "monitoring": fields(settings.position_monitoring,
            "enabled review_scope interval_seconds review_notifications_enabled"),
    }


async def add_owner_context(session, target, read_at, row):
    from app.core.config import get_settings
    from app.features.market.persistence.repositories import SqlAlchemyReferenceDataRepository
    from app.features.product.domain.listing_unit_evidence import ListingUnitRoute
    from app.features.product.persistence.listing_unit_evidence import ListingUnitEvidenceRepository
    from app.features.product.service.application import WarrantService
    from app.features.product.service.listing_unit_evidence import ListingUnitEvidenceReader

    binding = target["binding"]
    workspace_id, warrant_id = UUID(binding["workspace_id"]), UUID(binding["warrant_id"])
    owner, market = WarrantService(session), SqlAlchemyReferenceDataRepository(session)
    product = await owner.get(workspace_id, warrant_id)
    terms = await owner.current_terms(workspace_id, warrant_id)
    listings = await owner.listings(workspace_id, warrant_id)
    evidence = ListingUnitEvidenceRepository(session)
    unit_reader = ListingUnitEvidenceReader(session)
    result = {
        "product": fields(product,
            "id workspace_id issuer_id underlying_id isin wkn product_family "
            "lifecycle_status version"),
        "terms": fields(terms,
            "id warrant_id version_no effective_from effective_to option_direction strike "
            "strike_currency_code maturity_date ratio"),
        "listings": [],
        "unit_read_scope": "CURRENT_OWNER_AT_READ_TIME_NOT_V2_QUOTE_EVENT_QUALIFICATION",
    }
    mund_venue = await market.find_trading_venue_by_mic("MUND")
    result["mund_venue"] = (
        fields(mund_venue, "id mic is_active version") if mund_venue is not None else None
    )
    active_mund, active_mund_eur = [], []
    for listing in listings:
        venue = await market.get_trading_venue(listing.trading_venue_id)
        item = fields(listing,
            "id workspace_id warrant_id trading_venue_id symbol quotation_currency_code "
            "lifecycle_status version")
        item["venue"] = fields(venue, "id mic is_active version") if venue is not None else None
        revision = await evidence.latest(workspace_id, warrant_id, listing.id, read_at)
        item["unit_revision"] = (
            fields(revision, "id previous_revision_id revision_number terms_id kid_revision_id "
                "kid_document_sha256 binding recorded_at reviewed_at")
            if revision is not None else None
        )
        if venue is not None and venue.mic == "MUND" and venue.is_active \
                and listing.lifecycle_status.value == "ACTIVE":
            active_mund.append(str(listing.id))
            if listing.quotation_currency_code == "EUR":
                active_mund_eur.append(str(listing.id))
                item["current_unit"] = asdict(await unit_reader.current(
                    workspace_id=workspace_id, warrant_id=warrant_id,
                    route=ListingUnitRoute(listing.id, "GETTEX_DELAYED", "MUND", "EUR"),
                    known_at=read_at, event_at=read_at,
                ))
        result["listings"].append(item)
    settings = get_settings()
    row["owner_context"] = result
    row["settings"] = selected_settings(settings)
    row["readiness"] = {
        "active_product": product.lifecycle_status.value == "ACTIVE",
        "active_mund_listing_ids": active_mund,
        "active_mund_eur_listing_ids": active_mund_eur,
        "exactly_one_active_mund_eur_route": (
            product.lifecycle_status.value == "ACTIVE"
            and len(active_mund) == 1 and len(active_mund_eur) == 1
        ),
        "refresh_workspace_matches": settings.market_data.refresh.workspace_id == workspace_id,
        "mapping_cli_workspace_matches": (
            str(workspace_id) == "00000000-0000-4000-8000-000000000001"
        ),
        "mapping_preview_executed": False,
        "original_import_preview_executed": False,
    }


async def read_owner_position(session, target, read_at):
    row = await original_read(session, target, read_at)
    if row.get("binding_status") == "ARCHIVED_POSITION_AND_PRODUCT_MATCH":
        await add_owner_context(session, target, read_at, row)
    return helpers["private_view"](row)


async def run_read(reference):
    helpers["validate_reference"](reference)
    helpers["require"](
        len(reference["positions"]) == 1
        and reference["positions"][0]["position_label"] == "P01",
        "EXACTLY_ONE_ARCHIVED_P01_REQUIRED",
    )
    helpers["read_bound_position"] = read_owner_position
    result = {"read_only": True, "positions": [], "database_read_complete": False}
    async with asyncio.timeout(120):
        await helpers["read_database"](reference, result)
    return helpers["private_view"](result)


if __name__ == "__main__":
    logging.disable(logging.CRITICAL)
    try:
        result = asyncio.run(run_read(REFERENCE))
    except Exception as error:
        result = {"read_only": True, "database_read_complete": False,
                  **helpers["error_view"](error)}
    print(json.dumps(result, sort_keys=True, allow_nan=False))
"""


class ReadError(RuntimeError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ReadError(code)


def load_helpers(base: Path) -> dict:
    path = base / "trading-workspace-app/scripts/collect-depot-data-supply.py"
    require(path.is_file() and path.resolve(strict=True) == path, "COLLECTOR_PATH_INVALID")
    source = path.read_bytes()
    require(hashlib.sha256(source).hexdigest() == COLLECTOR_SHA256, "COLLECTOR_VERSION_MISMATCH")
    namespace = {"__name__": "p01_host_helpers", "__file__": str(path)}
    exec(compile(source, str(path), "exec"), namespace)
    return namespace


def p01_reference(helpers: dict, archive: Path) -> dict:
    require(archive.is_absolute(), "ABSOLUTE_REFERENCE_ARCHIVE_PATH_REQUIRED")
    reference = helpers["read_source_coverage_reference"](archive)
    targets = [item for item in reference["positions"] if item["position_label"] == "P01"]
    require(len(targets) == 1, "EXACTLY_ONE_ARCHIVED_P01_REQUIRED")
    return {**reference, "positions": targets}


def backend_payload(helpers: dict, reference: dict) -> str:
    return (
        "COLLECTOR_PAYLOAD = " + repr(helpers["SOURCE_COVERAGE_PAYLOAD"]) + "\n"
        "REFERENCE = " + repr(reference) + "\n" + OWNER_EXTENSION
    )


def create_output_dir(helpers: dict, requested: str | None) -> Path:
    if requested:
        path = Path(requested).expanduser()
        require(path.is_absolute(), "ABSOLUTE_OUTPUT_PATH_REQUIRED")
        require(path.parent.resolve(strict=True) == path.parent, "OUTPUT_PARENT_INVALID")
        require(helpers["outside_git"](path), "PRIVATE_OUTPUT_MUST_BE_OUTSIDE_GIT")
        path.mkdir(mode=0o700)
    else:
        home = Path.home().resolve(strict=True)
        require(helpers["outside_git"](home), "PRIVATE_OUTPUT_MUST_BE_OUTSIDE_GIT")
        path = Path(tempfile.mkdtemp(prefix="trading-workspace-p01.", dir=home))
    os.chmod(path, 0o700)
    return path


def collect(helpers: dict, base: Path, reference: dict) -> dict:
    before = helpers["read_installation"](base)
    require(
        before["commit"] == EXPECTED_COMMIT and before["version"] == EXPECTED_VERSION,
        "INSTALLED_RELEASE_MISMATCH",
    )
    require(
        all(
            item["state"] == "running" and item["health"] == "healthy"
            for item in before["containers"].values()
        ),
        "INSTALLED_SERVICES_NOT_HEALTHY",
    )
    backend_id = before["containers"]["backend"]["id"]
    schema = helpers["collect_schema"](backend_id)
    require(
        schema.get("versions") == EXPECTED_SCHEMA and not schema.get("read_error"),
        "INSTALLED_SCHEMA_MISMATCH",
    )
    result = helpers["parse_json"](
        helpers["run_command"](
            [*helpers["docker_prefix"](), "exec", "-i", backend_id, "python", "-B", "-"],
            input_text=backend_payload(helpers, reference),
            timeout=150,
        )
    )
    after = helpers["read_installation"](base)
    complete = (
        before == after
        and result.get("database_read_complete") is True
        and result.get("read_only") is True
        and result.get("transaction") == {"read_only": "on", "isolation": "repeatable read"}
        and len(result.get("positions", [])) == 1
        and result["positions"][0].get("binding_status") == "ARCHIVED_POSITION_AND_PRODUCT_MATCH"
        and result["positions"][0].get("binding") == reference["positions"][0]["binding"]
        and "owner_context" in result["positions"][0]
    )
    return {
        "schema": "PRIVATE_P01_GETTEX_OWNER_BINDING_READ_V1",
        "status": (
            "COMPLETE_P01_OWNER_READ_NOT_PREVIEW_OR_ACCEPTANCE"
            if complete
            else "INCOMPLETE_P01_OWNER_READ"
        ),
        "read_complete": complete,
        "installation_before": before,
        "installation_after": after,
        "installation_unchanged": before == after,
        "schema_versions": schema["versions"],
        "reference": reference,
        "owner_read": result,
    }


def error_code(error: BaseException, helpers: dict | None) -> str:
    known = (ReadError, helpers["DiagnosticError"]) if helpers is not None else (ReadError,)
    code = str(error) if isinstance(error, known) else type(error).__name__
    return code if re.fullmatch(r"[A-Za-z0-9_]{1,100}", code) else "READ_FAILED"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=str(Path.home() / "Boerse"))
    parser.add_argument("--reference-archive", help="Original complete private diagnostic .tar.gz")
    parser.add_argument("--output-dir", help="New private directory outside every Git checkout")
    args = parser.parse_args(argv)
    os.umask(0o077)
    helpers = None
    try:
        base = Path(args.base).expanduser()
        require(base.is_absolute(), "ABSOLUTE_BASE_PATH_REQUIRED")
        helpers = load_helpers(base)
        archive = args.reference_archive
        if not archive:
            require(sys.stdin.isatty(), "REFERENCE_ARCHIVE_ARGUMENT_REQUIRED")
            archive = input(
                "Absoluter Pfad des ursprünglichen privaten Diagnosearchivs (.tar.gz): "
            ).strip()
        reference = p01_reference(helpers, Path(archive).expanduser())
        output_dir = create_output_dir(helpers, args.output_dir)
        output = output_dir / "p01-owner-read-private.json"
        try:
            result = collect(helpers, base, reference)
        except Exception as error:
            result = {
                "status": "INCOMPLETE_P01_OWNER_READ",
                "read_complete": False,
                "read_error": error_code(error, helpers),
            }
        helpers["write_json"](output, result)
        print("Privater P01-Auszug: " + str(output))
        print("Status: " + result["status"])
        return 0 if result["read_complete"] else 2
    except (Exception, KeyboardInterrupt) as error:
        print("P01-Lesefehler: " + error_code(error, helpers), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
