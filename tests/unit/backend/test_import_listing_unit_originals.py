"""Local synthetic originals and controlled owner sessions; no provider or PC access."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.core.config import Settings
from app.core.exceptions import ApplicationError
from app.features.product.domain.listing_unit_evidence import (
    ListingUnitRuleDocumentSpec,
    ListingUnitRuleSet,
)
from app.features.product.service import listing_unit_sources
from app.tools import import_listing_unit_originals as cli

NOW = datetime(2026, 11, 24, 19, tzinfo=UTC)
WORKSPACE = UUID("00000000-0000-4000-8000-000000000101")
WARRANT = UUID("00000000-0000-4000-8000-000000000102")
LISTING = UUID("00000000-0000-4000-8000-000000000103")
KID_REVISION = UUID("00000000-0000-4000-8000-000000000104")
REQUEST = UUID("00000000-0000-4000-8000-000000000105")
ISIN = "DE000ABC1234"
PREVIEW = "a" * 64


@pytest.fixture
def package(tmp_path):
    files = {}
    for name in (
        "exchange_rules_file",
        "open_market_rules_file",
        "execution_rules_file",
        "product_classification_file",
    ):
        path = tmp_path / f"{name}.pdf"
        path.write_bytes(b"%PDF-1.4\nsynthetic-test-only-" + name.encode())
        files[name] = path
    pretrade = tmp_path / "pretrade.20261124.17.15.mund.csv.gz"
    pretrade.write_bytes(gzip.compress(f"{ISIN},17:01:00.000000,EUR,1.2,5,1.3,6\n".encode()))
    return argparse.Namespace(
        **files,
        pretrade_file=pretrade,
        warrant_id=WARRANT,
        listing_id=LISTING,
        kid_revision_id=KID_REVISION,
        previous_revision_id=None,
        reviewed_at=NOW - timedelta(minutes=1),
        review_reference="synthetic-local-original-review",
        request_id=REQUEST,
        expected_preview_fingerprint=None,
        apply=False,
    )


def arguments(args):
    result = []
    for name in (
        "warrant_id",
        "listing_id",
        "kid_revision_id",
        "exchange_rules_file",
        "open_market_rules_file",
        "execution_rules_file",
        "product_classification_file",
        "pretrade_file",
        "review_reference",
    ):
        result.extend(("--" + name.replace("_", "-"), str(getattr(args, name))))
    result.extend(("--reviewed-at", args.reviewed_at.isoformat()))
    if args.request_id is not None:
        result.extend(("--request-id", str(args.request_id)))
    if args.expected_preview_fingerprint is not None:
        result.extend(("--expected-preview-fingerprint", args.expected_preview_fingerprint))
    if args.apply:
        result.append("--apply")
    return result


@pytest.fixture
def controlled_owner(monkeypatch):
    events = []
    sessions = []
    commands = []
    sources = []
    failures = SimpleNamespace(record=None, preview=None)
    settings = Settings.model_construct(database_echo=True)
    settings.market_data.refresh.workspace_id = WORKSPACE

    class Session:
        def __init__(self):
            self.index = len(sessions)
            self.statements = []
            self.autoflush = True
            self.commit = AsyncMock(side_effect=AssertionError("CLI must not commit"))
            self.flush = AsyncMock(side_effect=AssertionError("CLI must not flush"))
            sessions.append(self)

        async def execute(self, statement):
            self.statements.append(str(statement))
            events.append(("sql", self.index))

        async def rollback(self):
            events.append(("rollback", self.index))

    @asynccontextmanager
    async def session_context():
        session = Session()
        events.append(("enter", session.index))
        try:
            yield session
        finally:
            events.append(("exit", session.index))

    database = SimpleNamespace(session_context=session_context, dispose=AsyncMock())

    def database_manager(actual_settings):
        assert actual_settings is not settings and actual_settings.database_echo is False
        return database

    class WarrantReader:
        def __init__(self, session):
            self.session = session

        async def get(self, workspace_id, warrant_id):
            assert (workspace_id, warrant_id) == (WORKSPACE, WARRANT)
            assert self.session.autoflush is False
            assert self.session.statements[0] == (
                "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
            )
            events.append(("identity", self.session.index))
            return SimpleNamespace(isin=ISIN)

    class Owner:
        def __init__(self, session):
            self.session = session

        async def preview(self, *, workspace_id, warrant_id, command, source, now):
            if failures.preview is not None:
                raise failures.preview
            assert (workspace_id, warrant_id, now) == (WORKSPACE, WARRANT, NOW)
            assert command.route.provider == "GETTEX_DELAYED"
            assert command.route.venue_mic == "MUND"
            assert command.route.currency == "EUR"
            assert command.route.listing_id == LISTING
            assert command.kid_revision_id == KID_REVISION
            commands.append(command)
            events.append(("preview", self.session.index))
            return SimpleNamespace(
                fingerprint=PREVIEW,
                source_fingerprint=source.fingerprint,
                next_revision_number=1,
                operation_status="READ_ONLY_PREVIEW",
            )

        async def record(
            self,
            *,
            workspace_id,
            warrant_id,
            actor_id,
            command,
            source,
            expected_preview_fingerprint,
        ):
            assert (workspace_id, warrant_id, actor_id) == (
                WORKSPACE,
                WARRANT,
                cli.ACTOR_ID,
            )
            assert source is sources[-1]
            assert ("exit", self.session.index - 1) in events
            assert self.session.statements == []
            events.append(("record", self.session.index))
            commands.append(command)
            if expected_preview_fingerprint != PREVIEW:
                raise ApplicationError(
                    code="LISTING_UNIT_PREVIEW_CHANGED",
                    message="synthetic",
                    status_code=409,
                )
            if failures.record is not None:
                raise failures.record
            return SimpleNamespace(revision_number=1)

    def qualify(**kwargs):
        assert "registry" not in kwargs and kwargs["target_isin"] == ISIN
        assert kwargs["source"].seekable() and not kwargs["source"].closed
        rules = kwargs["rules"]
        registry = (
            ListingUnitRuleSet(
                "synthetic-test-only",
                NOW - timedelta(days=1),
                tuple(
                    ListingUnitRuleDocumentSpec(
                        item.role,
                        f"https://example.invalid/synthetic/{item.role}",
                        hashlib.sha256(item.document).hexdigest(),
                        item.media_type,
                    )
                    for item in rules
                ),
            ),
        )
        events.append(("qualify", sessions[-1].index))
        source = listing_unit_sources.qualify_gettex_listing_source(**kwargs, registry=registry)
        sources.append(source)
        return source

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW

    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    monkeypatch.setattr(cli, "DatabaseManager", database_manager)
    monkeypatch.setattr(cli, "WarrantService", WarrantReader)
    monkeypatch.setattr(cli, "ListingUnitImportService", Owner)
    monkeypatch.setattr(cli, "qualify_gettex_listing_source", qualify)
    monkeypatch.setattr(cli, "datetime", Clock)
    return SimpleNamespace(
        events=events,
        sessions=sessions,
        sources=sources,
        commands=commands,
        failures=failures,
        database=database,
        settings=settings,
    )


async def test_preview_uses_real_read_only_transaction_and_complete_original_qualifier(
    package, controlled_owner
):
    result = await cli._run(package)
    assert result["operation_status"] == "READ_ONLY_PREVIEW"
    assert result["preview_fingerprint"] == PREVIEW
    assert len(controlled_owner.sessions) == 1
    assert ("record", 1) not in controlled_owner.events
    assert controlled_owner.events[-2:] == [("rollback", 0), ("exit", 0)]
    source = controlled_owner.sources[0]
    assert (
        source.pretrade.file_sha256
        == hashlib.sha256(package.pretrade_file.read_bytes()).hexdigest()
    )
    assert source.pretrade.file_bytes == package.pretrade_file.stat().st_size
    assert source.pretrade.retrieved_at is None
    assert all(original.retrieved_at is None for original in source.rule_originals)
    controlled_owner.database.dispose.assert_awaited_once()
    assert controlled_owner.settings.database_echo is True


async def test_apply_closes_read_only_snapshot_before_owner_write_and_does_not_commit_itself(
    package, controlled_owner
):
    package.apply = True
    package.expected_preview_fingerprint = PREVIEW
    package.previous_revision_id = UUID("00000000-0000-4000-8000-000000000106")
    result = await cli._run(package)
    assert result["outcome"] == "IMPORTED_OR_REUSED"
    assert len(controlled_owner.sessions) == 2
    assert controlled_owner.events.index(("exit", 0)) < controlled_owner.events.index(("record", 1))
    assert controlled_owner.commands[0].expected_revision_id == package.previous_revision_id
    assert controlled_owner.commands[0].reviewed_at == package.reviewed_at
    for session in controlled_owner.sessions:
        session.commit.assert_not_awaited()
        session.flush.assert_not_awaited()
    controlled_owner.database.dispose.assert_awaited_once()


async def test_changed_preview_is_rejected_by_owner_without_a_cli_commit(package, controlled_owner):
    package.apply = True
    package.expected_preview_fingerprint = "b" * 64
    with pytest.raises(ApplicationError) as caught:
        await cli._run(package)
    assert caught.value.code == "LISTING_UNIT_PREVIEW_CHANGED"
    assert len(controlled_owner.sessions) == 2
    assert controlled_owner.events[-2:] == [("rollback", 1), ("exit", 1)]
    controlled_owner.sessions[1].commit.assert_not_awaited()
    controlled_owner.database.dispose.assert_awaited_once()


async def test_apply_replay_reaches_owner_without_a_conflicting_predecessor_preview(
    package, controlled_owner
):
    package.apply = True
    package.expected_preview_fingerprint = PREVIEW
    first = await cli._run(package)
    controlled_owner.failures.preview = ApplicationError(
        code="LISTING_UNIT_REVISION_CONFLICT",
        message="head now exists",
        status_code=409,
    )
    repeated = await cli._run(package)
    assert first == repeated
    assert controlled_owner.commands[0] == controlled_owner.commands[1]
    assert [event for event in controlled_owner.events if event[0] == "record"] == [
        ("record", 1),
        ("record", 3),
    ]
    assert not any(event[0] == "preview" for event in controlled_owner.events)


async def test_owner_rejection_after_preflight_is_rolled_back_and_never_reported_as_import(
    package, controlled_owner
):
    package.apply = True
    package.expected_preview_fingerprint = PREVIEW
    controlled_owner.failures.record = ApplicationError(
        code="LISTING_UNIT_PREVIEW_MISMATCH",
        message="synthetic private details",
        status_code=409,
    )
    with pytest.raises(ApplicationError):
        await cli._run(package)
    assert controlled_owner.events[-2:] == [("rollback", 1), ("exit", 1)]
    controlled_owner.database.dispose.assert_awaited_once()


async def test_corruption_after_valid_target_still_blocks_the_full_gzip_import(
    package, controlled_owner
):
    later_member = bytearray(gzip.compress(b"DE000DEF5678,17:02:00.000000,EUR,2,5,3,6\n"))
    later_member[-8] ^= 1
    package.pretrade_file.write_bytes(package.pretrade_file.read_bytes() + later_member)
    package.apply = True
    package.expected_preview_fingerprint = PREVIEW
    with pytest.raises(listing_unit_sources.ListingUnitSourceError, match="PRETRADE_INVALID"):
        await cli._run(package)
    assert len(controlled_owner.sessions) == 1
    assert controlled_owner.sources == []
    assert not any(event[0] in {"preview", "record"} for event in controlled_owner.events)


async def test_unqualified_production_registry_stays_blocked_without_caller_override(
    package, controlled_owner, monkeypatch
):
    monkeypatch.setattr(
        cli,
        "qualify_gettex_listing_source",
        listing_unit_sources.qualify_gettex_listing_source,
    )
    with pytest.raises(listing_unit_sources.ListingUnitSourceError, match="ORIGINALS_UNQUALIFIED"):
        await cli._run(package)
    assert controlled_owner.sources == []
    assert len(controlled_owner.sessions) == 1


@pytest.mark.parametrize("kind", ["file_link", "parent_link", "fifo", "directory"])
def test_symlink_components_and_special_files_are_rejected_without_following(tmp_path, kind):
    directory = tmp_path / "originals"
    directory.mkdir()
    original = directory / "source.pdf"
    original.write_bytes(b"%PDF-1.4\nsynthetic")
    path = tmp_path / "candidate"
    if kind == "file_link":
        path.symlink_to(original)
    elif kind == "parent_link":
        path.symlink_to(directory, target_is_directory=True)
        path = path / "source.pdf"
    elif kind == "fifo":
        os.mkfifo(path)
    else:
        path.mkdir()
    with pytest.raises(cli.ListingUnitCliError, match="SOURCE_FILE_INVALID"):
        cli.read_rule_original(path, role="EXCHANGE_RULES")


@pytest.mark.parametrize(
    "value", ["-", "https://example.invalid/original.pdf", "file:/private.pdf"]
)
def test_stdin_and_urls_are_not_local_original_sources(value):
    with pytest.raises(cli.ListingUnitCliError, match="SOURCE_FILE_INVALID"):
        cli.read_rule_original(Path(value), role="EXCHANGE_RULES")


@pytest.mark.parametrize("content", [b"", b"%PDF-" + b"x" * 32])
def test_original_size_is_bounded_before_reading(tmp_path, monkeypatch, content):
    path = tmp_path / "size.pdf"
    path.write_bytes(content)
    monkeypatch.setattr(cli, "MAX_RULE_DOCUMENT_BYTES", 32)
    with pytest.raises(cli.ListingUnitCliError, match="SOURCE_SIZE_INVALID"):
        cli.read_rule_original(path, role="EXCHANGE_RULES")


def test_new_rule_bound_accepts_bsw_sized_original_and_preserves_bytes(tmp_path):
    path = tmp_path / "synthetic-classification.pdf"
    content = b"%PDF-1.4\n" + b"x" * 2_835_850
    path.write_bytes(content)
    result = cli.read_rule_original(path, role="PRODUCT_CLASSIFICATION")
    assert result.document == content and result.media_type == "application/pdf"
    assert result.retrieved_at is None


def test_only_classification_role_accepts_original_html(tmp_path):
    path = tmp_path / "classification.html"
    content = b"<!doctype html><html><body>synthetic classification</body></html>"
    path.write_bytes(content)
    result = cli.read_rule_original(path, role="PRODUCT_CLASSIFICATION")
    assert result.document == content and result.media_type == "text/html"
    with pytest.raises(cli.ListingUnitCliError, match="RULE_FILE_FORMAT_INVALID"):
        cli.read_rule_original(path, role="EXCHANGE_RULES")


@pytest.mark.parametrize("missing", ["request_id", "expected_preview_fingerprint"])
def test_apply_requires_both_review_fingerprint_and_explicit_request_before_io(
    package, monkeypatch, capsys, missing
):
    package.apply = True
    package.expected_preview_fingerprint = PREVIEW
    setattr(package, missing, None)
    run = AsyncMock()
    monkeypatch.setattr(cli, "_run", run)
    assert cli.main(arguments(package)) == 1
    run.assert_not_awaited()
    assert json.loads(capsys.readouterr().out) == {
        "outcome": "FAILED",
        "problem": "LISTING_UNIT_APPLY_CONFIRMATION_REQUIRED",
    }


def test_argument_error_does_not_echo_private_input_or_accept_pin_registration(
    package, monkeypatch, capsys
):
    run = AsyncMock()
    monkeypatch.setattr(cli, "_run", run)
    private = "postgresql://private-user:private-password@private-host"
    args = arguments(package)
    args[args.index("--warrant-id") + 1] = private
    assert cli.main(args) == 1
    output = capsys.readouterr()
    assert private not in output.out + output.err
    assert json.loads(output.out)["problem"] == "LISTING_UNIT_ARGUMENTS_INVALID"
    assert cli.main([*arguments(package), "--register-pin", private]) == 1
    assert private not in capsys.readouterr().out
    run.assert_not_awaited()


def test_default_main_preview_prints_no_product_ids_prices_or_original_data(
    package, controlled_owner, capsys
):
    assert cli.main(arguments(package)) == 0
    output = capsys.readouterr().out
    result = json.loads(output)
    assert result["operation_status"] == "READ_ONLY_PREVIEW"
    assert result["request_id"] == str(REQUEST)
    for private in (
        ISIN,
        str(WARRANT),
        str(LISTING),
        str(KID_REVISION),
        "17:01:00",
        "%PDF-",
    ):
        assert private not in output


@pytest.mark.parametrize(
    "error,expected",
    [
        (
            RuntimeError("postgresql://secret:password@private-host"),
            "LISTING_UNIT_IMPORT_FAILED",
        ),
        (ValueError("LISTING_UNIT_PRIVATE_VALUE"), "LISTING_UNIT_IMPORT_FAILED"),
        (
            ApplicationError(
                code="LISTING_UNIT_DE000ABC1234",
                message="private payload",
                status_code=422,
            ),
            "LISTING_UNIT_IMPORT_FAILED",
        ),
        (
            listing_unit_sources.ListingUnitSourceError("LISTING_UNIT_RULE_ORIGINALS_UNQUALIFIED"),
            "LISTING_UNIT_RULE_ORIGINALS_UNQUALIFIED",
        ),
        (
            ApplicationError(
                code="PRODUCT_DOCUMENT_UNDERLYING_MISMATCH",
                message="private original identity details",
                status_code=422,
            ),
            "PRODUCT_DOCUMENT_UNDERLYING_MISMATCH",
        ),
    ],
)
def test_failure_output_contains_only_bounded_owner_codes(
    package, monkeypatch, capsys, error, expected
):
    monkeypatch.setattr(cli, "_run", AsyncMock(side_effect=error))
    assert cli.main(arguments(package)) == 1
    assert json.loads(capsys.readouterr().out) == {
        "outcome": "FAILED",
        "problem": expected,
    }
