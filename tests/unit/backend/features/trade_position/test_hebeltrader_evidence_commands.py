"""Explicit append commands and database-only reads over synthetic owner facts."""

from contextlib import asynccontextmanager
from dataclasses import asdict, replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.unit.backend.features.trade_position import test_hebeltrader_coverage as examples
from tests.unit.backend.features.trade_position.test_hebeltrader_coverage import (
    NOW,
    POSITION_ID,
    SOURCE_ID,
    TRADE,
    UNDERLYING_ID,
)

from app.core.exceptions import ApplicationError
from app.features.learning.application.hebeltrader_source_reader import HebeltraderSourceEvidence
from app.features.trade_position.domain.hebeltrader_evidence import (
    EntryOrderEvidence,
    Z1SaleEvidence,
)
from app.features.trade_position.domain.price_binding import PriceBasis, PriceBinding
from app.features.trade_position.service import hebeltrader_evidence as module

case = examples.case
pytestmark = pytest.mark.asyncio


@pytest.fixture
def command(monkeypatch, case):
    basis, evidence, publisher = case
    session = Mock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    repo = SimpleNamespace(
        find_request=AsyncMock(return_value=None),
        history=AsyncMock(return_value=()),
        add=AsyncMock(),
    )

    def repository(actual):
        assert actual is session
        return repo

    context = AsyncMock(return_value=(basis, UNDERLYING_ID))
    source = AsyncMock(return_value=publisher)
    monkeypatch.setattr(module, "SqlAlchemyHebeltraderEvidenceRepository", repository)
    monkeypatch.setattr(module, "_context", context)
    monkeypatch.setattr(module, "_source", source)
    return SimpleNamespace(
        service=module.HebeltraderEvidenceService(session),
        session=session,
        repo=repo,
        context=context,
        source=source,
        basis=basis,
        existing=evidence,
        publisher=publisher,
        args={
            "workspace_id": TRADE.workspace_id,
            "trade_id": TRADE.id,
            "position_id": POSITION_ID,
            "declaration": evidence.declaration,
            "actor": TRADE.created_by,
            "request_id": UUID(int=100),
            "supersedes_evidence_id": None,
        },
    )


async def record(command, **changes):
    return await command.service.record(**(command.args | changes))


def assert_no_economic_write(command):
    # The repository is evidence-specific. Nothing stages a Trade, execution,
    # position, currency confirmation, activation or delivery in this session.
    command.session.add.assert_not_called()
    command.session.add_all.assert_not_called()
    command.session.delete.assert_not_called()
    command.session.flush.assert_not_called()


async def test_explicit_review_appends_evidence_once_and_preserves_owner_facts(command):
    before = asdict(command.basis)
    result = await record(command)
    assert result.declaration == command.args["declaration"]
    assert result.recorded_by == TRADE.created_by
    assert result.workspace_id == TRADE.workspace_id
    assert result.product_id == TRADE.product_id
    assert result.position_id == POSITION_ID
    assert result.supersedes_evidence_id is None
    command.repo.add.assert_awaited_once_with(result)
    command.session.commit.assert_awaited_once_with()
    command.session.rollback.assert_not_awaited()
    assert command.context.await_args.kwargs["lock"] is True
    assert asdict(command.basis) == before
    assert_no_economic_write(command)


async def test_identical_retry_returns_original_without_new_revision_or_source_lookup(command):
    original = await record(command)
    command.repo.find_request.return_value = original
    command.repo.history.reset_mock()
    command.repo.add.reset_mock()
    command.source.reset_mock()
    command.session.commit.reset_mock()
    replay = await record(command)
    assert replay is original
    command.repo.add.assert_not_awaited()
    command.repo.history.assert_not_awaited()
    command.source.assert_not_awaited()
    command.session.commit.assert_not_awaited()
    assert_no_economic_write(command)


