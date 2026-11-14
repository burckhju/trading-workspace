"""Actual target-ledger migrations and guards in uniquely created disposable PostgreSQL.

Executions are real synthetic REST commands. Source-import rows are explicit
synthetic database fixtures for FK/confirmation tests, not publisher documents
or service-level source qualifications. Outbound HTTP and lifespan jobs are off.
"""

import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import insert, text, update
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from tests.integration.backend.database.test_position_baseline_evidence_postgres import (
    append as append_evidence,
)
from tests.integration.backend.database.test_position_baseline_evidence_postgres import (
    revision as evidence_revision,
)
from tests.integration.backend.database.test_position_baseline_evidence_postgres import seed
from tests.integration.backend.learning.test_journal_write_postgres import (
    journal_database as guarded_database,
)
from tests.integration.backend.test_realized_gross_report_postgres import (
    _client as real_client,
)
from tests.integration.backend.test_realized_gross_report_postgres import _state
from tests.integration.backend.test_trade_capture_safety import (
    ACTOR,
    BASE,
    WORKSPACE,
    purchase,
    sql,
)
from tests.integration.backend.test_usd_chf_currency_references import _migrate
from tests.unit.backend.features.position_monitoring.test_hebeltrader_target_persistence import (
    assessment,
    receipt,
)

from app.core.exceptions import ApplicationError
from app.features.learning.persistence.models import (
    ExternalObservationImportBatchModel,
    ExternalObservationImportRowModel,
    ExternalObservationModel,
    ExternalObservationVersionModel,
)
from app.features.market.persistence.models import WorkspaceModel
from app.features.position_monitoring.persistence.hebeltrader_targets import (
    HebeltraderTargetAssessmentModel,
    SqlAlchemyHebeltraderTargetRepository,
)
from app.features.position_monitoring.service.hebeltrader_target_contracts import (
    TargetAssessmentCommand,
)
from app.features.position_monitoring.service.hebeltrader_targets import (
    HebeltraderTargetReader,
    HebeltraderTargetService,
)
from app.features.trade_position.persistence.hebeltrader_evidence import (
    SqlAlchemyHebeltraderEvidenceRepository,
)
from app.features.trade_position.persistence.repositories import SqlAlchemyTradeRepository


@pytest.fixture
def target_database():
    # Requires the exact designated test parent, then creates/drops only a fresh UUID DB.
    yield from guarded_database.__wrapped__()


@pytest.fixture(autouse=True)
def forbid_outbound_http(monkeypatch):
    asynchronous = AsyncMock(side_effect=AssertionError("External HTTP forbidden"))
    synchronous = Mock(side_effect=AssertionError("External HTTP forbidden"))
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", asynchronous)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", synchronous)
    yield
    asynchronous.assert_not_awaited()
    synchronous.assert_not_called()


def engine_for(url):
    assert make_url(url).database.startswith("tw_currency_ref_test_")
    return create_async_engine(url, poolclass=NullPool)


def target_check_name(name):
    # The PostgreSQL dialect shortens naming-convention identifiers to 63 bytes.
    constraint = next(
        item
        for item in HebeltraderTargetAssessmentModel.__table__.constraints
        if item.name and item.name.endswith(name)
    )
    return postgresql.dialect().identifier_preparer.format_constraint(constraint)


def record_for(data, underlying, **changes):
    values = dict(
        workspace_id=UUID(WORKSPACE),
        trade_id=UUID(data["trade"]["id"]),
        position_id=UUID(data["position"]["id"]),
        product_id=UUID(data["trade"]["product_id"]),
        underlying_id=underlying,
        source_version_id=None,
        evidence_revision_id=None,
        recorded_at=datetime.now(UTC),
        recorded_by=UUID(ACTOR),
    )
    values.update(changes)
    return assessment(**values)


