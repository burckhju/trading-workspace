"""Compose two current Product originals without changing KID or historical facts."""

import hashlib
from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from sqlalchemy import event
from tests.unit.backend.features.product import test_product_review_evidence_reader as kids
from tests.unit.backend.providers.product_review_document_fixture import synthetic_kid_pdf

from app.features.product.domain.listing_unit_evidence import (
    ListingUnitBinding,
    ListingUnitRead,
    ListingUnitRoute,
    ListingUnitRuleSource,
)
from app.features.product.domain.price_scale_evidence import ProductPriceScaleBinding

context = kids.context
no_provider_access = kids.no_provider_access
ROUTE = ListingUnitRoute(UUID(int=1201), "GETTEX_DELAYED", "MUND", "EUR")


def kid_revision(context, *, number=1, recorded_at=kids.NOW, unit=None, **changes):
    row = kids.revision(
        context, revision_number=number, recorded_at=recorded_at, unit=unit, **changes
    )
    quotation = "Kursnotierung: Stücknotiz " if unit == "CURRENCY_PER_WARRANT" else ""
    row.document = synthetic_kid_pdf(
        f"Synthetisches Basisinformationsblatt Optionsschein {kids.ISIN} "
        f"Basiswert {kids.UNDERLYING_ISIN} Währung des Produkts: EUR "
        f"{quotation}Referenzstelle: New York Stock Exchange "
        f"Bewertungstag Der Ausübungstag bzw. der 15.01.2027 Revision {number}"
    )
    row.document_sha256 = hashlib.sha256(row.document).hexdigest()
    context.sql.commit()
    return row


def current_listing_evidence(kid):
    product = ProductPriceScaleBinding(
        kids.WARRANT, kids.ISIN, kids.ISSUER, kids.UNDERLYING, kids.TERMS
    )
    return ListingUnitRead(
        workspace_id=kids.WORKSPACE,
        warrant_id=kids.WARRANT,
        route=ROUTE,
        known_at=kids.NOW,
        event_at=kids.NOW,
        status="AVAILABLE",
        reasons=(),
        revision_id=UUID(int=1301),
        revision_number=1,
        recorded_at=kids.NOW,
        binding=ListingUnitBinding(product, ROUTE, 1, UUID(int=1401), 1),
        unit="CURRENCY_PER_WARRANT",
        currency="EUR",
        product_class="CALL_WARRANT_ON_EQUITY",
        imported_kid_revision_id=kid.id,
        imported_kid_document_sha256=kid.document_sha256,
        current_kid_revision_id=kid.id,
        rule_set_version="synthetic-unit-composition-v1",
        rule_sources=(
            ListingUnitRuleSource(
                "EXCHANGE_RULES",
                "https://example.invalid/synthetic-exchange-rules.pdf",
                "a" * 64,
                kids.NOW - timedelta(hours=1),
            ),
        ),
        pretrade_file_name="pretrade.20261118.16.00.mund.csv.gz",
        pretrade_file_sha256="b" * 64,
        pretrade_row_sha256="c" * 64,
        pretrade_observed_at=kids.NOW - timedelta(minutes=5),
        fingerprint="d" * 64,
    )


@pytest.fixture
def listing_owner(monkeypatch):
    from app.features.product.service.listing_unit_evidence import ListingUnitEvidenceReader

    owner = SimpleNamespace(value=None, calls=[])

    async def current(_self, *, workspace_id, warrant_id, route, known_at, event_at=None):
        owner.calls.append(
            {
                "workspace_id": workspace_id,
                "warrant_id": warrant_id,
                "route": route,
                "known_at": known_at,
                "event_at": event_at,
            }
        )
        assert owner.value is not None
        return replace(owner.value, known_at=known_at, event_at=event_at or known_at)

    monkeypatch.setattr(ListingUnitEvidenceReader, "current", current)
    return owner


async def combined(context, *, now=kids.NOW, route=ROUTE, event_at=None):
    return await context.reader.current_for_review(
        workspace_id=kids.WORKSPACE,
        warrant_id=kids.WARRANT,
        known_at=now,
        listing_unit_route=route,
        listing_unit_event_at=event_at,
    )