async def test_request_id_cannot_be_reused_for_changed_declaration(command):
    original = await record(command)
    command.repo.find_request.return_value = original
    command.repo.add.reset_mock()
    command.session.commit.reset_mock()
    with pytest.raises(ApplicationError) as raised:
        await record(command, declaration=replace(command.args["declaration"], z1_sales=()))
    assert raised.value.code == "BASELINE_EVIDENCE_REQUEST_CONFLICT"
    assert raised.value.status_code == 409
    command.repo.add.assert_not_awaited()
    command.session.commit.assert_not_awaited()
    command.session.rollback.assert_awaited_once_with()


@pytest.mark.parametrize("stale", [None, UUID(int=999)])
async def test_stale_revision_is_rejected_before_loading_sources(command, stale):
    command.repo.history.return_value = (command.existing,)
    with pytest.raises(ApplicationError) as raised:
        await record(command, supersedes_evidence_id=stale)
    assert raised.value.code == "BASELINE_EVIDENCE_CONFLICT"
    command.repo.add.assert_not_awaited()
    command.source.assert_not_awaited()
    command.session.commit.assert_not_awaited()
    command.session.rollback.assert_awaited_once_with()


async def test_successor_retains_original_and_requires_exact_current_revision(command):
    command.repo.history.return_value = (command.existing,)
    before = asdict(command.existing)
    revised = replace(command.args["declaration"], z1_sales=())
    result = await record(command, supersedes_evidence_id=command.existing.id, declaration=revised)
    assert result.supersedes_evidence_id == command.existing.id
    assert result.declaration.z1_sales == ()
    assert result.id != command.existing.id
    assert asdict(command.existing) == before
    assert command.source.await_args.kwargs["reuse_trade_link"] is False
    command.repo.add.assert_awaited_once_with(result)
    assert_no_economic_write(command)


async def test_first_review_reuses_existing_pin_and_retry_uses_original_request_fingerprint(
    command,
):
    unbound = replace(command.args["declaration"], source_version_id=None)
    original = await record(command, declaration=unbound)
    assert original.declaration.source_version_id == SOURCE_ID
    assert unbound.source_version_id is None
    assert command.source.await_args.kwargs["reuse_trade_link"] is True
    command.repo.find_request.return_value = original
    command.repo.add.reset_mock()
    command.source.reset_mock()
    replay = await record(command, declaration=unbound)
    assert replay is original
    command.repo.add.assert_not_awaited()
    command.source.assert_not_awaited()


async def test_later_explicitly_cleared_pin_is_not_rebound_to_current_trade_link(command):
    command.repo.history.return_value = (command.existing,)
    command.source.return_value = None
    cleared = replace(command.args["declaration"], source_version_id=None)
    result = await record(command, declaration=cleared, supersedes_evidence_id=command.existing.id)
    assert result.declaration.source_version_id is None
    assert command.source.await_args.kwargs["reuse_trade_link"] is False
    assert command.source.await_args.kwargs["source_version_id"] is None


async def test_later_explicit_source_replacement_is_a_new_revision(command):
    command.repo.history.return_value = (command.existing,)
    replacement_id = UUID(int=200)
    command.source.return_value = HebeltraderSourceEvidence(
        replacement_id,
        replace(command.publisher.source, source_version_id=replacement_id, version=2),
    )
    changed = replace(command.args["declaration"], source_version_id=replacement_id)
    result = await record(command, declaration=changed, supersedes_evidence_id=command.existing.id)
    assert result.declaration.source_version_id == replacement_id
    assert command.existing.declaration.source_version_id == SOURCE_ID
    assert command.source.await_args.kwargs["reuse_trade_link"] is False
    assert command.source.await_args.kwargs["source_version_id"] == replacement_id


@pytest.mark.parametrize(
    "reason", ["NOT_FOUND", "NOT_CONFIRMED_PDF", "IDENTITY_MISMATCH", "PROVENANCE_MISMATCH"]
)
async def test_unqualified_explicit_source_is_rejected_without_persistence(command, reason):
    command.source.return_value = HebeltraderSourceEvidence(SOURCE_ID, None, (reason,))
    with pytest.raises(ApplicationError) as raised:
        await record(command)
    assert raised.value.code == "BASELINE_SOURCE_UNSUITABLE"
    command.repo.add.assert_not_awaited()
    command.session.commit.assert_not_awaited()


