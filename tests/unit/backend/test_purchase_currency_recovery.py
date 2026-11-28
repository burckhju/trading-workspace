"""Private-plan validation, stable retry identity and sanitized maintenance CLI."""

import asyncio
import io
import json
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.tools import recover_purchase_currency as recovery


def _payload() -> dict:
    return {
        "schema_version": "purchase-currency-recovery-v1",
        "workspace_id": "10000000-0000-4000-8000-000000000001",
        "actor_id": "10000000-0000-4000-8000-000000000002",
        "currency": "EUR",
        "expected_basis": "a" * 64,
        "inventory_sha256": "b" * 64,
        "note": "Synthetic current declaration for the bounded legacy inventory",
        "filters": {
            "from_date": "2026-10-01",
            "to_date": "2026-11-08",
            "report_currency": "EUR",
            "report_timezone": "Europe/Berlin",
        },
        "targets": [
            {
                "execution_id": "20000000-0000-4000-8000-000000000001",
                "trade_id": "30000000-0000-4000-8000-000000000001",
                "product_id": "40000000-0000-4000-8000-000000000001",
            },
            {
                "execution_id": "20000000-0000-4000-8000-000000000002",
                "trade_id": "30000000-0000-4000-8000-000000000001",
                "product_id": "40000000-0000-4000-8000-000000000001",
            },
        ],
        "expected_counts": {
            "examined": 1,
            "in_period": 1,
            "outside_period": 0,
            "period_ambiguous": 0,
            "period_unknown": 0,
            "candidates": 1,
            "usable": 1,
            "unresolved": 0,
            "excluded": 0,
            "cancelled": 0,
        },
        "expected_summary_status": "COMPLETE",
    }


def _plan(payload: dict | None = None) -> recovery.PurchaseCurrencyRecoveryPlan:
    return recovery.PurchaseCurrencyRecoveryPlan.model_validate_json(
        json.dumps(payload if payload is not None else _payload())
    )


def _stdin(monkeypatch: pytest.MonkeyPatch, payload: bytes, mode: str = "preview") -> None:
    monkeypatch.setattr(recovery.sys, "argv", ["recovery", mode, "--plan", "-"])
    monkeypatch.setattr(recovery.sys, "stdin", io.TextIOWrapper(io.BytesIO(payload)))


def test_plan_round_trip_and_target_order_preserve_retry_identity() -> None:
    plan = _plan()
    reordered = _plan(_payload() | {"targets": list(reversed(_payload()["targets"]))})
    assert _plan(json.loads(plan.model_dump_json())) == plan
    assert recovery.plan_fingerprint(plan) == recovery.plan_fingerprint(reordered)
    requests = {recovery.recovery_request_id(plan, target) for target in plan.targets}
    assert len(requests) == 2
    assert all(isinstance(request_id, UUID) for request_id in requests)
    # Preserve the existing v1 identity for already approved private plans.
    assert recovery.plan_fingerprint(plan) == (
        "98e8dcf8102c9b0052be8f84e643669a4cd370086301f8bbf83140ef66d8b832"
    )
    assert requests == {
        UUID("eabf7e46-7f4e-5848-9474-ebde9d149aa7"),
        UUID("c20c8184-dbd8-52cf-b694-0cca5d92c653"),
    }
    assert requests == {
        recovery.recovery_request_id(reordered, target) for target in reordered.targets
    }


@pytest.mark.parametrize("change", ["actor", "note", "inventory", "basis", "postcondition"])
def test_retry_identity_binds_scope_declaration_and_required_outcome(change: str) -> None:
    original = _plan()
    payload = _payload()
    if change == "actor":
        payload["actor_id"] = "10000000-0000-4000-8000-000000000099"
    elif change == "note":
        payload["note"] = "A different synthetic declaration"
    elif change == "inventory":
        payload["inventory_sha256"] = "c" * 64
    elif change == "basis":
        payload["expected_basis"] = "d" * 64
    else:
        payload["expected_counts"]["cancelled"] = 1
    changed = _plan(payload)
    assert recovery.plan_fingerprint(original) != recovery.plan_fingerprint(changed)
    assert recovery.recovery_request_id(original, original.targets[0]) != (
        recovery.recovery_request_id(changed, changed.targets[0])
    )