@pytest.mark.asyncio
async def test_missing_kid_unit_can_use_a_separate_current_listing_original(context, listing_owner):
    kid = kid_revision(context)
    before = (kid.document, kid.document_sha256, deepcopy(kid.facts), kid.retrieved_at)
    listing_owner.value = current_listing_evidence(kid)
    quote_at = kids.NOW - timedelta(minutes=2)

    report = await combined(context, event_at=quote_at)

    assert report.status == "AVAILABLE" and report.reasons == ()
    assert report.unit == "CURRENCY_PER_WARRANT" and report.currency == "EUR"
    assert report.unit_source_kind == "LISTING_ORIGINAL"
    assert report.quality == "CURRENT_UNIT_HISTORY_ASSUMED"
    assert report.revision_id == kid.id
    assert report.source_document_sha256 == kid.document_sha256
    assert report.listing_unit_evidence.revision_id == listing_owner.value.revision_id
    assert report.listing_unit_evidence.imported_kid_revision_id == kid.id
    assert listing_owner.calls == [
        {
            "workspace_id": kids.WORKSPACE,
            "warrant_id": kids.WARRANT,
            "route": ROUTE,
            "known_at": kids.NOW,
            "event_at": quote_at,
        }
    ]
    assert (kid.document, kid.document_sha256, kid.facts, kid.retrieved_at) == before
    assert kid.facts["unit"] is None
    assert report.listing_unit_evidence.recorded_at > quote_at


@pytest.mark.asyncio
async def test_ordinary_read_without_route_does_not_claim_a_listing_unit(context, listing_owner):
    kid = kid_revision(context)
    listing_owner.value = current_listing_evidence(kid)

    report = await combined(context, route=None)

    assert report.status == "MISSING" and "PRODUCT_REVIEW_UNIT_UNPROVEN" in report.reasons
    assert report.unit is None and report.unit_source_kind is None
    assert report.listing_unit_evidence is None
    assert listing_owner.calls == []


@pytest.mark.asyncio
async def test_direct_kid_unit_remains_independent_of_the_new_source(context, listing_owner):
    kid = kid_revision(context, unit="CURRENCY_PER_WARRANT")
    listing_owner.value = replace(
        current_listing_evidence(kid),
        status="UNSUITABLE",
        reasons=("SYNTHETIC_LISTING_ORIGINAL_CORRUPT",),
    )

    report = await combined(context)

    assert report.status == "AVAILABLE" and report.reasons == ()
    assert report.unit_source_kind == "KID_ORIGINAL"
    assert report.revision_id == kid.id and report.listing_unit_evidence is None
    assert listing_owner.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("changes", "status", "reason"),
    [
        ({"currency": None}, "MISSING", "PRODUCT_REVIEW_CURRENCY_UNPROVEN"),
        (
            {"underlying_isin": None, "issues": ("PRODUCT_DOCUMENT_UNDERLYING_AMBIGUOUS",)},
            "MISSING",
            "PRODUCT_DOCUMENT_UNDERLYING_AMBIGUOUS",
        ),
        (
            {"issues": ("PRODUCT_DOCUMENT_CURRENT_TERMS_MISMATCH",)},
            "UNSUITABLE",
            "PRODUCT_DOCUMENT_CURRENT_TERMS_MISMATCH",
        ),
        (
            {"issues": ("PRODUCT_DOCUMENT_UNDERLYING_MISMATCH",)},
            "UNSUITABLE",
            "PRODUCT_DOCUMENT_UNDERLYING_MISMATCH",
        ),
    ],
)
async def test_listing_unit_cannot_remove_other_current_kid_problems(
    context, listing_owner, changes, status, reason
):
    kid = kid_revision(context, **changes)
    listing_owner.value = current_listing_evidence(kid)

    report = await combined(context)

    assert report.status == status and reason in report.reasons
    assert report.revision_id == kid.id


