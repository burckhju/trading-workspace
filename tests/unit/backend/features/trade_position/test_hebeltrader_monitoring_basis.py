"""The F207-2 consumer receives one scoped owner snapshot, not new economics."""

from contextlib import asynccontextmanager, contextmanager
from dataclasses import asdict, replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from tests.unit.backend.features.trade_position import test_hebeltrader_coverage as examples
from tests.unit.backend.features.trade_position.test_hebeltrader_coverage import (
    POSITION_ID,
    SOURCE_ID,
    TRADE,
    UNDERLYING_ID,
)

from app.core.exceptions import ApplicationError
from app.features.product.domain.models import OptionDirection
from app.features.trade_position.service import hebeltrader_evidence as module

case = examples.case
pytestmark = pytest.mark.asyncio


@pytest.fixture
def snapshot(monkeypatch, case):
    basis, revision, source = case
    session = MagicMock(spec=AsyncSession)
    session.autoflush = True

    @contextmanager
    def no_autoflush():
        previous = session.autoflush
        session.autoflush = False
        try:
            yield
        finally:
            session.autoflush = previous

    session.no_autoflush = no_autoflush()
    repository = SimpleNamespace(history=AsyncMock(return_value=(revision,)))
    product = SimpleNamespace(
        terms_history=AsyncMock(
            return_value=[
                SimpleNamespace(
                    id=UUID(int=800),
                    warrant_id=TRADE.product_id,
                    option_direction=OptionDirection.CALL,
                )
            ]
        )
    )

    async def read_context(actual, **_kwargs):
        assert actual is session
        assert actual.autoflush is False
        return basis, UNDERLYING_ID

    async def read_source(actual, **_kwargs):
        assert actual is session
        assert actual.autoflush is False
        return source

    def evidence_repository(actual):
        assert actual is session
        assert actual.autoflush is False
        return repository

    def product_service(actual):
        assert actual is session
        assert actual.autoflush is False
        return product

    context = AsyncMock(side_effect=read_context)
    source_read = AsyncMock(side_effect=read_source)
    monkeypatch.setattr(module, "_context", context)
    monkeypatch.setattr(module, "_source", source_read)
    monkeypatch.setattr(module, "SqlAlchemyHebeltraderEvidenceRepository", evidence_repository)
    monkeypatch.setattr(module, "WarrantService", product_service)
    return SimpleNamespace(
        session=session,
        repository=repository,
        product=product,
        context=context,
        source_read=source_read,
        basis=basis,
        revision=revision,
        source=source,
        args={"workspace_id": TRADE.workspace_id, "trade_id": TRADE.id, "position_id": POSITION_ID},
    )


def assert_no_write_or_transaction_ownership(snapshot):
    for operation in ("add", "add_all", "delete", "flush", "commit", "rollback", "begin"):
        getattr(snapshot.session, operation).assert_not_called()
    assert snapshot.session.autoflush is True


async def test_one_session_preserves_owner_economics_and_original_references(snapshot, case):
    before = tuple(asdict(value) for value in case)
    result = await module.read_hebeltrader_monitoring_basis(snapshot.session, **snapshot.args)

    assert result.execution_basis is snapshot.basis
    assert result.evidence_revision is snapshot.revision
    assert result.source_evidence is snapshot.source
    assert result.coverage.valuation_basis is snapshot.basis.valuation_basis
    assert result.coverage.basis_id == examples.project(case).basis_id
    assert result.coverage.original_z1_quantity == 100
    assert result.coverage.assigned_z1_sold_quantity == 40
    assert result.coverage.valuation_basis.position.open_quantity == 80
    assert tuple(asdict(value) for value in case) == before
    snapshot.context.assert_awaited_once_with(snapshot.session, **snapshot.args, lock=False)
    snapshot.repository.history.assert_awaited_once_with(TRADE.workspace_id, TRADE.id, POSITION_ID)
    snapshot.source_read.assert_awaited_once_with(
        snapshot.session,
        basis=snapshot.basis,
        underlying_id=UNDERLYING_ID,
        source_version_id=SOURCE_ID,
        reuse_trade_link=False,
    )
    snapshot.product.terms_history.assert_awaited_once_with(TRADE.workspace_id, TRADE.product_id)
    assert result.coverage.read_started_at <= result.coverage.read_completed_at
    assert_no_write_or_transaction_ownership(snapshot)


async def test_requested_trade_lock_stays_with_the_existing_owner(snapshot):
    await module.read_hebeltrader_monitoring_basis(snapshot.session, **snapshot.args, lock=True)
    snapshot.context.assert_awaited_once_with(snapshot.session, **snapshot.args, lock=True)
    assert_no_write_or_transaction_ownership(snapshot)


@pytest.mark.parametrize("status", ["UNVERIFIED", "UNCHANGED_VERIFIED", "ADJUSTMENT_REQUIRED"])
async def test_reviewed_scale_never_qualifies_new_market_observations(snapshot, status):
    revision = replace(
        snapshot.revision,
        declaration=replace(snapshot.revision.declaration, scale_review_status=status),
    )
    snapshot.repository.history.return_value = (revision,)
    result = await module.read_hebeltrader_monitoring_basis(snapshot.session, **snapshot.args)
    assert result.scale.review_status == status
    assert result.scale.source_scale_reference == revision.declaration.source_scale_reference
    assert result.scale.review_reference == revision.declaration.scale_review_reference
    assert result.scale.scope == "SOURCE_AND_PURCHASE_EVIDENCE_ONLY"
    assert result.scale.market_observations_verified is False
    assert_no_write_or_transaction_ownership(snapshot)


