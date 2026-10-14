"""Real migrated PostgreSQL + real REST writers, including actual synthetic BUY/SELL.

No providers are called, no executions are inserted as fixtures. Only completed
underlying prices are synthetic seed data; retrieval time is now, not trade time.
"""

import asyncio
import os
from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from tests.integration.backend.test_trade_capture_safety import product, purchase, sql
from tests.integration.backend.test_usd_chf_currency_references import _client, _migrate
from tests.integration.backend.test_usd_chf_currency_references import (
    currency_database as base_database,
)

BASE = "/api/v1/trade-position"
LEARN = "/api/v1/learning"
POST = "/api/v1/post-trade/trades"
WORKSPACE = "00000000-0000-4000-8000-000000000001"
ACTOR = "00000000-0000-4000-8000-000000000002"


@pytest.fixture
def journal_database():
    configured = os.environ.get("TRADING_WORKSPACE_TEST_DATABASE_URL")
    if not configured:
        pytest.skip("Disposable PostgreSQL test URL required")
    assert make_url(configured).database == "trading_workspace_test", "Not a disposable test target"
    yield from base_database.__wrapped__()


async def seed_prices(url, listing_id, *, start=0, stop=20):
    assert make_url(url).database.startswith(("tw_currency_ref_test_", "trading_workspace_test"))
    day = date(2026, 8, 19)
    days = []
    while len(days) < 20:
        if day.weekday() < 5:
            days.append(day)
        day += timedelta(days=1)
    for day in days[start:stop]:
        await sql(
            url,
            """INSERT INTO daily_prices
        (id,workspace_id,listing_id,trading_date,open,high,low,close,currency,
         provider,provider_symbol,retrieved_at,source_updated_at,quality_status,
         warnings,price_type,created_at,updated_at)
        VALUES(:id,:workspace,:listing,:day,100,105,95,102,'EUR','EODHD',
        'SYNTHETIC-NO-PROVIDER',:now,NULL,'VALID','synthetic test observations','EOD',:now,:now)
        """,
            dict(
                id=uuid4(), workspace=WORKSPACE, listing=listing_id, day=day, now=datetime.now(UTC)
            ),
        )


async def command(client, trade, body, key=None, status=200):
    response = await client.post(
        f"{LEARN}/trades/{trade}/journal/commands",
        json=body,
        headers={"Idempotency-Key": key or str(uuid4())},
    )
    assert response.status_code == status, response.text
    return response.json()


async def history(client, trade):
    response = await client.get(f"{LEARN}/trades/{trade}/journal")
    assert response.status_code == 200, response.text
    return response.json()


async def review(client, trade):
    response = await client.post(f"{POST}/{trade}/exit-review")
    assert response.status_code == 201, response.text
    response = await client.put(
        f"{POST}/{trade}/exit-review/draft",
        json={
            "timing": "NOT_ASSESSABLE",
            "process_adherence": "GOOD",
            "risk_decision": "ACCEPTABLE",
            "overall_exit_decision": "NOT_ASSESSABLE",
            "rationale": "Synthetic explicit review, not virtual warrant profit.",
        },
    )
    assert response.status_code == 200, response.text
    response = await client.post(f"{POST}/{trade}/exit-review/finalize")
    assert response.status_code == 200, response.text
    return response.json()["current_version_id"]


async def closed(client):
    pid = await product(client)
    bought = await client.post(BASE + "/purchases/external", json=purchase(pid))
    assert bought.status_code == 201, bought.text
    tid = bought.json()["trade"]["id"]
    # An open real trade is not eligible for a journal or observation.
    initial = dict(
        operation="CREATE_DRAFT",
        expected_latest_version_id=None,
        expected_exit_review_version_id=str(uuid4()),
        confirmed=True,
    )
    assert (await command(client, tid, initial, status=409))["code"] == "JOURNAL_SOURCE_NOT_READY"
    rejected = await client.post(f"{POST}/{tid}/observation")
    assert rejected.status_code == 422, rejected.text
    assert rejected.json()["code"] == "POST_TRADE_NOT_ELIGIBLE"
    sale = await client.post(
        f"{BASE}/trades/{tid}/sales",
        json={
            "quantity": 10,
            "price_per_unit": "0.65",
            "executed_on": "2026-08-18",
            "execution_timezone": "Europe/Berlin",
            "request_id": str(uuid4()),
        },
    )
    assert sale.status_code == 201, sale.text
    assert sale.json()["position"]["is_closed"]
    assert float(sale.json()["position"]["realized_gross_pnl"]) == 1
    started = await client.post(f"{POST}/{tid}/observation")
    assert started.status_code == 201, started.text
    return tid, started.json()["underlying_listing_id"], sale.json()["execution"]["id"], pid


