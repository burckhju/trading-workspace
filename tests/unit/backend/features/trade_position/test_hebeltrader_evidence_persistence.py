"""Evidence storage keeps original dates, decimals and revision order without commits."""

import importlib.util
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory

from app.features.trade_position.domain.hebeltrader_evidence import (
    EntryOrderEvidence,
    HebeltraderEvidenceDeclaration,
    HebeltraderEvidenceRevision,
    UnderlyingTradeEvidence,
    Z1SaleEvidence,
)
from app.features.trade_position.domain.price_binding import PriceBasis, PriceBinding
from app.features.trade_position.persistence.hebeltrader_evidence import (
    DECLARATION,
    HebeltraderEvidenceModel,
    SqlAlchemyHebeltraderEvidenceRepository,
    to_domain,
)

ROOT = Path(__file__).resolve().parents[5]


def evidence():
    execution, underlying = uuid4(), uuid4()
    return HebeltraderEvidenceRevision(
        id=UUID(int=9),
        workspace_id=uuid4(),
        trade_id=uuid4(),
        position_id=uuid4(),
        product_id=uuid4(),
        underlying_id=underlying,
        declaration=HebeltraderEvidenceDeclaration(
            entry_order=EntryOrderEvidence("Synthetic order receipt", (execution,), True),
            source_version_id=uuid4(),
            underlying_trades=(
                UnderlyingTradeEvidence(
                    execution_id=execution,
                    source_reference="Synthetic archived trade",
                    price=Decimal("101.123456789012345"),
                    binding=PriceBinding(PriceBasis.UNDERLYING, underlying, "USD"),
                    scale_reference="Synthetic original scale",
                    last_trade_verified=True,
                    observed_on=date(2026, 8, 17),
                    observation_timezone="America/New_York",
                ),
            ),
            z1_sales=(Z1SaleEvidence(uuid4(), "Synthetic sale confirmation"),),
            z1_sales_reviewed=True,
        ),
        recorded_at=datetime(2026, 11, 14, 8, 1, tzinfo=UTC),
        recorded_by=uuid4(),
        request_id=uuid4(),
        request_fingerprint="a" * 64,
    )


def row(revision):
    return HebeltraderEvidenceModel(
        **{
            name: getattr(revision, name)
            for name in revision.__dataclass_fields__
            if name != "declaration"
        },
        declaration=DECLARATION.dump_python(revision.declaration, mode="json"),
        source_version_id=revision.declaration.source_version_id,
    )


async def test_append_roundtrip_preserves_precision_and_source_without_committing():
    original = evidence()
    session = Mock(flush=AsyncMock(), commit=AsyncMock())
    await SqlAlchemyHebeltraderEvidenceRepository(session).add(original)
    session.add.assert_called_once()
    session.flush.assert_awaited_once()
    session.commit.assert_not_awaited()
    stored = session.add.call_args.args[0]
    assert to_domain(stored) == original
    observation = stored.declaration["underlying_trades"][0]
    assert observation["price"] == "101.123456789012345"
    assert observation["observed_at"] is None
    assert observation["observed_on"] == "2026-08-17"
    assert observation["observation_timezone"] == "America/New_York"
    assert stored.declaration["source_version_id"] == str(original.declaration.source_version_id)


async def test_read_orders_equal_clocks_by_predecessor_and_filters_all_owner_ids():
    original = evidence()
    later = replace(
        original, id=UUID(int=2), request_id=uuid4(), supersedes_evidence_id=original.id
    )
    session = Mock(scalars=AsyncMock(return_value=[row(later), row(original)]))
    values = await SqlAlchemyHebeltraderEvidenceRepository(session).history(
        original.workspace_id, original.trade_id, original.position_id
    )
    assert values == (original, later)
    query = session.scalars.call_args.args[0].compile()
    assert set(query.params.values()) == {
        original.workspace_id,
        original.trade_id,
        original.position_id,
    }
    session.add.assert_not_called()
    session.flush.assert_not_called()
    session.commit.assert_not_called()


async def test_empty_history_and_idempotency_read_are_tenant_scoped():
    original = evidence()
    session = Mock(scalars=AsyncMock(return_value=[]), scalar=AsyncMock(return_value=row(original)))
    repository = SqlAlchemyHebeltraderEvidenceRepository(session)
    assert await repository.history(uuid4(), uuid4(), uuid4()) == ()
    assert await repository.find_request(original.workspace_id, original.request_id) == original
    assert set(session.scalar.call_args.args[0].compile().params.values()) == {
        original.workspace_id,
        original.request_id,
    }
    session.scalar.return_value = None
    assert await repository.find_request(uuid4(), original.request_id) is None
    session.add.assert_not_called()
    session.commit.assert_not_called()


async def test_broken_chain_is_not_silently_returned_as_complete_history():
    original = evidence()
    broken = replace(original, supersedes_evidence_id=uuid4())
    session = Mock(scalars=AsyncMock(return_value=[row(broken)]))
    with pytest.raises(ValueError, match="chain is incomplete or ambiguous"):
        await SqlAlchemyHebeltraderEvidenceRepository(session).history(
            original.workspace_id, original.trade_id, original.position_id
        )
    session.scalars.return_value = [row(original), row(replace(original, id=uuid4()))]
    with pytest.raises(ValueError, match="chain is incomplete or ambiguous"):
        await SqlAlchemyHebeltraderEvidenceRepository(session).history(
            original.workspace_id, original.trade_id, original.position_id
        )


def test_storage_source_mismatch_and_invalid_declaration_fail_closed():
    stored = row(evidence())
    stored.source_version_id = uuid4()
    with pytest.raises(ValueError, match="source reference disagrees"):
        to_domain(stored)
    stored = row(evidence())
    stored.declaration["underlying_trades"][0]["price"] = "NaN"
    with pytest.raises(ValueError):
        to_domain(stored)


def test_migration_graph_and_generated_postgres_ddl_preserve_evidence_boundaries(monkeypatch):
    config = Config()
    config.set_main_option("script_location", str(ROOT / "backend/migrations"))
    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_heads() == ["20261114_0051"]
    revision = scripts.get_revision("20261114_0050")
    assert revision.down_revision == "20261109_0049"
    path = ROOT / "backend/migrations/versions/20261114_0050_position_baseline_evidence.py"
    spec = importlib.util.spec_from_file_location("baseline_evidence_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output}
    )
    monkeypatch.setattr(module, "op", Operations(context))
    module.upgrade()
    ddl = output.getvalue()
    assert "REFERENCES execution_records (id) ON DELETE RESTRICT" in ddl
    assert "REFERENCES external_observation_versions (id) ON DELETE RESTRICT" in ddl
    assert "CREATE UNIQUE INDEX uq_position_baseline_root" in ddl
    assert "WHERE supersedes_evidence_id IS NULL" in ddl
    assert "BEFORE INSERT OR UPDATE OR DELETE" in ddl
    assert "INSERT INTO execution_records" not in ddl
    assert "UPDATE positions" not in ddl
    module.downgrade()
    assert output.getvalue().index("Refusing downgrade") < output.getvalue().index("DROP TABLE")
