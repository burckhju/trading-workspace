"""Versioned manual evidence: SQL persistence, identity binding and explicit unknowns."""

from datetime import timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session
from tests.unit.backend.features.market_data import test_retained_quotes as retained_tests
from tests.unit.backend.features.market_data.test_retained_quotes import (
    NOW,
)

from app.features.product.domain.models import OptionDirection
from app.features.product.persistence.models import (
    WarrantModel,
    WarrantTermsVersionModel,
    WarrantValuationEvidenceModel,
)
from app.features.product.service.errors import WarrantConcurrentModification, WarrantNotFound
from app.features.product.service.valuation_evidence import (
    ValuationEvidenceService,
    ValuationFacts,
    current_evidence,
)

context = retained_tests.context


def facts(**changes):
    return ValuationFacts.model_validate(
        dict(
            product_type="VANILLA_WARRANT",
            exercise_style="EUROPEAN",
            quanto=False,
            ratio_convention="UNDERLYING_UNITS_PER_WARRANT",
            expiry_at="2027-01-15T17:30:00+01:00",
            reviewed_at=NOW,
            document_reference="Synthetic final terms, page 2",
            note="Synthetic test evidence",
            **changes,
        )
    )


@pytest.fixture
def prepared(context):
    c = context
    for model in (WarrantTermsVersionModel, WarrantValuationEvidenceModel):
        model.__table__.create(c.database.engine)
    c.terms = uuid4()
    c.actor = uuid4()
    with Session(c.database.engine) as session:
        session.add(
            WarrantTermsVersionModel(
                id=c.terms,
                warrant_id=c.warrant,
                version_no=1,
                effective_from=NOW,
                effective_to=None,
                option_direction=OptionDirection.CALL,
                strike=100,
                strike_currency_code="EUR",
                maturity_date=facts().expiry_at.date(),
                ratio=0.1,
                created_at=NOW,
            )
        )
        session.commit()
    return c


async def record(c, **changes):
    args = dict(
        workspace_id=c.request.workspace_id,
        warrant_id=c.warrant,
        terms_id=c.terms,
        expected_version=1,
        expected_revision=0,
        facts=facts(),
        actor_id=c.actor,
        now=NOW,
    )
    args.update(changes)
    async with c.database.session_context() as session:
        return await ValuationEvidenceService(session).record(**args)


@pytest.mark.asyncio
async def test_revision_roundtrip_explicit_revocation_and_asof(prepared):
    c = prepared
    first = await record(c)
    assert first.status == "CURRENT" and first.revision == 1
    assert first.current.origin == "MANUAL_DOCUMENT_REVIEW"
    assert first.current.recorded_at == NOW
    assert first.current.actor_id == c.actor
    assert first.current.identity["isin"] == "DE000VH2LU21"
    unknown = facts().model_copy(
        update={
            "product_type": None,
            "exercise_style": None,
            "quanto": None,
            "ratio_convention": None,
            "expiry_at": None,
        }
    )
    second = await record(c, expected_revision=1, facts=unknown, now=NOW + timedelta(seconds=1))
    assert second.revision == 2 and second.current.facts.quanto is None
    assert len(second.history) == 2
    assert second.history[1].facts.quanto is False
    async with c.database.session_context() as session:
        warrant = await session.get(WarrantModel, c.warrant)
        assert warrant.version == 1  # evidence does not change the quote/stop identity
        assert (await current_evidence(session, warrant, c.terms, NOW)).revision == 1
        assert await current_evidence(session, warrant, c.terms, NOW - timedelta(seconds=1)) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["isin", "wkn", "issuer_id", "underlying_id", "terms"])
