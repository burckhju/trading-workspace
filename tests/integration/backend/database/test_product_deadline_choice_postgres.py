"""Original-file and personal-exit choices on actual guarded disposable owners."""

import asyncio
import base64
from datetime import timedelta
from uuid import uuid4

from tests.integration.backend.database import test_saved_quote_evidence_postgres as saved
from tests.integration.backend.database.test_product_deadline_review_postgres import (
    ASSESSMENTS,
    listing_html,
    post,
    prepare,
)
from tests.integration.backend.database.test_product_price_scale_evidence_postgres import engine_for
from tests.integration.backend.test_realized_gross_report_postgres import _client, _state
from tests.integration.backend.test_usd_chf_currency_references import _migrate

deadline_database = saved.quote_database
forbid_outbound_http = saved.forbid_outbound_http


def test_choice_is_explicit_scoped_idempotent_and_passive_with_concurrency_guards(
    deadline_database,
):
    _migrate(deadline_database, "head")

    async def exercise():
        engine = engine_for(deadline_database)
        try:
            async with _client(deadline_database) as (client, database):
                scope = await prepare(client, database, with_calendar=False)
                before = await _state(engine)
                choices = await asyncio.gather(
                    *(client.put(scope["choice_url"], json=scope["choice_body"]) for _ in range(3))
                )
                assert all(row.status_code == 200 for row in choices)
                assert {row.json()["revision_number"] for row in choices} == {1}
                assert await _state(engine) == before
                for key, value in (
                    ("expected_terms_id", str(uuid4())),
                    ("expected_listing_version", 99999),
                    ("expected_venue_version", 99999),
                ):
                    result = await client.put(
                        scope["choice_url"], json={**scope["choice_body"], key: value}
                    )
                    assert result.status_code == 409, result.text
                assert await _state(engine) == before
                foreign = await post(
                    client,
                    "/api/v1/warrants",
                    {
                        "issuer_id": scope["product"]["issuer_id"],
                        "underlying_id": scope["product"]["underlying_id"],
                        "display_name": "Synthetic foreign exit-choice instrument",
                        "option_direction": "CALL",
                        "strike": "100",
                        "maturity_date": scope["term"].isoformat(),
                        "ratio": "0.1",
                    },
                )
                foreign_listing = await post(
                    client,
                    f"/api/v1/warrants/{foreign['id']}/listings",
                    {
                        "trading_venue_id": scope["venue"]["id"],
                        "quotation_currency_code": "EUR",
                    },
                )
                foreign_before = await _state(engine)
                result = await client.put(
                    scope["choice_url"],
                    json={
                        **scope["choice_body"],
                        "listing_id": foreign_listing["id"],
                    },
                )
                assert (
                    result.status_code == 422
                    and result.json()["code"] == "PRODUCT_EXIT_LISTING_UNAVAILABLE"
                )
                assert await _state(engine) == foreign_before
                response = await client.get(scope["choice_url"])
                assert response.status_code == 200 and response.json()["status"] == "AVAILABLE"
                assert await _state(engine) == foreign_before
                withdrawal = {
                    **scope["choice_body"],
                    "listing_id": None,
                    "expected_revision_number": 1,
                    "expected_listing_version": None,
                    "expected_venue_version": None,
                }
                response = await client.put(scope["choice_url"], json=withdrawal)
                assert response.status_code == 200
                assert response.json()["selected_listing_id"] is None
                assert response.json()["reasons"] == ["PRODUCT_EXIT_LISTING_WITHDRAWN"]
                withdrawn = await _state(engine)
                assert len(withdrawn["product_deadline_exit_choices"]) == 2
                assert len(withdrawn[ASSESSMENTS]) == 0 and withdrawn["alerts"] == []
                assert (await client.put(scope["choice_url"], json=withdrawal)).status_code == 200
                assert (await client.get(scope["choice_url"])).json()["selected_listing_id"] is None
                assert await _state(engine) == withdrawn
                stale = await client.put(scope["choice_url"], json=scope["choice_body"])
                assert (
                    stale.status_code == 409
                    and stale.json()["code"] == "PRODUCT_EXIT_CHOICE_CHANGED"
                )
        finally:
            await engine.dispose()

    asyncio.run(exercise())


def test_original_revision_withdrawal_and_changed_terms_never_reuse_old_qualification(
    deadline_database,
):
    _migrate(deadline_database, "head")

    async def exercise():
        engine = engine_for(deadline_database)
        try:
            async with _client(deadline_database) as (client, database):
                scope = await prepare(client, database, with_calendar=False)
                original = (await client.get(scope["source_url"] + "/current")).json()
                state = await _state(engine)
                assert (
                    original["verification"]
                    == "USER_SUPPLIED_ORIGINAL_NOT_INDEPENDENT_VERIFICATION"
                )
                assert original["receipt_time_basis"] == "FILE_RECEIVED_AT"
                body = {"document_base64": base64.b64encode(listing_html(scope["term"])).decode()}
                repeats = await asyncio.gather(
                    *(client.post(scope["source_url"] + "/imports", json=body) for _ in range(3))
                )
                assert {row.status_code for row in repeats} == {201}
                assert {row.json()["revision_id"] for row in repeats} == {original["revision_id"]}
                assert await _state(engine) == state
                changed = await post(
                    client,
                    scope["source_url"] + "/imports",
                    {
                        "document_base64": base64.b64encode(
                            listing_html(scope["term"], label="Zahltag")
                        ).decode(),
                    },
                )
                assert changed["status"] == "UNSUITABLE" and changed["last_trading_on"] is None
                assert changed["revision_number"] == 2
                response = await client.post(
                    scope["source_url"] + "/withdrawals",
                    json={
                        "expected_revision_number": 1,
                        "reason": "Synthetic original withdrawn",
                    },
                )
                assert response.status_code == 409
                withdrawn = await post(
                    client,
                    scope["source_url"] + "/withdrawals",
                    {
                        "expected_revision_number": 2,
                        "reason": "Synthetic original withdrawn",
                    },
                    status=200,
                )
                assert "PRODUCT_LISTING_TERMS_WITHDRAWN" in withdrawn["reasons"]
                restored = await post(client, scope["source_url"] + "/imports", body)
                assert restored["status"] == "AVAILABLE" and restored["revision_number"] == 4
                product = (await client.get(f"/api/v1/warrants/{scope['product']['id']}")).json()
                await post(
                    client,
                    f"/api/v1/warrants/{product['id']}/terms",
                    {
                        "expected_version": product["version"],
                        "option_direction": "CALL",
                        "strike": "100",
                        "maturity_date": (scope["term"] + timedelta(days=1)).isoformat(),
                        "ratio": "0.1",
                    },
                )
                before_reads = await _state(engine)
                source = (await client.get(scope["source_url"] + "/current")).json()
                choice = (await client.get(scope["choice_url"])).json()
                assert source["status"] == choice["status"] == "UNSUITABLE"
                assert "PRODUCT_LISTING_TERMS_BINDING_CHANGED" in source["reasons"]
                assert "PRODUCT_EXIT_TERMS_CHANGED" in choice["reasons"]
                assert await _state(engine) == before_reads
        finally:
            await engine.dispose()

    asyncio.run(exercise())