async def ready(client, url):
    tid, listing, sale, pid = await closed(client)
    await seed_prices(url, listing)
    response = await client.get(f"{POST}/{tid}/observation")
    assert response.status_code == 200, response.text
    assert response.json()["is_complete"]
    rid = await review(client, tid)
    return tid, rid, sale, pid


def first(rid, latest=None):
    return dict(
        operation="CREATE_DRAFT",
        expected_latest_version_id=latest,
        expected_exit_review_version_id=rid,
        confirmed=True,
    )


def finish(v, rid):
    return dict(
        operation="FINALIZE",
        version_id=v["id"],
        expected_edit_revision=v["edit_revision"],
        expected_exit_review_version_id=rid,
        confirmed=True,
    )


def test_actual_exit_to_journal_evidence_lesson_and_execution_correction(journal_database):
    url = journal_database
    _migrate(url, "head")

    async def exercise():
        async with _client(url) as client:
            tid, listing, sale, pid = await closed(client)
            await seed_prices(url, listing, stop=19)
            incomplete = (await client.get(f"{POST}/{tid}/observation")).json()
            assert incomplete["available_observation_count"] == 19 and not incomplete["is_complete"]
            assert (await history(client, tid))["versions"] == []
            await seed_prices(url, listing, start=19)
            complete = await client.get(f"{POST}/{tid}/observation")
            assert complete.status_code == 200, complete.text
            assert complete.json()["is_complete"]
            assert complete.json()["completed_at"] >= complete.json()["started_at"]
            rid = await review(client, tid)
            draft = (await command(client, tid, first(rid), "create"))["result_id"]
            # Retry creates no extra version; incorrect pins cannot be used as a fallback.
            assert (await command(client, tid, first(rid), "create"))["replayed"]
            empty = (await history(client, tid))["versions"][0]["version"]
            assert empty["source_exit_review_version_id"] == rid and empty["what_went_well"] is None
            saved = dict(
                operation="SAVE_DRAFT",
                version_id=draft,
                expected_edit_revision=1,
                what_went_well="Ausstieg bewusst dokumentiert",
                would_do_differently=None,
                additional_notes="Underlying-Verlauf beweist keinen Optionsscheinpreis.",
            )
            await command(client, tid, saved, "save")
            assert (await command(client, tid, saved, "save"))["replayed"]
            assert (await command(client, tid, saved, status=409))["code"] == "JOURNAL_CONFLICT"
            v = (await history(client, tid))["versions"][0]["version"]
            await command(client, tid, finish(v, rid), "final")
            snapshot = (await history(client, tid))["versions"][0]["version"]
            assert snapshot["status"] == "FINALIZED"
            assert (await client.get(f"{LEARN}/learning-evidence")).json() == []
            evidence = (
                await command(
                    client,
                    tid,
                    dict(operation="MATERIALIZE", version_id=draft, confirmed=True),
                    "materialize",
                )
            )["result_id"]
            assert (
                await command(
                    client,
                    tid,
                    dict(operation="MATERIALIZE", version_id=draft, confirmed=True),
                    "other",
                )
            )["result_id"] == evidence
            origin = (await client.get(f"{LEARN}/learning-evidence/{evidence}")).json()
            assert origin["source"] == {
                "type": "TRADE_JOURNAL_VERSION",
                "trade_journal_version_id": draft,
            }
            lesson = await client.post(
                f"{LEARN}/lessons",
                json={
                    "title": "Eigene ausdrückliche Interpretation",
                    "main_category": "Prozess",
                    "content": "Diese Reflexion ist eine persönliche Hypothese, kein Marktbeweis.",
                    "tags": [],
                    "evidence_links": [{"learning_evidence_id": evidence, "relation": "SUPPORTS"}],
                },
            )
            assert lesson.status_code == 201, lesson.text
            lid = lesson.json()["lesson_id"]
            lversion = lesson.json()["current_version_id"]
            old_lesson = (await client.get(f"{LEARN}/lessons/{lid}")).json()
            correction = await client.post(
                f"{BASE}/trades/{tid}/executions/{sale}/corrections",
                json={
                    "side": "SELL",
                    "quantity": 10,
                    "price_per_unit": "0.60",
                    "executed_on": "2026-08-18",
                    "execution_timezone": "Europe/Berlin",
                },
            )
            assert correction.status_code == 201, correction.text
            h = await history(client, tid)
            assert not h["handoff"]["ready"] and h["versions"][0]["source_currentness"] == "STALE"
            assert h["versions"][0]["version"] == snapshot
            assert (await client.get(f"{LEARN}/lessons/{lid}")).json() == old_lesson
            # Inspection did not silently mutate persisted review state.
            assert (
                await sql(
                    url, "SELECT currentness FROM exit_review_versions WHERE id=:id", {"id": rid}
                )
            )[0]["currentness"] == "CURRENT"
            await command(client, tid, first(rid, latest=draft), status=409)
            assert (await client.post(f"{POST}/{tid}/exit-review/revalidate")).status_code == 200
            new_rid = await review(client, tid)
            assert new_rid != rid
            successor = (await command(client, tid, first(new_rid, latest=draft)))["result_id"]
            h = await history(client, tid)
            assert h["versions"][0]["version"]["supersedes_version_id"] == draft
            assert h["versions"][-1]["version"] == snapshot
            assert h["versions"][0]["version"]["what_went_well"] == snapshot["what_went_well"]
            assert (await client.get(f"{LEARN}/lessons/{lid}")).json()[
                "current_version_id"
            ] == lversion
            assert (await client.get(f"{LEARN}/journal-versions/{draft}")).json()["versions"][0][
                "version"
            ] == snapshot
            for statement in (
                "UPDATE trade_journal_versions SET additional_notes=additional_notes WHERE id=:id",
                "DELETE FROM trade_journal_versions WHERE id=:id",
                "UPDATE trade_journals SET created_at=created_at+interval '1 second' WHERE id=(SELECT trade_journal_id FROM trade_journal_versions WHERE id=:id)",
                "DELETE FROM trade_journal_version_evidence WHERE trade_journal_version_id=:id",
            ):
                with pytest.raises(IntegrityError):
                    await sql(url, statement, {"id": draft})
            # Add a synthetic parent link solely to exercise the existing delete consumer.
            plan = uuid4()
            await sql(
                url,
                """INSERT INTO trade_plans(id,workspace_id,underlying_id,origin_type,created_at,created_by)
              SELECT :plan,workspace_id,underlying_id,'MANUAL',now(),'synthetic-journal-test' FROM warrants WHERE id=:pid""",
                {"plan": plan, "pid": pid},
            )
            await sql(
                url, "UPDATE trades SET trade_plan_id=:plan WHERE id=:id", {"plan": plan, "id": tid}
            )
            blocked = await client.delete(f"/api/v1/trade-plans/{plan}")
            assert (
                blocked.status_code == 409 and blocked.json()["code"] == "JOURNAL_HISTORY_PROTECTED"
            ), blocked.text
            assert (await client.get(f"{LEARN}/lessons/{lid}")).json() == old_lesson
            assert (await history(client, tid))["versions"][-1]["version"] == snapshot
            assert (
                await sql(
                    url,
                    "SELECT count(*) AS n FROM execution_records WHERE trade_id=:id",
                    {"id": tid},
                )
            )[0]["n"] == 3
            assert (
                await sql(
                    url,
                    "SELECT count(*) AS n FROM trade_journal_versions WHERE id=:id",
                    {"id": successor},
                )
            )[0]["n"] == 1
            # A real cancellation is distinct from economic closure and never starts observation.
            other = await client.post(
                BASE + "/purchases/external", json=purchase(pid, day="2026-08-20")
            )
            assert other.status_code == 201, other.text
            cancelled = other.json()["trade"]["id"]
            preview = (await client.get(f"{BASE}/trades/{cancelled}/cancellation")).json()
            cancelled_response = await client.post(
                f"{BASE}/trades/{cancelled}/cancel",
                json={
                    "expected_product_id": pid,
                    "expected_state_token": preview["state_token"],
                    "reason": "synthetic capture mistake",
                    "confirmed": True,
                },
            )
            assert cancelled_response.status_code == 200, cancelled_response.text
            assert (await client.post(f"{POST}/{cancelled}/observation")).status_code >= 400
            assert (await command(client, cancelled, first(rid), status=404))[
                "code"
            ] == "JOURNAL_NOT_FOUND"
        with pytest.raises(AssertionError, match="journal provenance exists"):
            await asyncio.to_thread(_migrate, url, "20261012_0045", action="downgrade")

    asyncio.run(exercise())


