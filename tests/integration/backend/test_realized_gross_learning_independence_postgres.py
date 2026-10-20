"""A populated incomplete/stale learning process cannot gate qualified SELLs.

Uses actual capture, confirmation, observation, review, journal and lesson owners
in a fresh guarded database. NOT_READY is the existing handoff's ready=False
result over a persisted ACTIVE observation, not an invented database enum.
Stored STALE is produced by the explicit review-revalidation command.
"""

import asyncio
from collections.abc import Iterator
from uuid import uuid4

import pytest
from tests.integration.backend.learning.test_ft011_consistency_postgres import materialize
from tests.integration.backend.learning.test_journal_write_postgres import (
    BASE,
    LEARN,
    POST,
    closed,
    command,
    finish,
    first,
    history,
    review,
    seed_prices,
)
from tests.integration.backend.learning.test_journal_write_postgres import (
    journal_database as guarded_database,
)
from tests.integration.backend.test_realized_gross_report_postgres import (
    DECLARATION,
    QUERY,
    _client,
    _report,
    _state,
)
from tests.integration.backend.test_realized_gross_report_postgres import (
    forbid_external_calls as guarded_http,
)
from tests.integration.backend.test_usd_chf_currency_references import _migrate

AUGUST = QUERY | {"from_date": "2026-08-01", "to_date": "2026-08-31"}


@pytest.fixture
def learning_report_database() -> Iterator[str]:
    yield from guarded_database.__wrapped__()