async def append(url, value=None, request=None, *, rollback=False, barrier=None):
    engine = engine_for(url)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            await session.execute(text("SET LOCAL lock_timeout = '5000ms'"))
            await session.execute(text("SET LOCAL statement_timeout = '10000ms'"))
            repo = SqlAlchemyHebeltraderTargetRepository(session)
            if barrier is not None:
                await barrier.wait()
            if value is not None:
                await repo.add(value)
            if request is not None:
                await repo.receipt(request)
            if rollback:
                await session.rollback()
            else:
                await session.commit()
    finally:
        await engine.dispose()


async def reread(url, value, request=None):
    """A new engine/session on every call models restart rather than an ORM cache hit."""
    engine = engine_for(url)
    try:
        async with async_sessionmaker(engine)() as session:
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            repo = SqlAlchemyHebeltraderTargetRepository(session)
            result = {
                "latest": await repo.latest(value.workspace_id, value.trade_id, value.position_id),
                "exact": await repo.get(
                    value.workspace_id, value.trade_id, value.position_id, value.id
                ),
                "count": await repo.count(value.workspace_id, value.trade_id, value.position_id),
                "receipt": (
                    await repo.find_request(value.workspace_id, request.request_id)
                    if request is not None
                    else None
                ),
            }
            assert await repo.get(uuid4(), value.trade_id, value.position_id, value.id) is None
            assert await repo.latest(value.workspace_id, uuid4(), value.position_id) is None
            assert await repo.count(value.workspace_id, value.trade_id, uuid4()) == 0
            if request is not None:
                assert await repo.find_request(uuid4(), request.request_id) is None
            await session.rollback()
            return result
    finally:
        await engine.dispose()


async def state(url):
    engine = engine_for(url)
    try:
        return await _state(engine)
    finally:
        await engine.dispose()


async def second_position(client, data, underlying):
    current = await client.get(f"/api/v1/warrants/{data['trade']['product_id']}")
    assert current.status_code == 200, current.text
    created = await client.post(
        "/api/v1/warrants",
        json={
            "issuer_id": current.json()["issuer_id"],
            "underlying_id": str(underlying),
            "display_name": "Synthetic independent target guard position",
            "option_direction": "CALL",
            "strike": "550",
            "maturity_date": "2099-12-31",
            "ratio": "0.1",
        },
    )
    assert created.status_code == 201, created.text
    bought = await client.post(BASE + "/purchases/external", json=purchase(created.json()["id"]))
    assert bought.status_code == 201, bought.text
    return bought.json()


