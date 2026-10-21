"""Native source reads: real owners, guarded disposable PostgreSQL, no external HTTP.

Collection is not execution. No write guard may be bypassed to qualify these cases.
Only the established synthetic EOD fixture used by review setup inserts price rows.
"""

import asyncio
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from tests.integration.backend.learning.test_explicit_lesson_review_postgres import (
    context,
    setup_lesson,
)
from tests.integration.backend.learning.test_journal_write_postgres import (
    LEARN,
    closed,
    command,
    first,
    ready,
)
from tests.integration.backend.test_realized_gross_report_postgres import (
    BASE,
    QUERY,
    _capture_reference,
    _client,
    _report,
    _state,
)
from tests.integration.backend.test_realized_gross_report_postgres import (
    forbid_external_calls as guarded_http,
)
from tests.integration.backend.test_realized_gross_report_postgres import (
    report_database as guarded_database,
)
from tests.integration.backend.test_usd_chf_currency_references import _migrate

from app.core.exceptions import ApplicationError
from app.features.trade_position.service import source_view
from app.features.trade_position.service.source_view import TradeSourceReader


@pytest.fixture
def source_database():
    yield from guarded_database.__wrapped__()


@pytest.fixture(autouse=True)
def forbid_external_calls(monkeypatch):
    yield from guarded_http.__wrapped__(monkeypatch)