@pytest.mark.parametrize("role", ["entry", "observation", "sale"])
async def test_unknown_or_foreign_execution_references_are_rejected(command, role):
    declaration = command.args["declaration"]
    if role == "entry":
        declaration = replace(
            declaration,
            entry_order=EntryOrderEvidence("Foreign source order", (UUID(int=999),), True),
        )
    elif role == "observation":
        declaration = replace(
            declaration,
            underlying_trades=(
                replace(declaration.underlying_trades[0], execution_id=UUID(int=999)),
            ),
        )
    else:
        declaration = replace(
            declaration, z1_sales=(Z1SaleEvidence(UUID(int=999), "Foreign sale source"),)
        )
    with pytest.raises(ApplicationError) as raised:
        await record(command, declaration=declaration)
    assert raised.value.code == "BASELINE_EXECUTION_MISMATCH"
    command.repo.add.assert_not_awaited()
    command.session.commit.assert_not_awaited()


@pytest.mark.parametrize("kind", ["axis", "instrument", "currency", "scale"])
async def test_price_binding_and_scale_mismatch_are_not_saved_as_valid(command, kind):
    observation = command.args["declaration"].underlying_trades[0]
    changes = {
        "axis": {"binding": PriceBinding(PriceBasis.WARRANT, UNDERLYING_ID, "USD")},
        "instrument": {"binding": PriceBinding(PriceBasis.UNDERLYING, UUID(int=999), "USD")},
        "currency": {"binding": PriceBinding(PriceBasis.UNDERLYING, UNDERLYING_ID, "EUR")},
        "scale": {"scale_reference": "Different reviewed scale"},
    }
    declaration = replace(
        command.args["declaration"], underlying_trades=(replace(observation, **changes[kind]),)
    )
    with pytest.raises(ApplicationError) as raised:
        await record(command, declaration=declaration)
    assert raised.value.code == (
        "BASELINE_SCALE_MISMATCH" if kind == "scale" else "BASELINE_PRICE_BINDING_MISMATCH"
    )
    command.repo.add.assert_not_awaited()
    command.session.commit.assert_not_awaited()


async def test_a_cancelled_trade_accepts_no_new_evidence(command):
    command.context.return_value = (
        replace(command.basis, trade=replace(TRADE, cancelled_at=NOW)),
        UNDERLYING_ID,
    )
    with pytest.raises(ApplicationError) as raised:
        await record(command)
    assert raised.value.code == "TRADE_CANCELLED"
    command.repo.add.assert_not_awaited()
    command.session.commit.assert_not_awaited()


async def test_database_concurrency_conflict_rolls_back_and_is_not_reported_success(command):
    command.repo.add.side_effect = IntegrityError("synthetic insert", {}, RuntimeError("conflict"))
    with pytest.raises(ApplicationError) as raised:
        await record(command)
    assert raised.value.code == "BASELINE_EVIDENCE_CONFLICT"
    command.session.commit.assert_not_awaited()
    command.session.rollback.assert_awaited_once_with()


async def test_coverage_read_uses_readonly_context_and_no_command_or_commit(command, monkeypatch):
    command.repo.history.return_value = (command.existing,)
    reader = module.HebeltraderEvidenceReader(Mock())

    @asynccontextmanager
    async def snapshot():
        yield command.session

    monkeypatch.setattr(reader, "_snapshot", snapshot)
    result = await reader.read(TRADE.workspace_id, TRADE.id, POSITION_ID)
    assert result.coverage_status == "COMPLETE"
    assert command.context.await_args.kwargs["lock"] is False
    assert command.source.await_args.kwargs["source_version_id"] == SOURCE_ID
    assert command.source.await_args.kwargs["reuse_trade_link"] is False
    command.repo.find_request.assert_not_awaited()
    command.repo.add.assert_not_awaited()
    command.session.commit.assert_not_awaited()
    assert_no_economic_write(command)


