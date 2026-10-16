"""Actual PostgreSQL source races and inventory using synthetic REST-captured trades.

No provider/production calls. Existing parent FKs and native row locks, not fake
repositories, must block both mutations and phantom earlier-date observations.
"""

import asyncio
from datetime import date
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from tests.integration.backend.learning.test_journal_write_postgres import (
    BASE,
    LEARN,
    POST,
    WORKSPACE,
    closed,
    ready,
    review,
    seed_prices,
)
from tests.integration.backend.learning.test_journal_write_postgres import (
    journal_database as guarded_database,
)
from tests.integration.backend.test_trade_capture_safety import sql
from tests.integration.backend.test_usd_chf_currency_references import _client, _migrate

from app.features.learning.api.materialization_dependencies import (
    get_ft011_materialization_service,
)
from app.features.learning.persistence.ft011_materialization_repository import (
    SqlAlchemyFt011MaterializationRepository,
)
from app.features.trade_position.persistence.unit_of_work import SqlAlchemyTradePositionUnitOfWork


@pytest.fixture
def source_database():
    yield from guarded_database.__wrapped__()


async def materialize(client, trade, version, key):
    return await client.post(
        f"{LEARN}/trades/{trade}/ft011-evidence/materialize",
        json={"expected_exit_review_version_id": version},
        headers={"Idempotency-Key": key},
    )


async def inventory(client, trade):
    response = await client.get(f"{LEARN}/trades/{trade}/ft011-evidence/history")
    assert response.status_code == 200, response.text
    return response.json()


async def counts(url):
    result = await sql(
        url,
        """SELECT
        (SELECT count(*) FROM learning_evidence) AS evidence,
        (SELECT count(*) FROM ft011_evidence) AS sources,
        (SELECT count(*) FROM ft012_idempotency_records) AS receipts""",
    )
    return dict(result[0])


async def correction(client, trade, sale):
    return await client.post(
        f"{BASE}/trades/{trade}/executions/{sale}/corrections",
        json=dict(
            side="SELL",
            quantity=10,
            price_per_unit="0.60",
            executed_on="2026-08-18",
            execution_timezone="Europe/Berlin",
        ),
    )


async def assert_database_waiter(engine, blocker):
    async def poll():
        while True:
            async with engine.connect() as connection:
                waiting = await connection.scalar(
                    text("""SELECT EXISTS (
                    SELECT 1 FROM pg_stat_activity WHERE datname=current_database()
                    AND wait_event_type='Lock' AND :pid=ANY(pg_blocking_pids(pid)))"""),
                    {"pid": blocker},
                )
                if waiting:
                    return
            await asyncio.sleep(0.01)

    await asyncio.wait_for(poll(), timeout=5)


async def paused_command(sessions, trade, version, entered, release, *, key="stable"):
    async with sessions() as session:
        service = get_ft011_materialization_service(session)
        original = service._handoff_reader

        async def read(**kwargs):
            handoff = await original.get(**kwargs)
            assert handoff.ready
            entered.set_result(await session.scalar(text("SELECT pg_backend_pid()")))
            await asyncio.wait_for(release.wait(), timeout=15)
            return handoff

        service._handoff_reader = SimpleNamespace(get=read)
        return await service.execute(
            workspace_id=UUID(WORKSPACE),
            trade_id=UUID(trade),
            expected_exit_review_version_id=UUID(version),
            idempotency_key=key,
        )


