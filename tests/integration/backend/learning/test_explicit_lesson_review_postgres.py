"""Actual capture, journal, review commands and independent PostgreSQL transactions.

Only the existing guarded disposable database fixture and synthetic EOD data are used.
"""

import asyncio
from uuid import uuid4

import pytest
from tests.integration.backend.learning.test_journal_write_postgres import (
    BASE,
    LEARN,
    POST,
    command,
    finish,
    first,
    history,
    ready,
    review,
)
from tests.integration.backend.learning.test_journal_write_postgres import (
    journal_database as guarded_database,
)
from tests.integration.backend.test_trade_capture_safety import sql
from tests.integration.backend.test_usd_chf_currency_references import _client, _migrate

from app.features.learning.persistence.unit_of_work import SqlAlchemyLearningTradeLinkUnitOfWork


@pytest.fixture
def journal_database():
    yield from guarded_database.__wrapped__()


async def setup_lesson(client, url):
    tid, rid, sale, _ = await ready(client, url)
    await command(client, tid, first(rid))
    version = (await history(client, tid))["versions"][0]["version"]
    await command(client, tid, finish(version, rid))
    journal_eid = (
        await command(
            client, tid, dict(operation="MATERIALIZE", version_id=version["id"], confirmed=True)
        )
    )["result_id"]
    ft = await client.post(
        f"{LEARN}/trades/{tid}/ft011-evidence/materialize",
        json={"expected_exit_review_version_id": rid},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert ft.status_code in (200, 201), ft.text
    ft_eid = ft.json()["learning_evidence_id"]
    made = await client.post(
        f"{LEARN}/lessons",
        json=dict(
            title="Explicit review lesson",
            main_category="Process",
            content="Original interpretation, never automatically rewritten.",
            tags=[],
            evidence_links=[
                dict(learning_evidence_id=journal_eid, relation="SUPPORTS"),
                dict(learning_evidence_id=ft_eid, relation="CONTRADICTS"),
            ],
        ),
    )
    assert made.status_code == 201, made.text
    return tid, rid, sale, version["id"], journal_eid, ft_eid, made.json()["lesson_id"]


async def context(client, lid):
    response = await client.get(f"{LEARN}/lessons/{lid}/review-context")
    assert response.status_code == 200, response.text
    return response.json()


def body(context, operation, **kwargs):
    lesson = context["lesson"]
    signal = next(
        (s["signal"]["id"] for s in context["signals"] if s["signal"]["status"] == "OPEN"), None
    )
    return (
        dict(
            operation=operation,
            expected_current_version_id=lesson["current_version_id"],
            expected_current_state=lesson["current_state"],
            expected_open_signal_id=signal,
            reason="Explicit synthetic review decision",
            confirmed=True,
        )
        | kwargs
    )


async def post(client, lid, payload, key=None, status=200):
    response = await client.post(
        f"{LEARN}/lessons/{lid}/review-commands",
        json=payload,
        headers={"Idempotency-Key": key or str(uuid4())},
    )
    assert response.status_code == status, response.text
    return response.json()


async def source(client, eid):
    response = await client.get(f"{LEARN}/learning-evidence/{eid}/currentness")
    assert response.status_code == 200, response.text
    return response.json()


def test_actual_correction_source_review_successor_and_exact_historical_relations(journal_database):
    url = journal_database
    _migrate(url, "head")

    async def exercise():
        async with _client(url) as client:
            tid, rid, sale, jvid, j1, ft, lid = await setup_lesson(client, url)
            c = await context(client, lid)
            old = c["history"][0]
            assert len(c["history"]) == 1 and c["signals"] == []
            assert {x["relation"] for x in old["evidence_links"]} == {"SUPPORTS", "CONTRADICTS"}
            result = await client.post(
                f"{BASE}/trades/{tid}/executions/{sale}/corrections",
                json=dict(
                    side="SELL",
                    quantity=10,
                    price_per_unit="0.60",
                    executed_on="2026-08-18",
                    execution_timezone="Europe/Berlin",
                ),
            )
            assert result.status_code == 201, result.text
            assert (await source(client, ft))["source_currentness"] == "STALE"
            assert (await source(client, j1))["review_currentness"] == "STALE"
            # Reading has no automatic review, lesson or model mutations.
            assert (await context(client, lid))["history"] == c["history"]
            assert (await context(client, lid))["lesson"]["current_state"] == "CURRENT"
            opening = body(c, "OPEN_SOURCE_REVIEW", reviewed_evidence_ids=[j1, ft])
            await post(client, lid, opening, "source")
            c = await context(client, lid)
            assert c["lesson"]["current_state"] == "REVIEW_RECOMMENDED" and c["signals"] == []
            assert c["transitions"][-1]["related_lesson_version_id"] == old["version"]["id"]
            await post(client, lid, body(c, "CONFIRM_UNCHANGED"), "unchanged")
            assert (await source(client, j1))["review_currentness"] == "STALE"
            assert (await context(client, lid))["history"] == [old]
            assert (await post(client, lid, opening, "source"))["replayed"]
            # Only explicit upstream owner commands create the corrected journal.
            rr = await client.post(f"{POST}/{tid}/exit-review/revalidate")
            assert rr.status_code == 200, rr.text
            new_rid = await review(client, tid)
            await command(client, tid, first(new_rid, latest=jvid))
            v2 = (await history(client, tid))["versions"][0]["version"]
            await command(client, tid, finish(v2, new_rid))
            j2 = (
                await command(
                    client, tid, dict(operation="MATERIALIZE", version_id=v2["id"], confirmed=True)
                )
            )["result_id"]
            j1_source = await source(client, j1)
            assert (
                j1_source["source_currentness"] == "SUPERSEDED"
                and j1_source["superseded_by_version_id"] == v2["id"]
            )
            assert (await source(client, j2))["review_currentness"] == "CURRENT"
            c = await context(client, lid)
            await post(
                client,
                lid,
                body(c, "OPEN_SOURCE_REVIEW", reviewed_evidence_ids=[j1, ft]),
                "new-review",
            )
            c = await context(client, lid)
            intended = [
                dict(learning_evidence_id=j2, relation="SUPPORTS"),
                dict(learning_evidence_id=j1, relation="CONTEXTUAL"),
                dict(learning_evidence_id=ft, relation="CONTRADICTS"),
            ]
            decision = body(
                c,
                "NEW_VERSION",
                content="Explicit corrected interpretation.",
                main_category="Process",
                evidence=intended,
            )
            r = await post(client, lid, decision, "new-version")
            current = await context(client, lid)
            assert (
                current["lesson"]["current_state"] == "CURRENT"
                and current["lesson"]["current_version_id"] == r["result_id"]
            )
            assert len(current["history"]) == 2 and current["history"][1] == old
            assert current["history"][0]["version"]["supersedes_version_id"] == old["version"]["id"]
            assert {
                (x["learning_evidence_id"], x["relation"])
                for x in current["history"][0]["evidence_links"]
            } == {(x["learning_evidence_id"], x["relation"]) for x in intended}
            assert (await post(client, lid, decision, "new-version"))["result_id"] == r["result_id"]
            await post(client, lid, decision, "new-version-after-change", status=409)
            # The generic API must not strand an open contradiction signal.
            current_links = current["history"][0]["evidence_links"]
            supporting = next(x["id"] for x in current_links if x["relation"] == "SUPPORTS")
            contradicting = next(x["id"] for x in current_links if x["relation"] == "CONTRADICTS")
            await post(
                client,
                lid,
                body(current, "OPEN_CONTRADICTION_REVIEW", contradiction_link_ids=[supporting]),
                status=422,
            )
            sig = await post(
                client,
                lid,
                body(current, "OPEN_CONTRADICTION_REVIEW", contradiction_link_ids=[contradicting]),
            )
            opened = await context(client, lid)
            assert opened["signals"][0]["trigger_link_ids"] == [contradicting]
            generic = await client.post(
                f"{LEARN}/lessons/{lid}/versions",
                json=dict(
                    main_category="Process",
                    content="Cannot bypass",
                    evidence_links=intended,
                    expected_current_version_id=r["result_id"],
                    expected_current_state="REVIEW_RECOMMENDED",
                ),
            )
            assert generic.status_code == 409, generic.text
            generic = await client.post(
                f"{LEARN}/lessons/{lid}/state-transitions",
                json=dict(
                    expected_state="REVIEW_RECOMMENDED",
                    new_state="CURRENT",
                    reason="Cannot bypass",
                    related_lesson_version_id=r["result_id"],
                ),
            )
            assert generic.status_code == 409, generic.text
            assert (await context(client, lid))["history"] == current["history"]
            await post(client, lid, body(opened, "RETIRE"))
            retired = await context(client, lid)
            assert (
                retired["lesson"]["current_state"] == "RETIRED"
                and retired["history"] == current["history"]
            )
            signal = next(
                s["signal"] for s in retired["signals"] if s["signal"]["id"] == sig["result_id"]
            )
            assert (
                signal["resolution"] == "LESSON_RETIRED"
                and signal["resulting_lesson_version_id"] is None
            )
            assert (await source(client, j1))["source_version_id"] == jvid
            for table in ("model_change_proposals", "model_hypotheses"):
                # Existing governance tables: no implicit creation by any lesson operation.
                assert (await sql(url, f"SELECT count(*) n FROM {table}"))[0]["n"] == 0

    asyncio.run(exercise())


def test_parallel_commands_commit_failures_and_legacy_public_resolution(
    journal_database, monkeypatch
):
    url = journal_database
    _migrate(url, "head")

    async def exercise():
        async with _client(url) as client:
            _, _, _, _, j1, ft, lid = await setup_lesson(client, url)
            original = await context(client, lid)
            opening = body(original, "OPEN_SOURCE_REVIEW", reviewed_evidence_ids=[j1, ft])
            responses = await asyncio.gather(
                post(client, lid, opening, "same"), post(client, lid, opening, "same")
            )
            assert (
                len({r["result_id"] for r in responses}) == 1
                and sum(r["replayed"] for r in responses) == 1
            )
            opened = await context(client, lid)
            payload = body(opened, "CONFIRM_UNCHANGED")
            endpoint = f"{LEARN}/lessons/{lid}/review-commands"
            requests = await asyncio.gather(
                *[
                    client.post(endpoint, json=payload, headers={"Idempotency-Key": key})
                    for key in ("a", "b")
                ]
            )
            assert sorted(r.status_code for r in requests) == [200, 409], [r.text for r in requests]
            assert len((await context(client, lid))["transitions"]) == 2
            now = await context(client, lid)
            command_body = body(now, "OPEN_SOURCE_REVIEW", reviewed_evidence_ids=[j1, ft])

            async def fail_commit(_):
                raise RuntimeError("synthetic review commit failure")

            with monkeypatch.context() as m:
                m.setattr(SqlAlchemyLearningTradeLinkUnitOfWork, "commit", fail_commit)
                with pytest.raises(RuntimeError, match="synthetic review commit failure"):
                    await post(client, lid, command_body, "failed-commit")
            after = await context(client, lid)
            assert (
                after["lesson"] == now["lesson"]
                and after["transitions"] == now["transitions"]
                and after["history"] == original["history"]
            )
            assert (
                await sql(
                    url,
                    "SELECT count(*) n FROM ft012_idempotency_records WHERE idempotency_key='failed-commit'",
                )
            )[0]["n"] == 0
            assert not (await post(client, lid, command_body, "failed-commit"))["replayed"]
            await post(client, lid, body(await context(client, lid), "CONFIRM_UNCHANGED"))
            # Legacy public endpoints now have genuine commit boundaries, not only flush.
            c = await context(client, lid)
            link = next(
                x["id"] for x in c["history"][0]["evidence_links"] if x["relation"] == "CONTRADICTS"
            )
            response = await client.post(
                f"{LEARN}/lessons/{lid}/review-signals", json={"contradiction_link_ids": [link]}
            )
            assert response.status_code == 201, response.text
            signal = response.json()["signal_id"]
            assert (await context(client, lid))["lesson"]["current_state"] == "REVIEW_RECOMMENDED"
            response = await client.post(
                f"{LEARN}/lesson-review-signals/{signal}/resolve-unchanged",
                params={"lesson_id": lid},
            )
            assert response.status_code == 200, response.text
            assert (await context(client, lid))["lesson"]["current_state"] == "CURRENT"
            assert (await context(client, lid))["history"] == original["history"]

    asyncio.run(exercise())
