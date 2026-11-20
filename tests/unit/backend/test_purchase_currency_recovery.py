"""Private-plan validation, stable retry identity and sanitized maintenance CLI."""

import asyncio
import io
import json
from unittest.mock import Mock
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