@pytest.mark.parametrize(
    "mutation", ["execution", "review", "stale", "price_update", "price_delete", "backfill"]
)
def test_source_changes_wait_until_evidence_commit_including_phantom_insert(
    source_database, mutation
):
    url = source_database
    _migrate(url, "head")

    async def exercise():
        engine = create_async_engine(url, poolclass=NullPool)
        sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
        try:
            async with _client(url) as client:
                trade, listing, sale, _ = await closed(client)
                await seed_prices(url, listing)
                if mutation == "backfill":
                    # Leave a real weekday hole before finalization, keeping 20 fixture points.
                    await sql(
                        url,
                        "UPDATE daily_prices SET trading_date=:later "
                        "WHERE listing_id=:id AND trading_date=:day",
                        {"id": listing, "day": date(2026, 8, 19), "later": date(2026, 10, 1)},
                    )
                observation = await client.get(f"{POST}/{trade}/observation")
                assert observation.json()["is_complete"]
                version = await review(client, trade)
                entered = asyncio.get_running_loop().create_future()
                release = asyncio.Event()
                command = asyncio.create_task(
                    paused_command(sessions, trade, version, entered, release)
                )
                writer = None
                try:
                    holder = await asyncio.wait_for(entered, timeout=10)
                    if mutation == "execution":
                        writer = asyncio.create_task(correction(client, trade, sale))
                    elif mutation == "review":
                        writer = asyncio.create_task(client.post(f"{POST}/{trade}/exit-review"))
                    else:

                        async def write():
                            async with sessions.begin() as session:
                                assert (
                                    await session.scalar(text("SELECT pg_backend_pid()")) != holder
                                )
                                if mutation == "stale":
                                    await session.execute(
                                        text(
                                            "UPDATE exit_review_versions SET currentness='STALE', "
                                            "stale_at=now(), stale_reason='INPUT_CHANGED' "
                                            "WHERE id=:id"
                                        ),
                                        {"id": version},
                                    )
                                elif mutation == "price_update":
                                    await session.execute(
                                        text(
                                            "UPDATE daily_prices SET high=high+1 "
                                            "WHERE listing_id=:id"
                                        ),
                                        {"id": listing},
                                    )
                                elif mutation == "price_delete":
                                    await session.execute(
                                        text(
                                            "DELETE FROM daily_prices WHERE listing_id=:id "
                                            "AND trading_date=:day"
                                        ),
                                        {"id": listing, "day": date(2026, 8, 19)},
                                    )
                                else:
                                    # The listing FK must block this phantom INSERT.
                                    await session.execute(
                                        text("""INSERT INTO daily_prices
                                        (id,workspace_id,listing_id,trading_date,open,high,low,close,currency,
                                         provider,provider_symbol,retrieved_at,quality_status,warnings,price_type,created_at,updated_at)
                                        VALUES(:id,:ws,:listing,:day,100,105,95,102,'EUR','EODHD',
                                        'SYNTHETIC-BACKFILL',now(),'VALID',
                                        'test fixture','EOD',now(),now())"""),
                                        {
                                            "id": uuid4(),
                                            "ws": WORKSPACE,
                                            "listing": listing,
                                            "day": date(2026, 8, 19),
                                        },
                                    )

                        writer = asyncio.create_task(write())
                    await assert_database_waiter(engine, holder)
                    assert (
                        not writer.done()
                    )  # Actual pg_blocking_pids proof, not a sleep assertion.
                    release.set()
                    receipt = await asyncio.wait_for(command, timeout=10)
                    written = await asyncio.wait_for(writer, timeout=10)
                    if mutation in {"execution", "review"}:
                        assert written.status_code == 201, written.text
                    assert receipt.created and str(receipt.exit_review_version_id) == version
                    old = (await inventory(client, trade))[0]
                    assert old["learning_evidence_id"] == str(receipt.learning_evidence_id)
                    assert (
                        old["exit_review_version_id"] == version
                        and old["source_currentness"] == "STALE"
                    )
                    replay = await materialize(client, trade, version, "stable")
                    assert replay.status_code == 200 and replay.json()["replayed"]
                    assert replay.json()["learning_evidence_id"] == old["learning_evidence_id"]
                    rejected = await materialize(client, trade, version, "not-historical")
                    assert (
                        rejected.status_code == 409
                        and rejected.json()["code"] == "SOURCE_NOT_READY"
                    )
                    assert await counts(url) == {"evidence": 1, "sources": 1, "receipts": 1}
                finally:
                    release.set()
                    await asyncio.gather(
                        command, *([writer] if writer else []), return_exceptions=True
                    )
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_owner_correction_first_conflicts_then_rejects_stored_current_review(
    source_database, monkeypatch
):
    url = source_database
    _migrate(url, "head")

    async def exercise():
        async with _client(url) as client:
            trade, version, sale, _ = await ready(client, url)
            entered, release = asyncio.Event(), asyncio.Event()
            original = SqlAlchemyTradePositionUnitOfWork.commit

            async def pause(self):
                await self.flush()
                entered.set()
                await asyncio.wait_for(release.wait(), timeout=15)
                await original(self)

            with monkeypatch.context() as patch:
                patch.setattr(SqlAlchemyTradePositionUnitOfWork, "commit", pause)
                writer = asyncio.create_task(correction(client, trade, sale))
                try:
                    await asyncio.wait_for(entered.wait(), timeout=10)
                    conflict = await asyncio.wait_for(
                        materialize(client, trade, version, "busy"), timeout=5
                    )
                    assert (
                        conflict.status_code == 409 and conflict.json()["code"] == "SOURCE_BUSY"
                    ), conflict.text
                    assert await counts(url) == {"evidence": 0, "sources": 0, "receipts": 0}
                finally:
                    release.set()
                    written = await asyncio.wait_for(writer, timeout=10)
                    assert written.status_code == 201, written.text
            rejected = await materialize(client, trade, version, "busy")
            assert (
                rejected.status_code == 409 and rejected.json()["code"] == "SOURCE_NOT_READY"
            ), rejected.text
            # No GET or attempted materialization silently revalidated the stored review.
            assert (
                await sql(
                    url,
                    "SELECT currentness FROM exit_review_versions WHERE id=:id",
                    {"id": version},
                )
            )[0]["currentness"] == "CURRENT"
            assert await counts(url) == {"evidence": 0, "sources": 0, "receipts": 0}

    asyncio.run(exercise())


