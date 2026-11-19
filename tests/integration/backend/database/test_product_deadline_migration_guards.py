"""0060 database guards in generated, disposable synthetic PostgreSQL only.

The existing guarded fixture checks the parent database before creating a UUID
database. HTTP transports are blocked, and all setup uses synthetic originals
and the real owners. Rejected statements must leave the whole database intact.
"""

import asyncio
import base64
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from tests.integration.backend.database import test_saved_quote_evidence_postgres as saved
from tests.integration.backend.database.test_product_price_scale_evidence_postgres import engine_for
from tests.integration.backend.test_realized_gross_report_postgres import _client, _state
from tests.integration.backend.test_usd_chf_currency_references import _migrate

deadline_database = saved.quote_database
forbid_outbound_http = saved.forbid_outbound_http
CHOICES = "product_deadline_exit_choices"


async def rejected(engine, statement, parameters, message, preserved):
    # Each failing transaction is rolled back before the next assertion. CASCADE
    # on TRUNCATE deliberately reaches the history triggers instead of merely
    # proving that a foreign key blocks the command.
    with pytest.raises(IntegrityError, match=message):
        async with engine.begin() as connection:
            await connection.execute(statement, parameters)
    assert await _state(engine) == preserved


def test_assessment_episode_history_scope_and_gap_guards(deadline_database):
    # The composed owner fixture is imported only when this guarded PG test
    # executes; collection does not initialize the application or any database.
    from tests.integration.backend.database import test_product_deadline_review_postgres as owner

    from app.features.position_monitoring.persistence.product_deadline_review import (
        ProductDeadlineAssessmentModel,
        ProductDeadlineEpisodeModel,
    )

    _migrate(deadline_database, "head")

    async def exercise():
        engine = engine_for(deadline_database)
        try:
            async with _client(deadline_database) as (client, database):
                scope = await owner.prepare(client, database)
                first = await owner.evaluate(engine, scope)
                assert first.outcome == "WARNING_DUE"
                conflict = await owner.post(
                    client,
                    scope["source_url"] + "/imports",
                    {
                        "document_base64": base64.b64encode(
                            owner.listing_html(scope["term"], conflict=True)
                        ).decode(),
                    },
                )
                assert conflict["status"] == "UNSUITABLE"
                gap = await owner.evaluate(engine, scope)
                assert gap.outcome == "UNAVAILABLE"
                preserved = await _state(engine)
                episode = owner.active(preserved)["DEADLINE_REVIEW"]
                assert "DATA_UNAVAILABLE" in owner.active(preserved)
                assessment = next(
                    row for row in preserved[owner.ASSESSMENTS] if row["id"] == gap.assessment_id
                )
                for statement, parameters, message in (
                    (
                        "UPDATE product_deadline_assessments SET outcome='CLOSED' WHERE id=:id",
                        {"id": first.assessment_id},
                        "Product deadline assessments are append-only",
                    ),
                    (
                        "DELETE FROM product_deadline_assessments WHERE id=:id",
                        {"id": gap.assessment_id},
                        "Product deadline assessments are append-only",
                    ),
                    (
                        "TRUNCATE product_deadline_assessments CASCADE",
                        {},
                        "Product deadline "
                        "(assessments are append-only|episode history is immutable)",
                    ),
                    (
                        "UPDATE product_deadline_episodes SET event_key=:key WHERE id=:id",
                        {"id": episode["id"], "key": "f" * 64},
                        "Product deadline episode history is immutable",
                    ),
                    (
                        "DELETE FROM product_deadline_episodes WHERE id=:id",
                        {"id": episode["id"]},
                        "Product deadline episode history is immutable",
                    ),
                    (
                        "TRUNCATE product_deadline_episodes CASCADE",
                        {},
                        "Product deadline episode history is immutable",
                    ),
                ):
                    await rejected(engine, text(statement), parameters, message, preserved)
                # Neither missing inputs nor another observation of the same
                # unresolved business event may manufacture a closing record.
                for closing in (gap.assessment_id, first.assessment_id):
                    await rejected(
                        engine,
                        text(
                            "UPDATE product_deadline_episodes SET closed_at=:at, "
                            "closing_assessment_id=:closing, close_reason='SYNTHETIC_GAP' "
                            "WHERE id=:id"
                        ),
                        {"id": episode["id"], "closing": closing, "at": datetime.now(UTC)},
                        "Product deadline close requires recorded resolution",
                        preserved,
                    )
                for changes in (
                    {"workspace_id": uuid4()},
                    {"position_id": uuid4()},
                    {"rule_version": "synthetic-foreign-deadline-version"},
                    {"previous_assessment_id": uuid4()},
                ):
                    values = {
                        **assessment,
                        "id": uuid4(),
                        "previous_assessment_id": assessment["id"],
                        **changes,
                    }
                    await rejected(
                        engine,
                        ProductDeadlineAssessmentModel.__table__.insert().values(**values),
                        {},
                        "Product deadline assessment scope mismatch",
                        preserved,
                    )
                # A known predecessor cannot acquire two successors.
                await rejected(
                    engine,
                    ProductDeadlineAssessmentModel.__table__.insert().values(
                        **{
                            **assessment,
                            "id": uuid4(),
                            "previous_assessment_id": first.assessment_id,
                        }
                    ),
                    {},
                    "uq_product_deadline_successor",
                    preserved,
                )
                for changes in (
                    {"event_key": "f" * 64},
                    {"opening_assessment_id": gap.assessment_id},
                ):
                    await rejected(
                        engine,
                        ProductDeadlineEpisodeModel.__table__.insert().values(
                            **{**episode, "id": uuid4(), **changes}
                        ),
                        {},
                        "Product deadline episode scope mismatch",
                        preserved,
                    )
        finally:
            await engine.dispose()

    asyncio.run(exercise())
    with pytest.raises(AssertionError, match="Product deadline history exists"):
        _migrate(deadline_database, "20261118_0059", action="downgrade")