@pytest.fixture(autouse=True)
def forbid_external_calls(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    yield from guarded_http.__wrapped__(monkeypatch)


def _same_financial_response(before: dict, after: dict) -> None:
    # A repeated request has new wall-clock read/calculation times. Exact source
    # identity and every financial/filter/provenance output must remain the same.
    assert before["basis"]["id"] == after["basis"]["id"]
    assert before["basis"]["knowledge"] == after["basis"]["knowledge"]
    assert {key: value for key, value in before.items() if key != "basis"} == {
        key: value for key, value in after.items() if key != "basis"
    }


def test_report_ignores_persisted_incomplete_observation_and_stale_review(
    learning_report_database: str,
) -> None:
    _migrate(learning_report_database, "head")

    async def exercise() -> None:
        async with _client(learning_report_database) as (client, database):
            trade_id, listing_id, sale_id, _ = await closed(client)
            created = await _state(database.engine)
            assert len(created["execution_records"]) == 2
            for execution in created["execution_records"]:
                confirmed = await client.post(
                    f"{BASE}/trades/{trade_id}/executions/{execution['id']}/currency-confirmations",
                    json=DECLARATION | {"request_id": str(uuid4())},
                )
                assert confirmed.status_code == 201, confirmed.text

            handoff = await client.get(f"{POST}/{trade_id}/handoff")
            assert handoff.status_code == 200, handoff.text
            assert handoff.json()["ready"] is False
            assert handoff.json()["reason"] == "POST_TRADE_OBSERVATION_INCOMPLETE"
            incomplete = await _state(database.engine)
            assert len(incomplete["post_trade_observations"]) == 1
            observation = incomplete["post_trade_observations"][0]
            assert observation["status"] == "ACTIVE"
            assert observation["target_observation_count"] == 20
            assert observation["completed_at"] is None
            assert incomplete["daily_prices"] == []
            assert incomplete["exit_review_versions"] == []
            financial = await _report(client, AUGUST)
            assert financial["summary"]["status"] == "COMPLETE"
            assert financial["summary"]["total_display"] == "1.00"
            assert financial["counts"]["usable"] == 1
            assert financial["items"][0]["execution_id"] == sale_id
            assert await _state(database.engine) == incomplete

            # Existing synthetic EOD fixture plus explicit existing owner actions.
            # These setup calls can write; only the later report GET is under test.
            await seed_prices(learning_report_database, listing_id)
            completed = await client.get(f"{POST}/{trade_id}/observation")
            assert completed.status_code == 200 and completed.json()["is_complete"]
            review_id = await review(client, trade_id)
            journal_id = (await command(client, trade_id, first(review_id)))["result_id"]
            await command(
                client,
                trade_id,
                {
                    "operation": "SAVE_DRAFT",
                    "version_id": journal_id,
                    "expected_edit_revision": 1,
                    "what_went_well": "Synthetic preserved journal statement",
                    "would_do_differently": None,
                    "additional_notes": "Report reads must preserve this exact text.",
                },
            )
            version = (await history(client, trade_id))["versions"][0]["version"]
            await command(client, trade_id, finish(version, review_id))
            journal_evidence = (
                await command(
                    client,
                    trade_id,
                    {"operation": "MATERIALIZE", "version_id": journal_id, "confirmed": True},
                )
            )["result_id"]
            ft011 = await materialize(client, trade_id, review_id, str(uuid4()))
            assert ft011.status_code == 200, ft011.text
            ft011_evidence = ft011.json()["learning_evidence_id"]
            lesson = await client.post(
                f"{LEARN}/lessons",
                json={
                    "title": "Synthetic financial independence context",
                    "main_category": "Process",
                    "content": "Retain this interpretation despite later execution correction.",
                    "tags": [],
                    "evidence_links": [
                        {"learning_evidence_id": journal_evidence, "relation": "SUPPORTS"},
                        {"learning_evidence_id": ft011_evidence, "relation": "CONTEXTUAL"},
                    ],
                },
            )
            assert lesson.status_code == 201, lesson.text
            populated = await _state(database.engine)
            assert len(populated["trade_journal_versions"]) == 1
            assert len(populated["learning_evidence"]) == 2
            assert len(populated["ft011_evidence"]) == 1
            assert len(populated["lesson_versions"]) == 1
            assert len(populated["lesson_evidence_links"]) == 2
            assert populated["exit_review_versions"][0]["currentness"] == "CURRENT"
            _same_financial_response(financial, await _report(client, AUGUST))
            assert await _state(database.engine) == populated

            correction = await client.post(
                f"{BASE}/trades/{trade_id}/executions/{sale_id}/corrections",
                json={
                    "side": "SELL",
                    "quantity": 10,
                    "price_per_unit": "0.60",
                    "executed_on": "2026-08-18",
                    "execution_timezone": "Europe/Berlin",
                    "currency_confirmation": DECLARATION,
                },
            )
            assert correction.status_code == 201, correction.text
            corrected = await _report(client, AUGUST)
            assert corrected["summary"]["status"] == "COMPLETE"
            assert corrected["summary"]["total_display"] == "0.50"
            assert corrected["items"][0]["execution_id"] == correction.json()["execution"]["id"]
            assert (await _state(database.engine))["exit_review_versions"][0][
                "currentness"
            ] == "CURRENT"

            revalidated = await client.post(f"{POST}/{trade_id}/exit-review/revalidate")
            assert revalidated.status_code == 200, revalidated.text
            handoff = await client.get(f"{POST}/{trade_id}/handoff")
            assert handoff.status_code == 200, handoff.text
            assert handoff.json()["ready"] is False
            assert handoff.json()["reason"] == "EXIT_REVIEW_STALE"
            stale = await _state(database.engine)
            stored_review = stale["exit_review_versions"][0]
            assert str(stored_review["id"]) == review_id
            assert stored_review["status"] == "FINALIZED"
            assert stored_review["currentness"] == "STALE"
            assert stored_review["stale_at"] is not None
            assert stored_review["stale_reason"]
            for table in (
                "trade_journals",
                "trade_journal_versions",
                "learning_evidence",
                "ft011_evidence",
                "lessons",
                "lesson_versions",
                "lesson_evidence_links",
            ):
                assert stale[table] == populated[table]

            # GET cannot revalidate, materialize, duplicate linked SELLs or rewrite
            # old interpretation/evidence. Exact corrected economic source is stable.
            _same_financial_response(corrected, await _report(client, AUGUST))
            assert await _state(database.engine) == stale

    asyncio.run(exercise())