async def source_fixture(
    url,
    record,
    *,
    source_name="HEBELTRADER",
    accepted=True,
    foreign_workspace=False,
    unresolved_product=False,
    unresolved_underlying=False,
    future=False,
    future_import=False,
):
    """Legal source-owner fixture shapes; only the tested confirmation/scope may differ."""
    engine = engine_for(url)
    version_id, observation_id, batch_id, row_id = (uuid4() for _ in range(4))
    workspace = uuid4() if foreign_workspace else record.workspace_id
    now = datetime.now(UTC)
    try:
        async with async_sessionmaker(engine)() as session:
            if foreign_workspace:
                await session.execute(
                    insert(WorkspaceModel).values(
                        id=workspace, name="Synthetic foreign target test workspace", created_at=now
                    )
                )
            await session.execute(
                insert(ExternalObservationImportBatchModel).values(
                    id=batch_id,
                    workspace_id=workspace,
                    original_filename="synthetic-target-scope.pdf",
                    content_hash="d" * 64,
                    content_type="application/pdf",
                    file_size_bytes=1,
                    imported_at=now + timedelta(days=1) if future_import else now,
                    imported_by=record.recorded_by,
                )
            )
            await session.execute(
                insert(ExternalObservationImportRowModel).values(
                    id=row_id,
                    batch_id=batch_id,
                    workspace_id=workspace,
                    source_row_number=1,
                    raw_payload={"synthetic": "FK test source, no actual publisher content"},
                    validation_status="VALID",
                    disposition="PENDING",
                    resolved_underlying_id=None if unresolved_underlying else record.underlying_id,
                    resolved_product_id=None if unresolved_product else record.product_id,
                    created_at=now,
                    updated_at=now,
                )
            )
            await session.execute(
                insert(ExternalObservationModel).values(
                    id=observation_id,
                    workspace_id=workspace,
                    current_version_id=version_id,
                    created_at=now,
                    created_by=record.recorded_by,
                )
            )
            await session.execute(
                insert(ExternalObservationVersionModel).values(
                    id=version_id,
                    external_observation_id=observation_id,
                    version=1,
                    underlying_id=record.underlying_id,
                    product_id=record.product_id,
                    source_type="NEWSLETTER_RECOMMENDATION",
                    source_name=source_name,
                    observed_at=datetime(2026, 8, 14, tzinfo=UTC),
                    recorded_at=now + timedelta(days=1) if future else now,
                    imported_at=now + timedelta(days=1) if future_import else now,
                    recording_method="FILE_IMPORT",
                    import_row_id=row_id,
                    source_metadata={"synthetic": "FK test fixture"},
                    created_at=now,
                    created_by=record.recorded_by,
                )
            )
            if accepted:
                await session.execute(
                    update(ExternalObservationImportRowModel)
                    .where(ExternalObservationImportRowModel.id == row_id)
                    .values(
                        disposition="ACCEPTED",
                        target_external_observation_id=observation_id,
                        accepted_external_observation_version_id=version_id,
                        disposed_at=now,
                        disposed_by=record.recorded_by,
                    )
                )
            await session.commit()
            return version_id
    finally:
        await engine.dispose()


def test_target_migration_is_additive_roundtrips_empty_and_refuses_populated_downgrade(
    target_database,
):
    _migrate(target_database, "20261114_0050")

    async def prepare():
        async with real_client(target_database) as (client, _):
            return await seed(client)

    data, underlying = asyncio.run(prepare())
    before = asyncio.run(state(target_database))
    _migrate(target_database, "20261114_0051")
    after = asyncio.run(state(target_database))
    assert after["hebeltrader_target_assessments"] == []
    assert after["hebeltrader_target_requests"] == []
    assert {k: after[k] for k in before if k != "alembic_version"} == {
        k: v for k, v in before.items() if k != "alembic_version"
    }
    _migrate(target_database, "20261114_0050", action="downgrade")
    _migrate(target_database, "20261114_0051")
    value = record_for(data, underlying)
    request = receipt(value)
    asyncio.run(append(target_database, value, request))
    with pytest.raises(AssertionError, match="Refusing downgrade: hebeltrader target evidence"):
        _migrate(target_database, "20261114_0050", action="downgrade")
    saved = asyncio.run(reread(target_database, value, request))
    assert saved == {"latest": value, "exact": value, "count": 1, "receipt": request}
    assert (
        asyncio.run(sql(target_database, "SELECT version_num FROM alembic_version"))[0][
            "version_num"
        ]
        == "20261114_0051"
    )


def test_rollback_immutable_snapshots_receipts_and_restart_reads_preserve_all_other_tables(
    target_database,
):
    _migrate(target_database, "head")

    async def exercise():
        async with real_client(target_database) as (client, _):
            data, underlying = await seed(client)
        value = record_for(data, underlying)
        request = receipt(value)
        before = await state(target_database)
        await append(target_database, value, request, rollback=True)
        assert await state(target_database) == before
        assert (await reread(target_database, value, request))["count"] == 0
        await append(target_database, value, request)
        following = replace(
            value,
            id=uuid4(),
            previous_assessment_id=value.id,
            input_fingerprint="e" * 64,
            result={
                "targets": [
                    {"target": "Z1", "status": "PROVEN"},
                    {"target": "Z2", "status": "PROVEN"},
                ],
                "domain": {"synthetic": "A later preserved snapshot"},
            },
        )
        await append(target_database, following)
        stable = await state(target_database)
        saved = await reread(target_database, value, request)
        assert saved == {"latest": following, "exact": value, "count": 2, "receipt": request}
        assert await state(target_database) == stable
        for table, rows in before.items():
            if table not in {"hebeltrader_target_assessments", "hebeltrader_target_requests"}:
                assert stable[table] == rows, table
        for statement in (
            "UPDATE hebeltrader_target_assessments SET result=result",
            "DELETE FROM hebeltrader_target_assessments",
            "UPDATE hebeltrader_target_requests SET request_fingerprint=repeat('f',64)",
            "DELETE FROM hebeltrader_target_requests",
        ):
            with pytest.raises(IntegrityError, match="immutable"):
                await sql(target_database, statement)
        assert await state(target_database) == stable

    asyncio.run(exercise())


