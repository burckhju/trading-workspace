from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.features.product.domain.models import (
    OptionDirection,
    Warrant,
    WarrantLifecycle,
    WarrantListing,
    WarrantTermsVersion,
)
from app.features.product_selection.domain.enums import EligibilityStatus
from app.features.product_selection.domain.models import ModelReference, ProductSelectionRun
from app.features.product_selection.service.universe import (
    DirectionEligibilityRule,
    UniverseOmissionReason,
    construct_product_universe,
    evaluate_reference_eligibility,
)
from app.features.trade_plan.domain.enums import TradePlanStatus

NOW = datetime(2026, 8, 16, 8, 0, tzinfo=UTC)
MODEL = ModelReference("FT008", "1.0.0")


def _run(workspace_id=None, underlying_id=None):
    return ProductSelectionRun(
        uuid4(),
        workspace_id or uuid4(),
        uuid4(),
        uuid4(),
        TradePlanStatus.APPROVED,
        underlying_id or uuid4(),
        NOW,
        MODEL,
        MODEL,
        MODEL,
        NOW,
        uuid4(),
    )


def _warrant(run, active=True):
    return Warrant(
        uuid4(),
        run.workspace_id,
        uuid4(),
        run.underlying_id,
        "Test Warrant",
        None,
        None,
        WarrantLifecycle.ACTIVE if active else WarrantLifecycle.INACTIVE,
        1,
        NOW,
        NOW,
    )


def _terms(
    warrant,
    direction=OptionDirection.CALL,
    maturity=None,
    effective_from=None,
    effective_to=None,
    version_no=1,
):
    return WarrantTermsVersion(
        uuid4(),
        warrant.id,
        version_no,
        effective_from or NOW - timedelta(days=10),
        effective_to,
        direction,
        Decimal("100"),
        maturity or date(2026, 12, 31),
        Decimal("0.1"),
        NOW,
    )


def _listing(run, warrant, active=True):
    return WarrantListing(
        uuid4(),
        run.workspace_id,
        warrant.id,
        uuid4(),
        "abc",
        "EUR",
        WarrantLifecycle.ACTIVE if active else WarrantLifecycle.INACTIVE,
        1,
        NOW,
        NOW,
    )


def test_universe_scopes_workspace_underlying_and_keeps_each_listing():
    run = _run()
    included = _warrant(run)
    other = _warrant(_run(workspace_id=run.workspace_id))
    a, b = _listing(run, included), _listing(run, included)
    universe = construct_product_universe(
        run=run,
        warrants=(other, included),
        terms_versions=(_terms(included), _terms(other)),
        listings=(b, a),
    )
    assert [m.warrant.id for m in universe.members] == [included.id, included.id]
    assert [str(m.listing.id) for m in universe.members] == sorted([str(a.id), str(b.id)])


def test_universe_resolves_exact_effective_terms_at_run_time():
    run = _run()
    w = _warrant(run)
    old = _terms(w, effective_from=NOW - timedelta(days=20), effective_to=NOW - timedelta(days=5))
    current = _terms(w, effective_from=NOW - timedelta(days=5), version_no=2)
    universe = construct_product_universe(
        run=run, warrants=(w,), terms_versions=(current, old), listings=(_listing(run, w),)
    )
    assert universe.members[0].terms.id == current.id


def test_universe_reports_missing_terms_and_listing():
    run = _run()
    no_terms, no_listing = _warrant(run), _warrant(run)
    universe = construct_product_universe(
        run=run, warrants=(no_terms, no_listing), terms_versions=(_terms(no_listing),), listings=()
    )
    assert {x.reason for x in universe.omissions} == {
        UniverseOmissionReason.NO_EFFECTIVE_TERMS,
        UniverseOmissionReason.NO_LISTING,
    }


def test_overlapping_terms_are_rejected():
    run = _run()
    w = _warrant(run)
    with pytest.raises(ValueError, match="Overlapping"):
        construct_product_universe(
            run=run,
            warrants=(w,),
            terms_versions=(_terms(w), _terms(w, version_no=2)),
            listings=(_listing(run, w),),
        )


def test_inactive_reference_and_matured_product_are_ineligible():
    run = _run()
    w = _warrant(run, False)
    member = construct_product_universe(
        run=run,
        warrants=(w,),
        terms_versions=(_terms(w, maturity=date(2026, 8, 15)),),
        listings=(_listing(run, w, False),),
    ).members[0]
    result = evaluate_reference_eligibility(member=member, evaluated_at=NOW)
    assert result.status is EligibilityStatus.INELIGIBLE
    assert len(result.reasons) == 3


def test_direction_is_not_evaluable_without_explicit_rule():
    run = _run()
    w = _warrant(run)
    member = construct_product_universe(
        run=run, warrants=(w,), terms_versions=(_terms(w),), listings=(_listing(run, w),)
    ).members[0]
    result = evaluate_reference_eligibility(member=member, evaluated_at=NOW)
    assert result.status is EligibilityStatus.NOT_EVALUABLE
    assert result.reasons == ("Direction compatibility model rule is not approved/configured",)


def test_explicit_direction_rule_controls_eligibility():
    run = _run()
    w = _warrant(run)
    member = construct_product_universe(
        run=run, warrants=(w,), terms_versions=(_terms(w),), listings=(_listing(run, w),)
    ).members[0]
    call = DirectionEligibilityRule(frozenset({OptionDirection.CALL}), "LONG_CALL_V1")
    put = DirectionEligibilityRule(frozenset({OptionDirection.PUT}), "LONG_PUT_V1")
    assert (
        evaluate_reference_eligibility(member=member, evaluated_at=NOW, direction_rule=call).status
        is EligibilityStatus.ELIGIBLE
    )
    assert (
        evaluate_reference_eligibility(member=member, evaluated_at=NOW, direction_rule=put).status
        is EligibilityStatus.INELIGIBLE
    )