@pytest.mark.parametrize(
    "change",
    ["duplicate", "product", "currency", "date", "bool_count", "extra", "empty", "note"],
)
def test_private_plan_rejects_ambiguous_or_ill_typed_scope(change: str) -> None:
    payload = _payload()
    if change == "duplicate":
        payload["targets"][1] = payload["targets"][0]
    elif change == "product":
        payload["targets"][1]["product_id"] = "40000000-0000-4000-8000-000000000099"
    elif change == "currency":
        payload["currency"] = "USD"
    elif change == "date":
        payload["filters"]["from_date"] = "2027-01-01"
    elif change == "bool_count":
        payload["expected_counts"]["usable"] = True
    elif change == "extra":
        payload["assume_unknown_currency"] = True
    elif change == "empty":
        payload["targets"] = []
    else:
        payload["note"] = "  Untrimmed declaration  "
    with pytest.raises((ValidationError, ValueError)):
        _plan(payload)


def test_unknown_mode_cannot_fall_through_to_a_write(monkeypatch: pytest.MonkeyPatch) -> None:
    database = Mock(side_effect=AssertionError("Database must not be constructed"))
    monkeypatch.setattr(recovery, "DatabaseManager", database)
    with pytest.raises(recovery.RecoveryError, match="INVALID_MODE"):
        asyncio.run(recovery.run("not-a-mode", _plan()))
    database.assert_not_called()