def test_concurrent_roots_successors_and_request_receipts_have_exactly_one_winner(target_database):
    _migrate(target_database, "head")

    async def race(values, *, requests=False):
        barrier = asyncio.Barrier(len(values))
        results = await asyncio.wait_for(
            asyncio.gather(
                *(
                    append(
                        target_database,
                        None if requests else value,
                        value if requests else None,
                        barrier=barrier,
                    )
                    for value in values
                ),
                return_exceptions=True,
            ),
            timeout=20,
        )
        assert sum(result is None for result in results) == 1, results
        errors = [result for result in results if result is not None]
        assert len(errors) == 1 and isinstance(errors[0], IntegrityError), errors
        return values[results.index(None)], str(errors[0])

    async def exercise():
        async with real_client(target_database) as (client, _):
            data, underlying = await seed(client)
        first = record_for(data, underlying)
        winner, error = await race((first, replace(first, id=uuid4())))
        assert "uq_hebeltrader_target_root" in error
        successor = replace(winner, id=uuid4(), previous_assessment_id=winner.id)
        tip, error = await race((successor, replace(successor, id=uuid4())))
        assert "uq_hebeltrader_target_successor" in error
        request = receipt(tip)
        saved_request, error = await race((request, replace(request, id=uuid4())), requests=True)
        assert "uq_hebeltrader_target_request" in error
        saved = await reread(target_database, winner, saved_request)
        assert saved == {"latest": tip, "exact": winner, "count": 2, "receipt": saved_request}
        with pytest.raises(IntegrityError, match="uq_hebeltrader_target_request"):
            await append(
                target_database,
                request=replace(
                    saved_request,
                    id=uuid4(),
                    assessment_id=winner.id,
                    request_fingerprint="f" * 64,
                ),
            )
        assert (await reread(target_database, winner, saved_request))["receipt"] == saved_request

    asyncio.run(exercise())