async def test_actual_snapshot_sets_database_readonly_and_rolls_back_even_on_success(monkeypatch):
    session = Mock(spec=AsyncSession)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    session.execute = AsyncMock()
    session.rollback = AsyncMock()
    factory = Mock(return_value=session)
    monkeypatch.setattr(module, "AsyncSession", factory)
    engine = Mock()
    reader = module.HebeltraderEvidenceReader(engine)
    async with reader._snapshot() as entered:
        assert entered is session
    factory.assert_called_once_with(engine, expire_on_commit=False, autoflush=False)
    statements = [str(call.args[0]) for call in session.execute.await_args_list]
    assert statements == [
        "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY",
        "SET LOCAL statement_timeout = '10000ms'",
    ]
    session.rollback.assert_awaited_once_with()
    session.commit.assert_not_called()


@pytest.mark.parametrize("mode", ["explicit", "unbound_reuse", "unbound_no_reuse"])
async def test_source_helper_uses_exact_pin_and_never_queries_provider(command, monkeypatch, mode):
    owner = SimpleNamespace(
        find_trade_source=AsyncMock(return_value=SOURCE_ID),
        read=AsyncMock(return_value=command.publisher),
    )
    monkeypatch.setattr(module, "HebeltraderSourceReader", lambda session: owner)
    # The command fixture replaces _source; restore the saved production helper
    # through the separately imported function reference below.
    result = await SOURCE_HELPER(
        command.session,
        basis=command.basis,
        underlying_id=UNDERLYING_ID,
        source_version_id=SOURCE_ID if mode == "explicit" else None,
        reuse_trade_link=mode != "unbound_no_reuse",
    )
    if mode == "unbound_no_reuse":
        assert result is None
        owner.find_trade_source.assert_not_awaited()
        owner.read.assert_not_awaited()
    else:
        assert result is command.publisher
        owner.read.assert_awaited_once_with(
            workspace_id=TRADE.workspace_id,
            source_version_id=SOURCE_ID,
            product_id=TRADE.product_id,
            underlying_id=UNDERLYING_ID,
        )
        if mode == "explicit":
            owner.find_trade_source.assert_not_awaited()
        else:
            owner.find_trade_source.assert_awaited_once_with(
                workspace_id=TRADE.workspace_id, trade_id=TRADE.id
            )


SOURCE_HELPER = module._source


@pytest.mark.parametrize("invalid", ["trade", "position", "position_id"])
async def test_context_rejects_missing_or_foreign_scoped_owner_before_other_reads(
    case, monkeypatch, invalid
):
    basis, _, _ = case
    session = Mock(spec=AsyncSession)
    trade_reader = SimpleNamespace(
        get=AsyncMock(return_value=None if invalid == "trade" else TRADE)
    )
    position_reader = SimpleNamespace(
        get_for_trade=AsyncMock(
            return_value=None if invalid == "position" else basis.valuation_basis.position
        )
    )
    locked_reader = Mock(side_effect=AssertionError("read must not construct command lock reader"))
    monkeypatch.setattr(module, "SqlAlchemyReadOnlyTradeRepository", lambda actual: trade_reader)
    monkeypatch.setattr(module, "SqlAlchemyTradeRepository", locked_reader)
    monkeypatch.setattr(module, "SqlAlchemyPositionRepository", lambda actual: position_reader)
    with pytest.raises(ApplicationError) as raised:
        await module._context(
            session,
            workspace_id=TRADE.workspace_id,
            trade_id=TRADE.id,
            position_id=UUID(int=999) if invalid == "position_id" else POSITION_ID,
            lock=False,
        )
    assert raised.value.code == "BASELINE_POSITION_NOT_FOUND"
    assert raised.value.status_code == 404
    trade_reader.get.assert_awaited_once_with(TRADE.workspace_id, TRADE.id)
    position_reader.get_for_trade.assert_awaited_once_with(TRADE.workspace_id, TRADE.id)
    locked_reader.assert_not_called()
    session.scalars.assert_not_called()