@pytest.mark.asyncio
async def test_missing_or_corrupt_kid_never_becomes_qualified_by_listing_only(
    context, listing_owner
):
    missing = await combined(context)
    assert missing.status == "MISSING"
    assert "PRODUCT_REVIEW_DOCUMENT_MISSING" in missing.reasons
    assert listing_owner.calls == []

    kid = kid_revision(context)
    listing_owner.value = current_listing_evidence(kid)
    kid.document += b"synthetic-corruption"
    context.sql.commit()
    corrupt = await combined(context)
    assert corrupt.status == "UNSUITABLE"
    assert "PRODUCT_REVIEW_DOCUMENT_CORRUPT" in corrupt.reasons
    assert listing_owner.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["MISSING", "UNSUITABLE"])
async def test_unusable_listing_evidence_retains_the_precise_source_problem(
    context, listing_owner, status
):
    kid = kid_revision(context)
    reason = f"SYNTHETIC_LISTING_ORIGINAL_{status}"
    listing_owner.value = replace(
        current_listing_evidence(kid), status=status, reasons=(reason,), unit=None
    )

    report = await combined(context)

    assert report.status != "AVAILABLE" and report.unit is None
    assert report.listing_unit_evidence.status == status
    assert reason in report.listing_unit_evidence.reasons
    assert "PRODUCT_REVIEW_UNIT_UNPROVEN" in report.reasons


@pytest.mark.asyncio
async def test_daily_kid_rotation_keeps_the_listing_revision_and_both_provenances(
    context, listing_owner
):
    original_kid = kid_revision(context)
    listing_owner.value = current_listing_evidence(original_kid)
    before = await combined(context)
    later = kids.NOW + timedelta(days=1)
    current_kid = kid_revision(context, number=2, recorded_at=later)
    listing_owner.value = replace(listing_owner.value, current_kid_revision_id=current_kid.id)

    after = await combined(context, now=later)

    assert after.status == "AVAILABLE" and after.unit_source_kind == "LISTING_ORIGINAL"
    assert after.revision_id == current_kid.id != original_kid.id
    assert after.source_document_sha256 == current_kid.document_sha256
    assert after.listing_unit_evidence.revision_id == before.listing_unit_evidence.revision_id
    assert after.listing_unit_evidence.imported_kid_revision_id == original_kid.id
    assert after.listing_unit_evidence.imported_kid_document_sha256 == original_kid.document_sha256
    assert after.listing_unit_evidence.current_kid_revision_id == current_kid.id
    assert before.fingerprint != after.fingerprint
    assert original_kid.facts["unit"] is current_kid.facts["unit"] is None


@pytest.mark.asyncio
async def test_fingerprint_changes_with_evidence_but_not_with_a_reading_clock(
    context, listing_owner
):
    kid = kid_revision(context)
    listing_owner.value = current_listing_evidence(kid)
    first = await combined(context)
    later = await combined(context, now=kids.NOW + timedelta(minutes=1))
    assert first.fingerprint == later.fingerprint
    listing_owner.value = replace(
        listing_owner.value,
        revision_id=UUID(int=1302),
        revision_number=2,
        fingerprint="e" * 64,
    )
    changed = await combined(context, now=kids.NOW + timedelta(minutes=1))
    assert changed.fingerprint != first.fingerprint


@pytest.mark.asyncio
async def test_composed_current_read_preserves_passive_owner_boundary(context, listing_owner):
    kid = kid_revision(context)
    listing_owner.value = current_listing_evidence(kid)
    context.warrant.display_name = "Pending synthetic owner edit"
    flushes = []
    event.listen(context.sql, "before_flush", lambda *_args: flushes.append(True))
    context.session.flush = AsyncMock(side_effect=AssertionError("Read must not flush"))

    report = await combined(context)

    assert report.status == "AVAILABLE"
    assert flushes == [] and context.warrant in context.sql.dirty
    context.session.flush.assert_not_awaited()
    context.session.commit.assert_not_awaited()
    context.session.add.assert_not_called()