def test_parallel_commands_have_one_winner_or_exact_retry_receipt(journal_database):
    url = journal_database
    _migrate(url, "head")

    async def exercise():
        async with _client(url) as client:
            tid, rid, _, _ = await ready(client, url)
            target = f"{LEARN}/trades/{tid}/journal/commands"

            async def post(body, key):
                return await client.post(target, json=body, headers={"Idempotency-Key": key})

            responses = await asyncio.gather(post(first(rid), "same"), post(first(rid), "same"))
            assert [r.status_code for r in responses] == [200, 200], [r.text for r in responses]
            assert len({r.json()["result_id"] for r in responses}) == 1
            assert sum(r.json()["replayed"] for r in responses) == 1
            v = (await history(client, tid))["versions"][0]["version"]
            body = dict(
                operation="SAVE_DRAFT",
                version_id=v["id"],
                expected_edit_revision=1,
                what_went_well=None,
                would_do_differently="",
                additional_notes="",
            )
            responses = await asyncio.gather(
                post(body | {"additional_notes": "A"}, "A"),
                post(body | {"additional_notes": "B"}, "B"),
            )
            assert sorted(r.status_code for r in responses) == [200, 409], [
                r.text for r in responses
            ]
            v = (await history(client, tid))["versions"][0]["version"]
            assert v["edit_revision"] == 2
            responses = await asyncio.gather(
                post(finish(v, rid), "finishA"), post(finish(v, rid), "finishB")
            )
            assert sorted(r.status_code for r in responses) == [200, 409]
            body = dict(operation="MATERIALIZE", version_id=v["id"], confirmed=True)
            responses = await asyncio.gather(post(body, "eA"), post(body, "eB"))
            assert [r.status_code for r in responses] == [200, 200], [r.text for r in responses]
            assert len({r.json()["result_id"] for r in responses}) == 1
            rows = await sql(url, "SELECT count(*) n FROM trade_journal_version_evidence")
            assert rows[0]["n"] == 1
            responses = await asyncio.gather(
                post(first(rid, v["id"]), "sA"), post(first(rid, v["id"]), "sB")
            )
            assert sorted(r.status_code for r in responses) == [200, 409]
            assert len((await history(client, tid))["versions"]) == 2

    asyncio.run(exercise())