async def test_missing_revision_keeps_scale_unverified_and_owner_source_reuse_explicit(snapshot):
    snapshot.repository.history.return_value = ()
    result = await module.read_hebeltrader_monitoring_basis(snapshot.session, **snapshot.args)
    assert result.evidence_revision is None
    assert result.scale.review_status == "UNVERIFIED"
    assert result.scale.source_scale_reference is None
    assert result.scale.review_reference is None
    assert result.scale.market_observations_verified is False
    assert snapshot.source_read.await_args.kwargs["source_version_id"] is None
    assert snapshot.source_read.await_args.kwargs["reuse_trade_link"] is True
    assert_no_write_or_transaction_ownership(snapshot)


async def test_current_revision_keeps_deliberately_cleared_source_pin_cleared(snapshot):
    replacement = replace(
        snapshot.revision,
        id=UUID(int=810),
        supersedes_evidence_id=snapshot.revision.id,
        declaration=replace(snapshot.revision.declaration, source_version_id=None),
    )
    snapshot.repository.history.return_value = (snapshot.revision, replacement)
    snapshot.source_read.side_effect = None
    snapshot.source_read.return_value = None
    result = await module.read_hebeltrader_monitoring_basis(snapshot.session, **snapshot.args)
    assert result.evidence_revision is replacement
    assert result.source_evidence is None
    assert result.coverage.source is None
    assert snapshot.source_read.await_args.kwargs["source_version_id"] is None
    assert snapshot.source_read.await_args.kwargs["reuse_trade_link"] is False
    assert_no_write_or_transaction_ownership(snapshot)


@pytest.mark.parametrize(
    ("directions", "expected", "reason"),
    [
        ((OptionDirection.CALL, OptionDirection.CALL), OptionDirection.CALL, None),
        ((OptionDirection.PUT,), OptionDirection.PUT, None),
        ((), None, "PRODUCT_TERMS_MISSING"),
        ((OptionDirection.CALL, OptionDirection.PUT), None, "PRODUCT_DIRECTION_CONFLICT"),
    ],
)
async def test_option_direction_retains_terms_provenance_without_latest_version_substitution(
    snapshot, directions, expected, reason
):
    terms = [
        SimpleNamespace(id=UUID(int=820 + i), warrant_id=TRADE.product_id, option_direction=value)
        for i, value in enumerate(directions)
    ]
    snapshot.product.terms_history.return_value = terms
    result = await module.read_hebeltrader_monitoring_basis(snapshot.session, **snapshot.args)
    assert result.option_direction is expected
    assert result.option_direction_reason == reason
    assert result.option_terms_version_ids == tuple(term.id for term in terms)
    assert_no_write_or_transaction_ownership(snapshot)


@pytest.mark.parametrize(
    "scope_field", ["workspace_id", "trade_id", "position_id", "product_id", "underlying_id"]
)
async def test_foreign_revision_cannot_supply_typed_scale_to_monitoring(snapshot, scope_field):
    snapshot.repository.history.return_value = (
        replace(snapshot.revision, **{scope_field: UUID(int=830)}),
    )
    with pytest.raises(ApplicationError) as caught:
        await module.read_hebeltrader_monitoring_basis(snapshot.session, **snapshot.args)
    assert caught.value.code == "BASELINE_EVIDENCE_CONFLICT"
    snapshot.product.terms_history.assert_not_awaited()
    assert_no_write_or_transaction_ownership(snapshot)


async def test_foreign_product_terms_are_rejected_before_returning_direction(snapshot):
    snapshot.product.terms_history.return_value[0].warrant_id = UUID(int=840)
    with pytest.raises(ApplicationError) as caught:
        await module.read_hebeltrader_monitoring_basis(snapshot.session, **snapshot.args)
    assert caught.value.code == "BASELINE_PRODUCT_MISMATCH"
    assert_no_write_or_transaction_ownership(snapshot)


async def test_product_read_failure_is_not_reported_as_missing_evidence(snapshot):
    snapshot.product.terms_history.side_effect = RuntimeError("synthetic database failure")
    with pytest.raises(RuntimeError, match="synthetic database failure"):
        await module.read_hebeltrader_monitoring_basis(snapshot.session, **snapshot.args)
    assert_no_write_or_transaction_ownership(snapshot)


async def test_existing_f2074_read_reuses_facts_without_new_product_terms_dependency(
    snapshot, monkeypatch, case
):
    reader = module.HebeltraderEvidenceReader(MagicMock())

    @asynccontextmanager
    async def readonly_snapshot():
        with snapshot.session.no_autoflush:
            yield snapshot.session

    monkeypatch.setattr(reader, "_snapshot", readonly_snapshot)
    result = await reader.read(TRADE.workspace_id, TRADE.id, POSITION_ID)
    assert result.basis_id == examples.project(case).basis_id
    assert result.coverage_status == "COMPLETE"
    snapshot.context.assert_awaited_once_with(snapshot.session, **snapshot.args, lock=False)
    snapshot.product.terms_history.assert_not_awaited()
    assert_no_write_or_transaction_ownership(snapshot)