def test_exit_choice_history_binding_and_successor_guards(deadline_database):
    from tests.integration.backend.database import test_product_deadline_review_postgres as owner

    from app.features.product.persistence.deadline_choice import ProductDeadlineExitChoiceModel

    _migrate(deadline_database, "head")

    async def exercise():
        engine = engine_for(deadline_database)
        try:
            async with _client(deadline_database) as (client, database):
                scope = await owner.prepare(client, database, with_calendar=False)
                preserved = await _state(engine)
                original = preserved[CHOICES][0]
                for statement in (
                    "UPDATE product_deadline_exit_choices SET recorded_by=:id WHERE id=:id",
                    "DELETE FROM product_deadline_exit_choices WHERE id=:id",
                    "TRUNCATE product_deadline_exit_choices CASCADE",
                ):
                    await rejected(
                        engine,
                        text(statement),
                        {"id": original["id"]},
                        "Product exit choices are append-only",
                        preserved,
                    )
                successor = {
                    **original,
                    "id": uuid4(),
                    "previous_revision_id": original["id"],
                    "revision_number": 2,
                    "recorded_at": datetime.now(UTC),
                }
                for changes in (
                    {"workspace_id": uuid4()},
                    {"warrant_id": uuid4()},
                    {"terms_id": uuid4()},
                    {"previous_revision_id": uuid4()},
                    {"revision_number": 3},
                    {"listing_version": original["listing_version"] + 1},
                    {"venue_version": original["venue_version"] + 1},
                    {"venue_mic": "XXXX"},
                    {"quotation_currency_code": "USD"},
                    {"recorded_at": original["recorded_at"] - timedelta(seconds=1)},
                    {
                        "previous_revision_id": None,
                        "revision_number": 1,
                        "listing_id": None,
                        "listing_version": None,
                        "trading_venue_id": None,
                        "venue_mic": None,
                        "venue_version": None,
                        "quotation_currency_code": None,
                    },
                ):
                    await rejected(
                        engine,
                        ProductDeadlineExitChoiceModel.__table__.insert().values(
                            **{**successor, **changes}
                        ),
                        {},
                        "Product exit choice scope or predecessor mismatch",
                        preserved,
                    )
                withdrawal = {
                    **scope["choice_body"],
                    "listing_id": None,
                    "expected_revision_number": 1,
                    "expected_listing_version": None,
                    "expected_venue_version": None,
                }
                response = await client.put(scope["choice_url"], json=withdrawal)
                assert response.status_code == 200, response.text
                assert response.json()["selected_listing_id"] is None
                withdrawn = await _state(engine)
                assert len(withdrawn[CHOICES]) == 2
                # The chosen binding and its withdrawal remain a single chain;
                # stale callers cannot fork the first selection.
                await rejected(
                    engine,
                    ProductDeadlineExitChoiceModel.__table__.insert().values(**successor),
                    {},
                    "uq_product_deadline_exit_choice_(successor|number)",
                    withdrawn,
                )
        finally:
            await engine.dispose()

    asyncio.run(exercise())
