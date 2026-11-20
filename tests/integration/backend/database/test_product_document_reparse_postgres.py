"""Real PostgreSQL parser upgrades reuse immutable synthetic originals without HTTP.

The guarded fixture creates a UUID-isolated database with the actual migrations.
Economic facts use their registered API writers; only the prior document and its
operational acquisition budget are seeded as the pre-upgrade persisted state.
"""

import asyncio
import hashlib
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from tests.integration.backend.database import test_saved_quote_evidence_postgres as saved
from tests.integration.backend.database.test_product_price_scale_evidence_postgres import engine_for
from tests.integration.backend.test_realized_gross_report_postgres import (
    DECLARATION,
    _client,
    _state,
)
from tests.integration.backend.test_trade_capture_safety import BASE, WORKSPACE, purchase
from tests.integration.backend.test_usd_chf_currency_references import _migrate
from tests.unit.backend.providers.product_review_document_fixture import synthetic_kid_pdf

from app.features.product.domain.price_scale_evidence import ProductPriceScaleBinding
from app.features.product.persistence.review_evidence import (
    ProductReviewAcquisitionModel,
    ProductReviewDocumentModel,
)
from app.features.product.service.review_acquisition import ProductReviewReadiness
from app.features.product.service.review_evidence import BINDING, ProductReviewEvidenceReader
from app.providers.product_review_documents import PARSER_VERSION

quote_database = saved.quote_database
forbid_outbound_http = saved.forbid_outbound_http
ISIN, UNDERLYING_ISIN = "DE000TEST124", "US00SYNTH011"
END, PAYMENT = date(2031, 5, 16), date(2031, 5, 23)
SOURCE = f"https://kid.bnpparibas.com/{ISIN}_DE.pdf"
DOCUMENTS = "product_review_documents"
BUDGET = "product_review_acquisition"


