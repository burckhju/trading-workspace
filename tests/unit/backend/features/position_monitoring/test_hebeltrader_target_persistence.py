"""Target snapshot storage preserves scope, receipt identity and transaction ownership."""

import importlib.util
from dataclasses import replace
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory

from app.features.position_monitoring.persistence.hebeltrader_targets import (
    HebeltraderTargetAssessmentModel,
    HebeltraderTargetRequestModel,
    SqlAlchemyHebeltraderTargetRepository,
    TargetAssessmentRecord,
    TargetRequestReceipt,
)

ROOT = Path(__file__).resolve().parents[5]
NOW = datetime(2026, 11, 14, 12, tzinfo=UTC)


def assessment(**changes):
    value = TargetAssessmentRecord(
        id=uuid4(),
        workspace_id=uuid4(),
        trade_id=uuid4(),
        position_id=uuid4(),
        product_id=uuid4(),
        underlying_id=uuid4(),
        source_version_id=uuid4(),
        evidence_revision_id=uuid4(),
        previous_assessment_id=None,
        definition_version="hebeltrader-targets-v1",
        baseline_id="HEBELTRADER_CONFIRMED_BASELINE",
        baseline_version="1.0.0",
        basis_id="a" * 64,
        input_fingerprint="b" * 64,
        recorded_at=NOW,
        recorded_by=uuid4(),
        inputs={
            "original_price": "112.1234567890",
            "trading_date": "2026-10-01",
            "source_updated_at": None,
            "time_precision": "DATE_ONLY",
        },
        result={
            "targets": [
                {"target": "Z1", "status": "PROVEN"},
                {"target": "Z2", "status": "NOT_PROVEN"},
            ],
            "domain": {"synthetic": "Persistence boundary only, no rule execution"},
        },
    )
    return replace(value, **changes)


def receipt(value, **changes):
    result = TargetRequestReceipt(
        uuid4(),
        value.workspace_id,
        value.trade_id,
        value.position_id,
        value.id,
        uuid4(),
        "c" * 64,
        value.recorded_at,
        value.recorded_by,
    )
    return replace(result, **changes)


def model(value, cls=HebeltraderTargetAssessmentModel):
    return cls(**{name: getattr(value, name) for name in value.__dataclass_fields__})


@pytest.mark.asyncio
async def test_assessment_and_receipt_flush_without_committing_or_changing_original_input():
    value = assessment()
    request = receipt(value)
    session = Mock(flush=AsyncMock(), commit=AsyncMock(), execute=AsyncMock())
    repo = SqlAlchemyHebeltraderTargetRepository(session)
    await repo.add(value)
    await repo.receipt(request)
    saved, saved_receipt = [call.args[0] for call in session.add.call_args_list]
    assert isinstance(saved, HebeltraderTargetAssessmentModel)
    assert isinstance(saved_receipt, HebeltraderTargetRequestModel)
    assert saved.inputs == value.inputs and saved.result == value.result
    assert saved.source_version_id == value.source_version_id
    assert saved.evidence_revision_id == value.evidence_revision_id
    assert saved_receipt.assessment_id == value.id
    assert saved_receipt.request_id == request.request_id
    assert session.flush.await_count == 2
    session.commit.assert_not_awaited()
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_latest_and_exact_read_are_fully_scoped_without_writes():
    value = assessment(previous_assessment_id=uuid4())
    row = model(replace(value, recorded_at=NOW.replace(tzinfo=None)))
    session = Mock(scalar=AsyncMock(return_value=row), flush=AsyncMock(), commit=AsyncMock())
    repo = SqlAlchemyHebeltraderTargetRepository(session)
    assert await repo.latest(value.workspace_id, value.trade_id, value.position_id) == value
    latest = session.scalar.call_args.args[0].compile()
    assert set(latest.params.values()) == {value.workspace_id, value.trade_id, value.position_id}
    assert "EXISTS" in str(latest) and "previous_assessment_id" in str(latest)
    assert await repo.get(value.workspace_id, value.trade_id, value.position_id, value.id) == value
    exact = session.scalar.call_args.args[0].compile()
    assert set(exact.params.values()) == {
        value.workspace_id,
        value.trade_id,
        value.position_id,
        value.id,
    }
    session.add.assert_not_called()
    session.flush.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_receipt_read_is_tenant_scoped_and_survives_naive_storage_clock():
    request = receipt(assessment())
    row = model(
        replace(request, recorded_at=NOW.replace(tzinfo=None)), HebeltraderTargetRequestModel
    )
    session = Mock(scalar=AsyncMock(return_value=row), flush=AsyncMock(), commit=AsyncMock())
    repo = SqlAlchemyHebeltraderTargetRepository(session)
    assert await repo.find_request(request.workspace_id, request.request_id) == request
    query = session.scalar.call_args.args[0].compile()
    assert set(query.params.values()) == {request.workspace_id, request.request_id}
    session.add.assert_not_called()
    session.flush.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_reads_and_count_never_create_an_assessment_or_request():
    value = assessment()
    session = Mock(scalar=AsyncMock(return_value=None))
    repo = SqlAlchemyHebeltraderTargetRepository(session)
    assert await repo.latest(value.workspace_id, value.trade_id, value.position_id) is None
    assert await repo.get(value.workspace_id, value.trade_id, value.position_id, value.id) is None
    assert await repo.find_request(value.workspace_id, uuid4()) is None
    assert await repo.count(value.workspace_id, value.trade_id, value.position_id) == 0
    session.scalar.return_value = 2
    assert await repo.count(value.workspace_id, value.trade_id, value.position_id) == 2
    count_query = session.scalar.call_args.args[0].compile()
    assert set(count_query.params.values()) == {
        value.workspace_id,
        value.trade_id,
        value.position_id,
    }
    session.add.assert_not_called()


def test_real_postgresql_ddl_graph_scopes_immutability_and_guarded_downgrade(monkeypatch):
    graph = ScriptDirectory(str(ROOT / "backend/migrations"))
    assert graph.get_heads() == ["20261114_0051"]
    assert graph.get_revision("20261114_0051").down_revision == "20261114_0050"
    path = ROOT / "backend/migrations/versions/20261114_0051_hebeltrader_target_assessments.py"
    spec = importlib.util.spec_from_file_location("target_assessment_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output}
    )
    monkeypatch.setattr(module, "op", Operations(context))
    module.upgrade()
    ddl = output.getvalue()
    for owner in (
        "workspaces",
        "trades",
        "positions",
        "warrants",
        "underlyings",
        "position_baseline_evidence",
        "external_observation_versions",
        "hebeltrader_target_assessments",
    ):
        assert f"REFERENCES {owner} (id) ON DELETE RESTRICT" in ddl
    assert "CREATE UNIQUE INDEX uq_hebeltrader_target_root" in ddl
    assert "WHERE previous_assessment_id IS NULL" in ddl
    assert "UNIQUE (previous_assessment_id)" in ddl
    assert "UNIQUE (workspace_id, request_id)" in ddl
    assert ddl.count("BEFORE INSERT OR UPDATE OR DELETE") == 2
    assert "FOR UPDATE" in ddl
    assert "UPDATE positions" not in ddl and "INSERT INTO execution_records" not in ddl
    module.downgrade()
    assert output.getvalue().index("Refusing downgrade") < output.getvalue().index("DROP TRIGGER")
    assert output.getvalue().index("Refusing downgrade") < output.getvalue().index("DROP TABLE")