def test_assessment_waiting_for_evidence_correction_rejects_the_old_snapshot(target_database):
    """A real lock wait must not preserve a snapshot taken before the owner's commit."""
    _migrate(target_database, "head")

    async def exercise():
        async with real_client(target_database) as (client, _):
            data, underlying = await seed(client)
        first = replace(evidence_revision(data, underlying), recorded_at=datetime.now(UTC))
        await append_evidence(target_database, first)
        application = "tw_target_stale_snapshot_" + uuid4().hex
        reader_engine = engine_for(target_database)
        command_engine = create_async_engine(
            target_database,
            poolclass=NullPool,
            connect_args={"server_settings": {"application_name": application}},
        )
        task = None
        try:
            reader = HebeltraderTargetReader(reader_engine)
            report = await reader.read(first.workspace_id, first.trade_id, first.position_id)
            command = TargetAssessmentCommand(
                position_id=first.position_id,
                request_id=uuid4(),
                expected_basis_id=report.current_basis_id,
                expected_assessment_id=None,
            )
            before = await state(target_database)

            async def assess():
                async with async_sessionmaker(command_engine, expire_on_commit=False)() as session:
                    return await HebeltraderTargetService(session).assess(
                        workspace_id=first.workspace_id,
                        trade_id=first.trade_id,
                        command=command,
                        actor=first.recorded_by,
                    )

            async with async_sessionmaker(reader_engine, expire_on_commit=False)() as writer:
                trade = await SqlAlchemyTradeRepository(writer).get(
                    first.workspace_id, first.trade_id
                )
                assert trade is not None
                blocker = await writer.scalar(text("SELECT pg_backend_pid()"))
                following = replace(
                    first,
                    id=uuid4(),
                    request_id=uuid4(),
                    supersedes_evidence_id=first.id,
                    recorded_at=datetime.now(UTC),
                    declaration=replace(
                        first.declaration,
                        entry_order=replace(
                            first.declaration.entry_order,
                            source_reference="Synthetic corrected original order reference",
                        ),
                    ),
                )
                await SqlAlchemyHebeltraderEvidenceRepository(writer).add(following)
                task = asyncio.create_task(assess())

                async def wait_for_actual_lock_wait():
                    while True:
                        if task.done():
                            await task
                            pytest.fail(
                                "Assessment finished before encountering the held owner lock"
                            )
                        await writer.execute(text("SELECT pg_stat_clear_snapshot()"))
                        blocked = await writer.scalar(
                            text("""
                                SELECT EXISTS (
                                  SELECT 1 FROM pg_stat_activity
                                  WHERE datname=current_database()
                                    AND application_name=:application
                                    AND :blocker = ANY(pg_blocking_pids(pid))
                                )
                            """),
                            {"application": application, "blocker": blocker},
                        )
                        if blocked:
                            return
                        await asyncio.sleep(0.01)

                # Synchronize through actual PostgreSQL locks, not a guessed write delay.
                await asyncio.wait_for(wait_for_actual_lock_wait(), timeout=5)
                await writer.commit()
            with pytest.raises(ApplicationError) as failure:
                await asyncio.wait_for(task, timeout=10)
            assert failure.value.code == "HEBELTRADER_BASIS_CONFLICT"
            after = await state(target_database)
            assert after["hebeltrader_target_assessments"] == []
            assert after["hebeltrader_target_requests"] == []
            for table, rows in before.items():
                if table not in {"position_baseline_evidence", "position_baseline_execution_refs"}:
                    assert after[table] == rows, table
            saved = await sql(
                target_database,
                "SELECT id, supersedes_evidence_id FROM position_baseline_evidence "
                "ORDER BY recorded_at",
            )
            assert saved == [
                {"id": first.id, "supersedes_evidence_id": None},
                {"id": following.id, "supersedes_evidence_id": first.id},
            ]
            fresh = await reader.read(first.workspace_id, first.trade_id, first.position_id)
            assert fresh.current_basis_id != report.current_basis_id
            assert fresh.assessment_count == 0 and fresh.latest_assessment is None
        finally:
            if task is not None and not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            await command_engine.dispose()
            await reader_engine.dispose()

    asyncio.run(exercise())