@pytest.mark.parametrize("same_key", [True, False])
def test_parallel_commands_explicit_retry_and_commit_failure_leave_no_orphans(
    source_database, same_key
):
    url = source_database
    _migrate(url, "head")

    async def exercise():
        engine = create_async_engine(url, poolclass=NullPool)
        sessions = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
        try:
            async with _client(url) as client:
                trade, version, _, _ = await ready(client, url)
                async with sessions() as session:
                    service = get_ft011_materialization_service(session)

                    async def fail():
                        raise RuntimeError("synthetic commit failure")

                    service._uow.commit = fail
                    with pytest.raises(RuntimeError, match="synthetic commit"):
                        await service.execute(
                            workspace_id=UUID(WORKSPACE),
                            trade_id=UUID(trade),
                            expected_exit_review_version_id=UUID(version),
                            idempotency_key="failed",
                        )
                assert await counts(url) == {"evidence": 0, "sources": 0, "receipts": 0}
                entered, release = asyncio.get_running_loop().create_future(), asyncio.Event()
                command = asyncio.create_task(
                    paused_command(sessions, trade, version, entered, release)
                )
                key = "stable" if same_key else "second"
                try:
                    await asyncio.wait_for(entered, timeout=10)
                    conflict = await materialize(client, trade, version, key)
                    assert conflict.status_code == 409 and conflict.json()["code"] == "SOURCE_BUSY"
                finally:
                    release.set()
                    first = await asyncio.wait_for(command, timeout=10)
                retry = await materialize(client, trade, version, key)
                assert retry.status_code == 200 and not retry.json()["created"], retry.text
                assert retry.json()["replayed"] == same_key
                assert retry.json()["learning_evidence_id"] == str(first.learning_evidence_id)
                async with sessions() as session:
                    repo = SqlAlchemyFt011MaterializationRepository(session)
                    assert (
                        await repo.list_for_trade(workspace_id=uuid4(), trade_id=UUID(trade)) == ()
                    )
                    assert (
                        await repo.list_for_trade(workspace_id=UUID(WORKSPACE), trade_id=uuid4())
                        == ()
                    )
                assert await counts(url) == {
                    "evidence": 1,
                    "sources": 1,
                    "receipts": 1 if same_key else 2,
                }
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_existing_lesson_readback_uses_postgresql_distinct_ordering(source_database):
    """The existing browser GET must succeed even with no matching Lesson rows."""
    url = source_database
    _migrate(url, "head")

    async def exercise():
        async with _client(url) as client:
            response = await client.get(f"{LEARN}/learning-evidence/{uuid4()}/lessons")
            assert response.status_code == 200, response.text
            assert response.json() == []

    asyncio.run(exercise())