async def post(client, path, payload):
    response = await client.post(path, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def open_position(client):
    response = await client.get("/api/v1/market-reference-data/trading-venues")
    assert response.status_code == 200, response.text
    venue = next(row for row in response.json()["items"] if row["mic"] == "XETR")
    issuer = await post(
        client,
        "/api/v1/market-reference-data/issuers",
        {"legal_name": "BNP Paribas", "display_name": "Synthetic parser upgrade issuer"},
    )
    underlying = await post(
        client,
        "/api/v1/underlyings",
        {
            "name": "Synthetic parser upgrade underlying",
            "type": "STOCK",
            "isin": UNDERLYING_ISIN,
            "primary_listing": {
                "trading_venue_id": venue["id"],
                "ticker": "SYNTHREPARSE",
                "currency_code": "EUR",
            },
        },
    )
    product = await post(
        client,
        "/api/v1/warrants",
        {
            "issuer_id": issuer["id"],
            "underlying_id": underlying["id"],
            "display_name": "Synthetic original parser upgrade",
            "isin": ISIN,
            "option_direction": "CALL",
            "strike": "100",
            "maturity_date": PAYMENT.isoformat(),
            "ratio": "0.1",
        },
    )
    capture = await post(
        client,
        BASE + "/purchases/external",
        {**purchase(product["id"]), "currency_confirmation": DECLARATION},
    )
    response = await client.get(f"/api/v1/warrants/{product['id']}/terms")
    assert response.status_code == 200, response.text
    terms = response.json()
    assert len(terms) == 1
    return product, capture, terms


@pytest.mark.parametrize("concurrent", [False, True], ids=["sequential", "concurrent"])
def test_readiness_reparses_saved_original_once_without_changing_budget_or_history(
    quote_database, concurrent
):
    _migrate(quote_database, "head")

    async def exercise():
        engine = engine_for(quote_database)
        try:
            async with _client(quote_database) as (client, database):
                product, capture, terms = await open_position(client)
                workspace = UUID(WORKSPACE)
                warrant = UUID(product["id"])
                terms_id = UUID(terms[0]["id"])
                recorded_at = datetime.now(UTC)
                original = synthetic_kid_pdf(
                    f"Synthetisches Basisinformationsblatt Optionsschein {ISIN} "
                    f"Basiswert {UNDERLYING_ISIN} Währung des Produkts: EUR "
                    "Kursnotierung: Stücknotiz Referenzstelle: New York Stock Exchange "
                    f"Bewertungstag Der Ausübungstag bzw. der {END:%d.%m.%Y} "
                    f"Fälligkeitstag {PAYMENT:%d.%m.%Y}"
                )
                legacy_facts = {
                    "isin": ISIN,
                    "underlying_isin": UNDERLYING_ISIN,
                    "currency": "EUR",
                    "unit": "CURRENCY_PER_WARRANT",
                    "reference_venue_mic": "XNYS",
                    "maturity_on": END.isoformat(),
                    "last_trading_on": None,
                    "last_trading_venue_mic": None,
                    "issues": ["PRODUCT_DOCUMENT_CURRENT_TERMS_MISMATCH"],
                }
                async with database.session_context() as session:
                    session.add(
                        ProductReviewDocumentModel(
                            id=uuid4(),
                            workspace_id=workspace,
                            warrant_id=warrant,
                            terms_id=terms_id,
                            kind="KID",
                            revision_number=1,
                            recorded_at=recorded_at,
                            retrieved_at=recorded_at - timedelta(hours=3),
                            source_reference=SOURCE,
                            document_sha256=hashlib.sha256(original).hexdigest(),
                            document=original,
                            binding=BINDING.dump_python(
                                ProductPriceScaleBinding(
                                    warrant,
                                    ISIN,
                                    UUID(product["issuer_id"]),
                                    UUID(product["underlying_id"]),
                                    terms_id,
                                ),
                                mode="json",
                            ),
                            facts=legacy_facts,
                            parser_version="current-product-document-v1",
                        )
                    )
                    session.add(
                        ProductReviewAcquisitionModel(
                            workspace_id=workspace,
                            warrant_id=warrant,
                            attempted_at=recorded_at,
                            next_attempt_at=recorded_at + timedelta(hours=24),
                            outcome="REVIEW_READINESS_PARTIAL",
                            problems=["XSTU:REVIEW_CALENDAR_ACQUISITION_FAILED"],
                        )
                    )
                    await session.commit()

                async def read(known_at):
                    async with database.session_context() as session:
                        return await ProductReviewEvidenceReader(session).current_for_review(
                            workspace_id=workspace, warrant_id=warrant, known_at=known_at
                        )

                legacy = await read(recorded_at)
                assert legacy.status == "UNSUITABLE"
                assert legacy.reasons == ("PRODUCT_DOCUMENT_CURRENT_TERMS_MISMATCH",)
                assert legacy.maturity_on == END
                before = await _state(engine)
                assert len(before[DOCUMENTS]) == len(before[BUDGET]) == 1

                arguments = {
                    "workspace_id": workspace,
                    "trade_id": UUID(capture["trade"]["id"]),
                    "position_id": UUID(capture["position"]["id"]),
                }
                # Separate instances bypass the per-instance asyncio lock. The
                # concurrent case exercises the real database product lock.
                first, second = ProductReviewReadiness(database), ProductReviewReadiness(database)
                if concurrent:
                    await asyncio.gather(
                        first.prepare_for_review(**arguments),
                        second.prepare_for_review(**arguments),
                    )
                else:
                    await first.prepare_for_review(**arguments)
                    await second.prepare_for_review(**arguments)

                after = await _state(engine)
                assert {key: rows for key, rows in after.items() if key != DOCUMENTS} == {
                    key: rows for key, rows in before.items() if key != DOCUMENTS
                }
                revisions = sorted(after[DOCUMENTS], key=lambda row: row["revision_number"])
                assert len(revisions) == 2
                old, current = revisions
                assert old == before[DOCUMENTS][0]
                assert old["facts"] == legacy_facts
                assert current["revision_number"] == 2
                assert current["parser_version"] == PARSER_VERSION == "current-product-document-v2"
                assert current["id"] != old["id"]
                assert current["recorded_at"] > old["recorded_at"]
                changed = {"id", "revision_number", "recorded_at", "parser_version", "facts"}
                assert {key: value for key, value in current.items() if key not in changed} == {
                    key: value for key, value in old.items() if key not in changed
                }
                facts = current["facts"]
                assert facts["current_terms_date_role"] == "PAYMENT"
                assert facts["maturity_on"] == facts["product_end_on"] == END.isoformat()
                assert facts["payment_on"] == PAYMENT.isoformat()
                assert facts["maturity_on"] != facts["payment_on"]
                assert facts["issues"] == []

                available = await read(datetime.now(UTC))
                assert available.status == "AVAILABLE"
                assert available.reasons == ()
                assert available.revision_id == current["id"]
                assert available.current_terms_date_role == "PAYMENT"
                assert available.maturity_on == available.product_end_on == END
                assert available.payment_on == PAYMENT
                assert await read(recorded_at) == legacy
                response = await client.get(f"/api/v1/warrants/{warrant}/terms")
                assert response.status_code == 200, response.text
                assert response.json() == terms
                assert terms[0]["maturity_date"] == PAYMENT.isoformat()

                # A further scheduled pass is fully idempotent, including receipt
                # times and the old partial outcome / next network-attempt budget.
                await first.prepare_for_review(**arguments)
                assert await _state(engine) == after
        finally:
            await engine.dispose()

    asyncio.run(exercise())