def test_database_rejects_scope_predecessor_receipt_and_malformed_snapshot(target_database):
    _migrate(target_database, "head")

    async def exercise():
        async with real_client(target_database) as (client, _):
            data, underlying = await seed(client)
            other = await second_position(client, data, underlying)
        first = record_for(data, underlying)
        foreign = record_for(other, underlying)
        await append(target_database, first)
        await append(target_database, foreign)
        candidate = replace(first, id=uuid4(), previous_assessment_id=first.id)
        for change, expected in (
            ({"workspace_id": uuid4()}, "trade/workspace/product scope"),
            ({"trade_id": foreign.trade_id}, "trade/workspace/product scope"),
            ({"product_id": foreign.product_id}, "trade/workspace/product scope"),
            ({"position_id": foreign.position_id}, "position scope"),
            ({"underlying_id": uuid4()}, "underlying scope"),
            ({"previous_assessment_id": foreign.id}, "predecessor scope"),
            ({"previous_assessment_id": uuid4()}, "predecessor scope"),
            ({"recorded_at": first.recorded_at - timedelta(seconds=1)}, "chronology"),
            ({"evidence_revision_id": uuid4()}, "execution evidence scope"),
            ({"source_version_id": uuid4()}, "source scope or confirmation"),
            ({"definition_version": "unsupported"}, "unsupported target assessment definition"),
            ({"baseline_id": "OTHER"}, "unsupported target assessment definition"),
            ({"baseline_version": "2"}, "unsupported target assessment definition"),
            ({"basis_id": "short"}, target_check_name("hebeltrader_target_basis")),
            (
                {"input_fingerprint": "short"},
                target_check_name("hebeltrader_target_fingerprint"),
            ),
        ):
            with pytest.raises(IntegrityError, match=expected):
                await append(target_database, replace(candidate, **change))
        for malformed in (
            {},
            {"targets": []},
            {"targets": {}},
            {"targets": [{"target": "Z1", "status": "PROVEN"}]},
            {"targets": [{"target": "Z1", "status": "PROVEN"}] * 2},
            {"targets": [{"target": "Z1", "status": "PROVEN"}, {"target": "Z3"}]},
            {"targets": [{"target": "Z1", "status": "PROVEN"}, {"target": "Z2"}]},
            {
                "targets": [
                    {"target": "Z1", "status": "PROVEN"},
                    {"target": "Z2", "status": "AUTO_SELL_EXECUTED"},
                ]
            },
        ):
            with pytest.raises(DBAPIError):
                await append(target_database, replace(candidate, result=malformed))
        request = receipt(first)
        for change in (
            {"workspace_id": uuid4()},
            {"trade_id": foreign.trade_id},
            {"position_id": foreign.position_id},
            {"assessment_id": foreign.id},
            {"assessment_id": uuid4()},
            {"recorded_at": first.recorded_at - timedelta(seconds=1)},
        ):
            with pytest.raises(IntegrityError, match="request assessment scope or chronology"):
                await append(target_database, request=replace(request, **change))
        assert (await reread(target_database, first))["count"] == 1
        assert (await reread(target_database, foreign))["count"] == 1
        assert await sql(target_database, "SELECT * FROM hebeltrader_target_requests") == []

    asyncio.run(exercise())