def test_migration_preserves_unknown_legacy_final_and_blocks_source_reassignment(journal_database):
    url = journal_database
    _migrate(url, "20261012_0045")

    async def exercise():
        async with _client(url) as client:
            pid = await product(client)
            response = await client.post(BASE + "/purchases/external", json=purchase(pid))
            assert response.status_code == 201, response.text
            tid = response.json()["trade"]["id"]
            jid = uuid4()
            vid = uuid4()
            await sql(
                url,
                """INSERT INTO trade_journals(id,workspace_id,trade_id,created_at,created_by)
              VALUES(:id,:workspace,:trade,now(),:actor)""",
                dict(id=jid, workspace=WORKSPACE, trade=tid, actor=ACTOR),
            )
            await sql(
                url,
                """INSERT INTO trade_journal_versions(id,trade_journal_id,version,status,
                what_went_well,created_at,created_by,updated_at,updated_by,finalized_at,finalized_by)
              VALUES(:id,:journal,1,'FINALIZED','Legacy original',now(),:actor,now(),:actor,now(),:actor)""",
                dict(id=vid, journal=jid, actor=ACTOR),
            )
        await asyncio.to_thread(_migrate, url, "head")
        async with _client(url) as client:
            h = await history(client, tid)
            v = h["versions"][0]
            assert v["source_currentness"] == "UNKNOWN"
            assert v["version"]["source_exit_review_version_id"] is None
            assert (
                v["version"]["what_went_well"] == "Legacy original"
                and v["version"]["edit_revision"] == 1
            )
            with pytest.raises(IntegrityError):
                await sql(
                    url,
                    "UPDATE trade_journals SET workspace_id=:workspace WHERE id=:id",
                    dict(workspace=uuid4(), id=jid),
                )
            with pytest.raises(IntegrityError):
                await sql(
                    url,
                    "UPDATE trade_journal_versions SET source_exit_review_version_id=:source WHERE id=:id",
                    dict(source=uuid4(), id=vid),
                )
            assert (await history(client, tid))["versions"][0]["version"] == v["version"]

    asyncio.run(exercise())