def test_cli_validation_failure_does_not_echo_private_plan(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    payload = _payload() | {"private_invalid_field": "NEVER_ECHO_PRIVATE_INPUT"}
    _stdin(monkeypatch, json.dumps(payload).encode())
    assert recovery.main() == 1
    output = capsys.readouterr()
    assert json.loads(output.out)["code"] == "INVALID_PLAN"
    assert "NEVER_ECHO_PRIVATE_INPUT" not in output.out + output.err


@pytest.mark.parametrize(
    "arguments",
    [
        ["NEVER_ECHO_PRIVATE_MODE"],
        ["preview", "--unknown", "NEVER_ECHO_PRIVATE_ARGUMENT"],
        ["preview", "NEVER_ECHO_PRIVATE_PLAN_PATH"],
        ["preview", "--plan"],
    ],
)
def test_cli_argument_errors_are_private_before_reading_or_running(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, arguments: list[str]
) -> None:
    monkeypatch.setattr(recovery.sys, "argv", ["NEVER_ECHO_PRIVATE_PROGRAM_PATH", *arguments])
    open_plan = Mock(side_effect=AssertionError("An invalid command must not read a plan"))
    run = AsyncMock(side_effect=AssertionError("An invalid command must not run"))
    monkeypatch.setattr(recovery.Path, "open", open_plan)
    monkeypatch.setattr(recovery, "run", run)
    with pytest.raises(SystemExit) as stopped:
        recovery.main()
    assert stopped.value.code == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert json.loads(output.err)["code"] == "INVALID_ARGUMENTS"
    assert "NEVER_ECHO" not in output.out + output.err
    open_plan.assert_not_called()
    run.assert_not_awaited()


def test_cli_help_remains_available_without_reading_or_running(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.setattr(recovery.sys, "argv", ["recovery", "--help"])
    run = AsyncMock(side_effect=AssertionError("Help must not run recovery"))
    monkeypatch.setattr(recovery, "run", run)
    with pytest.raises(SystemExit) as stopped:
        recovery.main()
    assert stopped.value.code == 0
    output = capsys.readouterr()
    assert "--plan" in output.out and "preview" in output.out
    assert output.err == ""
    run.assert_not_awaited()


@pytest.mark.parametrize("duplicate", ["actor", "target", "counts", "note", "identical"])
def test_cli_rejects_duplicate_json_fields_before_running(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, duplicate: str
) -> None:
    raw = json.dumps(_payload())
    field, replacement = {
        "actor": (
            '"actor_id": "10000000-0000-4000-8000-000000000002"',
            '"actor_id": "10000000-0000-4000-8000-000000000099", '
            '"actor_id": "10000000-0000-4000-8000-000000000002"',
        ),
        "target": (
            '"execution_id": "20000000-0000-4000-8000-000000000001"',
            '"execution_id": "20000000-0000-4000-8000-000000000099", '
            '"execution_id": "20000000-0000-4000-8000-000000000001"',
        ),
        "counts": ('"usable": 1', '"usable": 2, "usable": 1'),
        "note": ('"note": ', '"note": "NEVER_ECHO_PRIVATE_NOTE", "note": '),
        "identical": ('"usable": 1', '"usable": 1, "usable": 1'),
    }[duplicate]
    assert field in raw
    _stdin(monkeypatch, raw.replace(field, replacement, 1).encode())
    run = AsyncMock(return_value={"status": "UNEXPECTED_PARSE"})
    monkeypatch.setattr(recovery, "run", run)
    assert recovery.main() == 1
    output = capsys.readouterr()
    assert json.loads(output.out)["code"] == "INVALID_PLAN"
    assert "NEVER_ECHO" not in output.out + output.err
    run.assert_not_awaited()


def test_cli_rejects_oversized_input_before_database_access(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    monkeypatch.setattr(recovery, "MAX_PLAN_BYTES", 64)
    _stdin(monkeypatch, b"x" * 65)
    database = Mock(side_effect=AssertionError("Database must not be constructed"))
    monkeypatch.setattr(recovery, "DatabaseManager", database)
    assert recovery.main() == 1
    assert json.loads(capsys.readouterr().out)["code"] == "INVALID_PLAN"
    database.assert_not_called()


@pytest.mark.parametrize(
    ("error", "code"),
    [(SQLAlchemyError, "DATABASE_REJECTED"), (RuntimeError, "RECOVERY_FAILED")],
)
def test_cli_does_not_expose_driver_or_application_error_details(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
    error: type[Exception],
    code: str,
) -> None:
    async def fail(mode: str, plan: recovery.PurchaseCurrencyRecoveryPlan) -> dict:
        raise error("NEVER_ECHO_DATABASE_URL_OR_BOUND_VALUES")

    monkeypatch.setattr(recovery, "run", fail)
    _stdin(monkeypatch, json.dumps(_payload()).encode(), "apply")
    assert recovery.main() == 1
    output = capsys.readouterr()
    assert json.loads(output.out)["code"] == code
    assert "NEVER_ECHO" not in output.out + output.err


def test_cli_preserves_explicit_uncertain_commit_result(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    async def uncertain(mode: str, plan: recovery.PurchaseCurrencyRecoveryPlan) -> dict:
        raise recovery.RecoveryError("COMMIT_OUTCOME_UNKNOWN", "Verify the exact plan.")

    monkeypatch.setattr(recovery, "run", uncertain)
    _stdin(monkeypatch, json.dumps(_payload()).encode(), "apply")
    assert recovery.main() == 1
    assert json.loads(capsys.readouterr().out) == {
        "status": "ERROR",
        "code": "COMMIT_OUTCOME_UNKNOWN",
        "message": "Verify the exact plan.",
    }


@pytest.fixture
def run_boundary(monkeypatch: pytest.MonkeyPatch):
    """Synthetic adapter for commit/response failures, not a database substitute."""
    events: list[str] = []
    settings = Mock()
    database = Mock()
    database.dispose = AsyncMock()
    connection = Mock()

    @asynccontextmanager
    async def transaction():
        events.append("begin")
        try:
            yield connection
        except Exception:
            events.append("rollback")
            raise
        events.append("commit")

    async def apply(conn, plan):
        assert conn is connection
        events.append("apply")
        return {"status": "APPLIED", "confirmations_created": 2}

    async def inspect(engine, plan):
        assert engine is database.engine
        events.append("inspect")
        return {"status": "ALREADY_APPLIED", "confirmations_created": 0}

    database.engine.begin.side_effect = transaction
    applied = AsyncMock(side_effect=apply)
    inspected = AsyncMock(side_effect=inspect)
    monkeypatch.setattr(recovery, "get_settings", lambda: settings)
    monkeypatch.setattr(recovery, "DatabaseManager", lambda configuration: database)
    monkeypatch.setattr(recovery, "apply_plan", applied)
    monkeypatch.setattr(recovery, "_readonly_inspect", inspected)
    return database, applied, inspected, events, settings


def test_run_confirms_success_only_after_commit_and_fresh_read(run_boundary) -> None:
    database, applied, inspected, events, settings = run_boundary
    result = asyncio.run(recovery.run("apply", _plan()))
    assert result == {
        "status": "APPLIED",
        "confirmations_created": 2,
        "verified_after_commit": True,
    }
    assert events == ["begin", "apply", "commit", "inspect"]
    applied.assert_awaited_once()
    inspected.assert_awaited_once()
    settings.model_copy.assert_called_once_with(update={"database_echo": False})
    database.dispose.assert_awaited_once()


def test_run_keeps_commit_acknowledgement_failure_uncertain(run_boundary) -> None:
    database, applied, inspected, events, _ = run_boundary

    @asynccontextmanager
    async def lost_acknowledgement():
        yield Mock()
        raise SQLAlchemyError("synthetic lost commit acknowledgement")

    database.engine.begin.side_effect = lost_acknowledgement
    applied.side_effect = None
    applied.return_value = {"status": "APPLIED", "confirmations_created": 2}
    with pytest.raises(recovery.RecoveryError, match="COMMIT_OUTCOME_UNKNOWN"):
        asyncio.run(recovery.run("apply", _plan()))
    applied.assert_awaited_once()
    inspected.assert_not_awaited()
    assert "rollback" not in events
    database.dispose.assert_awaited_once()


def test_run_preserves_precommit_rejection_and_never_claims_applied(run_boundary) -> None:
    database, applied, inspected, events, _ = run_boundary
    applied.side_effect = recovery.RecoveryError("BASELINE_CHANGED", "Synthetic changed basis.")
    with pytest.raises(recovery.RecoveryError, match="BASELINE_CHANGED"):
        asyncio.run(recovery.run("apply", _plan()))
    assert events == ["begin", "rollback"]
    inspected.assert_not_awaited()
    database.dispose.assert_awaited_once()


@pytest.mark.parametrize("failure", ["read_error", "not_found"])
def test_run_does_not_claim_rollback_or_retry_after_committed_verification_failure(
    run_boundary, failure: str
) -> None:
    database, applied, inspected, events, _ = run_boundary
    inspected.side_effect = (
        SQLAlchemyError("synthetic fresh read failure") if (failure == "read_error") else None
    )
    inspected.return_value = {"status": "READY"}
    with pytest.raises(recovery.RecoveryError, match="POST_COMMIT_VERIFICATION_FAILED"):
        asyncio.run(recovery.run("apply", _plan()))
    assert events == ["begin", "apply", "commit"]
    applied.assert_awaited_once()
    inspected.assert_awaited_once()
    database.dispose.assert_awaited_once()


@pytest.mark.parametrize("mode", ["preview", "verify"])
def test_readonly_modes_never_enter_apply_transaction(run_boundary, mode: str) -> None:
    database, applied, inspected, events, _ = run_boundary
    result = asyncio.run(recovery.run(mode, _plan()))
    assert result["status"] == "ALREADY_APPLIED"
    assert events == ["inspect"]
    database.engine.begin.assert_not_called()
    applied.assert_not_awaited()
    inspected.assert_awaited_once()
    database.dispose.assert_awaited_once()


def test_verify_of_unapplied_plan_refuses_without_writing(run_boundary) -> None:
    database, applied, inspected, _, _ = run_boundary
    inspected.side_effect = None
    inspected.return_value = {"status": "READY"}
    with pytest.raises(recovery.RecoveryError, match="NOT_APPLIED"):
        asyncio.run(recovery.run("verify", _plan()))
    database.engine.begin.assert_not_called()
    applied.assert_not_awaited()
    database.dispose.assert_awaited_once()