async def test_identity_changes_invalidate_latest_evidence(prepared, change):
    c = prepared
    await record(c)
    with Session(c.database.engine) as session:
        if change == "terms":
            term = session.get(WarrantTermsVersionModel, c.terms)
            term.effective_to = NOW + timedelta(seconds=1)
        else:
            warrant = session.get(WarrantModel, c.warrant)
            setattr(warrant, change, {"isin": "DE000VH4VNA6", "wkn": "VH4VNA"}.get(change, uuid4()))
        session.commit()
    async with c.database.session_context() as session:
        view = await ValuationEvidenceService(session).view(
            c.request.workspace_id, c.warrant, NOW + timedelta(seconds=2)
        )
        assert view.current is None and view.status == "IDENTITY_OR_TERMS_CHANGED"
        assert view.revision == 1 and len(view.history) == 1
        assert view.history[0].identity["isin"] == "DE000VH2LU21"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changes,exception",
    [
        ({"expected_version": 2}, WarrantConcurrentModification),
        ({"expected_revision": 1}, WarrantConcurrentModification),
        ({"terms_id": uuid4()}, WarrantConcurrentModification),
        ({"workspace_id": uuid4()}, WarrantNotFound),
        ({"now": NOW.replace(tzinfo=None)}, ValueError),
    ],
)
async def test_stale_editor_and_wrong_owner_cannot_record(prepared, changes, exception):
    with pytest.raises(exception):
        await record(prepared, **changes)


@pytest.mark.asyncio
async def test_bad_dates_no_isin_and_missing_owner(prepared):
    c = prepared
    for patch in ({"reviewed_at": NOW + timedelta(seconds=1)}, {"expiry_at": NOW}):
        with pytest.raises(ValueError):
            await record(c, facts=facts().model_copy(update=patch))
    with Session(c.database.engine) as session:
        session.get(WarrantModel, c.warrant).isin = None
        session.commit()
    with pytest.raises(ValueError, match="ISIN"):
        await record(c)
    async with c.database.session_context() as session:
        with pytest.raises(WarrantNotFound):
            await ValuationEvidenceService(session).view(uuid4(), c.warrant, NOW)
        with pytest.raises(ValueError, match="timezone"):
            await ValuationEvidenceService(session).view(
                c.request.workspace_id, c.warrant, NOW.replace(tzinfo=None)
            )


@pytest.mark.parametrize(
    "change",
    [
        {"reviewed_at": "2026-10-12T12:00:00"},
        {"expiry_at": "2027-01-15T17:30:00"},
        {"quanto": "false"},
        {"product_type": "TURBO"},
        {"document_reference": " "},
        {"source_url": "https://user:password@example.org/terms"},
        {"source_url": "file:///private/terms"},
        {"model": "unverified"},
    ],
)
def test_fact_schema_rejects_implicit_defaults_naive_times_and_secrets(change):
    data = facts().model_dump(mode="json")
    data.update(change)
    with pytest.raises(ValidationError):
        ValuationFacts.model_validate(data)


def test_unsupported_but_explicit_product_facts_can_be_documented():
    data = facts().model_dump(mode="json")
    data.update(product_type="OTHER_STRUCTURED", exercise_style="AMERICAN", quanto=True)
    assert ValuationFacts.model_validate(data).quanto is True
    for field in ("product_type", "quanto", "expiry_at"):
        partial = dict(data)
        del partial[field]
        with pytest.raises(ValidationError):
            ValuationFacts.model_validate(partial)


@pytest.mark.asyncio
async def test_risk_reader_uses_only_evidence_existing_at_evaluation_time(prepared):
    from app.features.product.service.risk_reference import RiskProductReader

    c = prepared
    await record(c, now=NOW + timedelta(seconds=1))
    async with c.database.session_context() as session:
        reader = RiskProductReader(session)
        old = await reader.read(
            workspace_id=c.request.workspace_id, warrant_id=c.warrant, as_of=NOW
        )
        current = await reader.read(
            workspace_id=c.request.workspace_id,
            warrant_id=c.warrant,
            as_of=NOW + timedelta(seconds=1),
        )
        assert old.exercise_style is None and old.evidence_revision is None
        assert current.exercise_style == "EUROPEAN" and current.quanto is False
        assert (
            current.evidence_revision == 1
            and current.evidence_document == facts().document_reference
        )
        assert current.expiry_at == facts().expiry_at
        assert current.ratio == old.ratio  # document revision does not rescale the ratio