async def sources(client, tid, section="", pin=None):
    response = await client.get(
        f"{BASE}/trades/{tid}/sources" + (f"/{section}" if section else ""),
        params={} if pin is None else {"version_id": pin},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["read_started_at"] <= body["read_completed_at"]
    return body["data"]


async def correct(client, tid, eid, *, price="3.00", quantity=40, day="2026-09-12"):
    response = await client.post(
        f"{BASE}/trades/{tid}/executions/{eid}/corrections",
        json=dict(
            side="SELL",
            quantity=quantity,
            price_per_unit=price,
            executed_on=day,
            execution_timezone="Europe/Berlin",
        ),
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_real_reference_sources_correction_and_optional_absence_are_read_only(source_database):
    _migrate(source_database, "head")

    async def exercise():
        async with _client(source_database) as (client, database):
            _, tid, ids = await _capture_reference(client, initial_currency_only=True)
            before = await _state(database.engine)
            original = await sources(client, tid)
            assert original["state"] == "CLOSED" and original["open_quantity"] == 0
            assert len(original["timeline"]) == 6 and len(original["currency_history"]) == 1
            assert [e["id"] for e in original["timeline"]] == ids
            assert all(e["executed_on"] for e in original["timeline"])
            assert {e["currency_resolution"]["currency_code"] for e in original["timeline"]} == {
                "EUR"
            }
            assert "realized_gross_pnl" not in original and "total" not in original
            assert await sources(client, tid, "plan") is None
            assert (await sources(client, tid, "reviews"))["selected"] is None
            assert (await sources(client, tid, "journal"))["selected"] is None
            assert await sources(client, tid, "evidence") == []
            assert Decimal((await _report(client))["summary"]["total"]) == Decimal("10")
            all_months = QUERY | {"from_date": "2026-08-01", "to_date": "2026-10-31"}
            assert Decimal((await _report(client, all_months))["summary"]["total"]) == Decimal("50")
            for section in ("reviews", "journal"):
                response = await client.get(
                    f"{BASE}/trades/{tid}/sources/{section}?version_id={uuid4()}"
                )
                assert response.status_code == 404
                assert response.json()["code"] == "SOURCE_VERSION_NOT_FOUND"
            assert await _state(database.engine) == before
            corrected = await correct(client, tid, ids[4])
            after_write = await _state(database.engine)
            new = await sources(client, tid)
            assert len(new["timeline"]) == 7
            assert next(e for e in new["timeline"] if e["id"] == ids[4]) == original["timeline"][4]
            replacement = next(
                e for e in new["timeline"] if e["id"] == corrected["execution"]["id"]
            )
            assert replacement["supersedes_id"] == ids[4]
            assert len(new["currency_history"]) == 1
            assert Decimal((await _report(client))["summary"]["total"]) == Decimal("30")
            assert Decimal((await _report(client, all_months))["summary"]["total"]) == Decimal("70")
            assert await _state(database.engine) == after_write

    asyncio.run(exercise())


def test_original_plan_and_real_approval_survive_p2_scope_and_limit_rejection(
    source_database, monkeypatch
):
    _migrate(source_database, "head")

    async def exercise():
        async with _client(source_database) as (client, database):
            tid, _, _, _ = await closed(client, planned=True)
            first_plan = await sources(client, tid, "plan")
            pid, p1 = first_plan["plan"]["id"], first_plan["version"]["id"]
            amendment = await client.post(
                f"/api/v1/trade-plans/{pid}/versions/{p1}/amendments",
                json=dict(
                    change_reason="Synthetic later assumption",
                    thesis="P2 not the original plan",
                    entry={"type": "PRICE", "currency": "EUR", "price": "101"},
                    invalidation={"stop_price": "96"},
                    targets=[{"sequence": 1, "price": "111"}],
                    risk_assumptions={"thesis_risk": "Later synthetic risk"},
                ),
            )
            assert amendment.status_code == 201, amendment.text
            assert amendment.json()["id"] != p1
            before = await _state(database.engine)
            selected = await sources(client, tid, "plan")
            assert selected["version"]["id"] == p1
            for field in ("thesis", "entry", "invalidation", "targets", "risk_assumptions"):
                assert selected["version"][field] == first_plan["version"][field]
            assert selected["approval"] == first_plan["approval"]
            assert first_plan["approval"]["trade_plan_version_id"] == p1
            reader = TradeSourceReader(database.engine)
            for method in (
                reader.core,
                reader.plan,
                reader.reviews,
                reader.journal,
                reader.evidence,
            ):
                with pytest.raises(ApplicationError) as error:
                    await method(uuid4(), UUID(tid))
                assert error.value.code == "TRADE_NOT_FOUND"
            with monkeypatch.context() as patch:
                patch.setattr(source_view, "MAX_FACTS", 1)
                response = await client.get(f"{BASE}/trades/{tid}/sources")
                assert response.status_code == 413
                assert response.json()["code"] == "SOURCE_RESOURCE_LIMIT"
                assert "data" not in response.json()
            assert await _state(database.engine) == before

    asyncio.run(exercise())


def test_exact_journal_review_evidence_and_lesson_history_survive_real_correction(source_database):
    _migrate(source_database, "head")

    async def exercise():
        async with _client(source_database) as (client, database):
            tid, rid, sale, jid, jeid, feid, lid = await setup_lesson(client, source_database)
            old = await context(client, lid)
            l1 = old["lesson"]["current_version_id"]
            created = await client.post(
                f"{LEARN}/lessons/{lid}/versions",
                json=dict(
                    main_category="Process",
                    content="A separate later interpretation",
                    evidence_links=[
                        {"learning_evidence_id": jeid, "relation": "CONTEXTUAL"},
                        {"learning_evidence_id": feid, "relation": "CONTRADICTS"},
                    ],
                    expected_current_version_id=l1,
                    expected_current_state=old["lesson"]["current_state"],
                ),
            )
            assert created.status_code == 201, created.text
            l2 = created.json()["current_version_id"]
            assert l1 != l2
            before = await _state(database.engine)
            journal = await sources(client, tid, "journal", jid)
            review = await sources(client, tid, "reviews", rid)
            evidence = await sources(client, tid, "evidence")
            assert journal["selected"]["status"] == "FINALIZED"
            assert journal["selected"]["source_exit_review_version_id"] == rid
            assert journal["selected"]["edit_revision"] >= 1
            assert review["selected"]["version"]["overall_exit_decision"] == "NOT_ASSESSABLE"
            assert review["selected"]["version"]["process_adherence"] == "GOOD"
            assert review["source_currentness"] == journal["source_currentness"] == "CURRENT"
            assert len(evidence) == 2
            by_id = {e["evidence_id"]: e for e in evidence}
            assert by_id[jeid]["journal_version_id"] == jid
            assert by_id[feid]["review_version_id"] == rid
            assert all(e["source_bound"] for e in evidence)
            assert {
                (x["lesson_version_id"], x["relation"]) for x in by_id[jeid]["lesson_links"]
            } == {(l1, "SUPPORTS"), (l2, "CONTEXTUAL")}
            assert {
                (x["lesson_version_id"], x["relation"]) for x in by_id[feid]["lesson_links"]
            } == {(l1, "CONTRADICTS"), (l2, "CONTRADICTS")}
            for section in ("reviews", "journal"):
                wrong = await client.get(
                    f"{BASE}/trades/{uuid4()}/sources/{section}",
                    params={"version_id": rid if section == "reviews" else jid},
                )
                assert wrong.status_code == 404
            assert await _state(database.engine) == before
            await correct(client, tid, sale, price="0.60", quantity=10, day="2026-08-18")
            after_write = await _state(database.engine)
            historical_review = await sources(client, tid, "reviews", rid)
            historical_journal = await sources(client, tid, "journal", jid)
            assert historical_review["selected"] == review["selected"]
            assert historical_journal["selected"] == journal["selected"]
            assert (
                historical_review["source_currentness"]
                == historical_journal["source_currentness"]
                == "STALE"
            )
            assert historical_review["selected"]["version"]["currentness"] == "CURRENT"
            assert await sources(client, tid, "evidence") == evidence
            assert await _state(database.engine) == after_write

    asyncio.run(exercise())


@pytest.mark.parametrize("section", ["core", "journal"])
def test_actual_writer_commits_during_bounded_read_without_mixing_snapshots(
    source_database, monkeypatch, section
):
    _migrate(source_database, "head")

    async def exercise():
        async with _client(source_database) as (client, _database):
            if section == "core":
                _, tid, ids = await _capture_reference(client, initial_currency_only=True)
                original = await sources(client, tid)
            else:
                tid, rid, _, _ = await ready(client, source_database)
                await command(client, tid, first(rid))
                original = await sources(client, tid, "journal")
                draft = original["selected"]
            locked_snapshot, resume = asyncio.Event(), asyncio.Event()
            old_trade = TradeSourceReader._trade
            first_call = True

            async def pause(session, workspace, trade):
                nonlocal first_call
                value = await old_trade(session, workspace, trade)
                if first_call:
                    first_call = False
                    assert (
                        await session.scalar(text("SHOW transaction_isolation"))
                        == "repeatable read"
                    )
                    assert await session.scalar(text("SHOW transaction_read_only")) == "on"
                    locked_snapshot.set()
                    await asyncio.wait_for(resume.wait(), 10)
                return value

            with monkeypatch.context() as patch:
                patch.setattr(TradeSourceReader, "_trade", staticmethod(pause))
                pending = asyncio.create_task(
                    sources(client, tid, "" if section == "core" else section)
                )
                try:
                    await asyncio.wait_for(locked_snapshot.wait(), 5)
                    if section == "core":
                        await asyncio.wait_for(correct(client, tid, ids[4]), 5)
                    else:
                        await asyncio.wait_for(
                            command(
                                client,
                                tid,
                                dict(
                                    operation="SAVE_DRAFT",
                                    version_id=draft["id"],
                                    expected_edit_revision=draft["edit_revision"],
                                    what_went_well="New writer content",
                                    would_do_differently=None,
                                    additional_notes=None,
                                ),
                            ),
                            5,
                        )
                finally:
                    resume.set()
                held = await asyncio.wait_for(pending, 5)
            if section == "core":
                assert held == original
                fresh = await sources(client, tid)
                assert len(fresh["timeline"]) == len(original["timeline"]) + 1
            else:
                assert held["selected"] == original["selected"]
                fresh = await sources(client, tid, "journal")
                assert fresh["selected"]["id"] == draft["id"]
                assert fresh["selected"]["edit_revision"] == draft["edit_revision"] + 1
                assert fresh["selected"]["what_went_well"] == "New writer content"

    asyncio.run(exercise())