def test_inventory_preserves_old_lesson_version_relations_after_successor(source_database):
    from tests.integration.backend.learning.test_explicit_lesson_review_postgres import (
        body,
        context,
        post,
    )

    url = source_database
    _migrate(url, "head")

    async def exercise():
        async with _client(url) as client:
            trade, version, sale, _ = await ready(client, url)
            first = await materialize(client, trade, version, "old")
            assert first.status_code == 200, first.text
            eid = first.json()["learning_evidence_id"]
            reference_path = f"{LEARN}/learning-evidence/{eid}/lessons"
            empty = await client.get(reference_path)
            assert empty.status_code == 200 and empty.json() == [], empty.text
            response = await client.post(
                f"{LEARN}/lessons",
                json=dict(
                    title="Historical exact relation",
                    main_category="Process",
                    content="My original interpretation",
                    tags=[],
                    evidence_links=[dict(learning_evidence_id=eid, relation="SUPPORTS")],
                ),
            )
            assert response.status_code == 201, response.text
            lid = response.json()["lesson_id"]
            original = await context(client, lid)
            previous = original["history"][0]
            references = await client.get(reference_path)
            assert references.status_code == 200, references.text
            assert len(references.json()) == 1
            assert references.json()[0]["lesson_id"] == lid
            assert references.json()[0]["current_version_id"] == previous["version"]["id"]
            before = (await inventory(client, trade))[0]
            assert before["source_currentness"] == "CURRENT"
            assert before["lesson_links"][0]["lesson_version_id"] == previous["version"]["id"]
            assert before["lesson_links"][0]["relation"] == "SUPPORTS"
            corrected = await correction(client, trade, sale)
            assert corrected.status_code == 201, corrected.text
            status = await client.get(
                f"{LEARN}/trades/{trade}/ft011-evidence/materialization-status"
            )
            assert not status.json()["ready"] and not status.json()["materialized"]
            stale = (await inventory(client, trade))[0]
            assert stale["learning_evidence_id"] == eid and stale["source_currentness"] == "STALE"
            assert (
                stale["stored_review_currentness"] == "CURRENT"
            )  # Inspection is not revalidation.
            assert stale["lesson_links"] == before["lesson_links"]
            assert (await context(client, lid))["history"] == original["history"]
            assert (await client.post(f"{POST}/{trade}/exit-review/revalidate")).status_code == 200
            next_version = await review(client, trade)
            second = await materialize(client, trade, next_version, "new")
            assert second.status_code == 200 and second.json()["learning_evidence_id"] != eid
            next_eid = second.json()["learning_evidence_id"]
            await post(
                client, lid, body(original, "OPEN_SOURCE_REVIEW", reviewed_evidence_ids=[eid])
            )
            c = await context(client, lid)
            await post(
                client,
                lid,
                body(
                    c,
                    "NEW_VERSION",
                    main_category="Process",
                    content="Explicit new interpretation",
                    evidence=[
                        dict(learning_evidence_id=next_eid, relation="SUPPORTS"),
                        dict(learning_evidence_id=eid, relation="CONTRADICTS"),
                    ],
                ),
            )
            latest = await context(client, lid)
            references = await client.get(reference_path)
            assert references.status_code == 200, references.text
            assert len(references.json()) == 1  # Root readback deduplicates V1/V2 links.
            assert references.json()[0]["lesson_id"] == lid
            assert (
                references.json()[0]["current_version_id"] == latest["lesson"]["current_version_id"]
            )
            assert latest["history"][1] == previous
            items = await inventory(client, trade)
            assert len(items) == 2
            old = next(x for x in items if x["learning_evidence_id"] == eid)
            assert old["exit_review_version_id"] == version
            assert old["superseded_by_version_id"] == next_version
            assert {x["relation"] for x in old["lesson_links"]} == {"SUPPORTS", "CONTRADICTS"}
            historical = next(x for x in old["lesson_links"] if not x["is_current_version"])
            assert historical["lesson_version_id"] == previous["version"]["id"]
            assert (
                historical["relation"] == "SUPPORTS"
                and historical["link_id"] == previous["evidence_links"][0]["id"]
            )
            assert old["materialized_at"] == before["materialized_at"]
            assert (await materialize(client, trade, version, "old")).json()[
                "learning_evidence_id"
            ] == eid
            assert await inventory(client, str(uuid4())) == []

    asyncio.run(exercise())