def test_confirmed_source_and_execution_evidence_refs_cannot_be_crossed_or_deleted(target_database):
    _migrate(target_database, "head")

    async def exercise():
        async with real_client(target_database) as (client, _):
            data, underlying = await seed(client)
            other = await second_position(client, data, underlying)
        first = record_for(data, underlying)
        foreign = record_for(other, underlying)
        good_source = await source_fixture(target_database, first)
        other_source = await source_fixture(target_database, first)
        foreign_source = await source_fixture(target_database, foreign)
        evidence = evidence_revision(data, underlying)
        evidence = replace(
            evidence,
            recorded_at=datetime.now(UTC),
            declaration=replace(evidence.declaration, source_version_id=good_source),
        )
        await append_evidence(target_database, evidence)
        foreign_evidence = replace(
            evidence_revision(other, underlying), recorded_at=datetime.now(UTC)
        )
        await append_evidence(target_database, foreign_evidence)
        first = replace(
            first,
            recorded_at=datetime.now(UTC),
            source_version_id=good_source,
            evidence_revision_id=evidence.id,
        )
        await append(target_database, first)
        candidate = replace(first, id=uuid4(), previous_assessment_id=first.id)
        for evidence_id in (uuid4(), foreign_evidence.id):
            with pytest.raises(IntegrityError, match="execution evidence scope"):
                await append(target_database, replace(candidate, evidence_revision_id=evidence_id))
        for source in (other_source, foreign_source):
            with pytest.raises(IntegrityError):
                await append(target_database, replace(candidate, source_version_id=source))
        # An unsuitable current source read may conservatively omit its qualified FK.
        # Its original pin remains in the proof and the earlier snapshot is untouched.
        unsuitable = replace(
            candidate,
            source_version_id=None,
            inputs={"source_provenance": {"original_version_id": str(good_source)}},
            result={
                "targets": [
                    {"target": "Z1", "status": "NOT_ASSESSABLE"},
                    {"target": "Z2", "status": "REVIEW_REQUIRED"},
                ],
                "domain": {"synthetic": "The source is retained but not qualified"},
            },
        )
        await append(target_database, unsuitable)
        # Missing binding in the execution declaration cannot be silently filled by this ledger.
        no_source = replace(evidence_revision(other, underlying), recorded_at=datetime.now(UTC))
        no_source = replace(no_source, supersedes_evidence_id=foreign_evidence.id)
        await append_evidence(target_database, no_source)
        with pytest.raises(IntegrityError):
            await append(
                target_database,
                replace(
                    foreign,
                    source_version_id=foreign_source,
                    evidence_revision_id=no_source.id,
                    recorded_at=datetime.now(UTC),
                ),
            )
        for defect in (
            {"source_name": "NOT_HEBELTRADER"},
            {"accepted": False},
            {"foreign_workspace": True},
            {"unresolved_product": True},
            {"unresolved_underlying": True},
            {"future": True},
            {"future_import": True},
        ):
            invalid_source = await source_fixture(target_database, foreign, **defect)
            with pytest.raises(IntegrityError, match="source scope or confirmation"):
                await append(
                    target_database,
                    replace(
                        foreign,
                        source_version_id=invalid_source,
                        recorded_at=datetime.now(UTC),
                    ),
                )
        for statement, identity in (
            ("DELETE FROM position_baseline_evidence WHERE id=:id", evidence.id),
            ("DELETE FROM external_observation_versions WHERE id=:id", good_source),
        ):
            with pytest.raises(IntegrityError):
                await sql(target_database, statement, {"id": identity})
        assert (await reread(target_database, first))["exact"] == first
        assert (await reread(target_database, first))["latest"] == unsuitable
        assert (await reread(target_database, foreign))["count"] == 0

    asyncio.run(exercise())


@pytest.mark.parametrize("action", ["close", "cancel"])
def test_closed_or_cancelled_position_rejects_new_assessment_but_keeps_history(
    target_database, action
):
    _migrate(target_database, "head")

    async def exercise():
        async with real_client(target_database) as (client, _):
            data, underlying = await seed(client)
            first = record_for(data, underlying)
            request = receipt(first)
            await append(target_database, first, request)
            trade_url = BASE + f"/trades/{first.trade_id}"
            if action == "close":
                response = await client.post(
                    trade_url + "/sales",
                    json={
                        "quantity": 10,
                        "price_per_unit": "0.65",
                        "executed_on": "2026-08-18",
                        "execution_timezone": "Europe/Berlin",
                        "request_id": str(uuid4()),
                    },
                )
                assert response.status_code == 201, response.text
            else:
                preview = await client.get(trade_url + "/cancellation")
                assert preview.status_code == 200, preview.text
                response = await client.post(
                    trade_url + "/cancel",
                    json={
                        "expected_product_id": str(first.product_id),
                        "expected_state_token": preview.json()["state_token"],
                        "reason": "Synthetic mistaken entry; retained original facts",
                        "confirmed": True,
                    },
                )
                assert response.status_code == 200, response.text
            with pytest.raises(IntegrityError, match="closed or cancelled position"):
                await append(
                    target_database,
                    replace(
                        first,
                        id=uuid4(),
                        previous_assessment_id=first.id,
                        recorded_at=datetime.now(UTC),
                    ),
                )
            before_read = await state(target_database)
            assert await reread(target_database, first, request) == {
                "latest": first,
                "exact": first,
                "count": 1,
                "receipt": request,
            }
            assert await state(target_database) == before_read

    asyncio.run(exercise())
