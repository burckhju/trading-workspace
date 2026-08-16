"""Deterministic FT-008 V1 product-universe construction and reference eligibility."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.features.product.domain.models import (
    OptionDirection,
    ProductFamily,
    Warrant,
    WarrantLifecycle,
    WarrantListing,
    WarrantTermsVersion,
)
from app.features.product_selection.domain.enums import (
    CriterionOutcome,
    DataAvailability,
    EligibilityStatus,
)
from app.features.product_selection.domain.models import CriterionResult, ProductSelectionRun


class UniverseOmissionReason(StrEnum):
    NO_EFFECTIVE_TERMS = "NO_EFFECTIVE_TERMS"
    NO_LISTING = "NO_LISTING"


@dataclass(frozen=True, slots=True)
class UniverseOmission:
    warrant_id: UUID
    reason: UniverseOmissionReason
    explanation: str


@dataclass(frozen=True, slots=True)
class ProductUniverseMember:
    warrant: Warrant
    terms: WarrantTermsVersion
    listing: WarrantListing


@dataclass(frozen=True, slots=True)
class ProductUniverse:
    run_id: UUID
    members: tuple[ProductUniverseMember, ...]
    omissions: tuple[UniverseOmission, ...]


@dataclass(frozen=True, slots=True)
class DirectionEligibilityRule:
    """Explicit model parameter; no LONG -> CALL default is hidden in FT-008."""

    allowed_directions: frozenset[OptionDirection]
    rule_id: str

    def __post_init__(self) -> None:
        if not self.allowed_directions:
            raise ValueError("allowed_directions must not be empty")
        if not self.rule_id.strip():
            raise ValueError("rule_id is required")


def construct_product_universe(
    *,
    run: ProductSelectionRun,
    warrants: tuple[Warrant, ...],
    terms_versions: tuple[WarrantTermsVersion, ...],
    listings: tuple[WarrantListing, ...],
) -> ProductUniverse:
    """Build the V1 universe without hiding eligibility rules in query filters."""
    terms_by_warrant: dict[UUID, list[WarrantTermsVersion]] = {}
    for terms in terms_versions:
        terms_by_warrant.setdefault(terms.warrant_id, []).append(terms)
    listings_by_warrant: dict[UUID, list[WarrantListing]] = {}
    for listing in listings:
        listings_by_warrant.setdefault(listing.warrant_id, []).append(listing)
    members: list[ProductUniverseMember] = []
    omissions: list[UniverseOmission] = []
    candidates = sorted(
        (
            w
            for w in warrants
            if w.workspace_id == run.workspace_id
            and w.underlying_id == run.underlying_id
            and w.product_family is ProductFamily.WARRANT
        ),
        key=lambda w: str(w.id),
    )
    for warrant in candidates:
        effective_terms = _effective_terms(terms_by_warrant.get(warrant.id, []), run.evaluated_at)
        if effective_terms is None:
            omissions.append(
                UniverseOmission(
                    warrant.id,
                    UniverseOmissionReason.NO_EFFECTIVE_TERMS,
                    "No WarrantTermsVersion is effective at the run evaluation time",
                )
            )
            continue
        warrant_listings = sorted(
            listings_by_warrant.get(warrant.id, []), key=lambda listing: str(listing.id)
        )
        if not warrant_listings:
            omissions.append(
                UniverseOmission(
                    warrant.id,
                    UniverseOmissionReason.NO_LISTING,
                    "Warrant has no concrete WarrantListing context",
                )
            )
            continue
        members.extend(
            ProductUniverseMember(warrant, effective_terms, listing) for listing in warrant_listings
        )
    return ProductUniverse(run.id, tuple(members), tuple(omissions))


@dataclass(frozen=True, slots=True)
class ReferenceEligibilityResult:
    member: ProductUniverseMember
    status: EligibilityStatus
    criteria: tuple[CriterionResult, ...]
    reasons: tuple[str, ...]


def evaluate_reference_eligibility(
    *,
    member: ProductUniverseMember,
    evaluated_at: datetime,
    direction_rule: DirectionEligibilityRule | None = None,
) -> ReferenceEligibilityResult:
    """Evaluate only repository-approved reference-data rules; no quote rules are implied."""
    criteria = [
        _lifecycle("warrant-lifecycle-usable", member.warrant.lifecycle_status),
        _terms_effective(member.terms, evaluated_at),
        _maturity(member.terms, evaluated_at),
        _lifecycle("listing-lifecycle-usable", member.listing.lifecycle_status),
        _direction(member.terms.option_direction, direction_rule),
    ]
    failed = [c for c in criteria if c.outcome is CriterionOutcome.NOT_FULFILLED]
    unavailable = [c for c in criteria if c.outcome is CriterionOutcome.NOT_EVALUABLE]
    if failed:
        return ReferenceEligibilityResult(
            member,
            EligibilityStatus.INELIGIBLE,
            tuple(criteria),
            tuple(c.explanation for c in failed),
        )
    if unavailable:
        return ReferenceEligibilityResult(
            member,
            EligibilityStatus.NOT_EVALUABLE,
            tuple(criteria),
            tuple(c.explanation for c in unavailable),
        )
    return ReferenceEligibilityResult(member, EligibilityStatus.ELIGIBLE, tuple(criteria), ())


def _effective_terms(
    versions: list[WarrantTermsVersion], evaluated_at: datetime
) -> WarrantTermsVersion | None:
    matches = [
        v
        for v in versions
        if v.effective_from <= evaluated_at
        and (v.effective_to is None or evaluated_at < v.effective_to)
    ]
    if not matches:
        return None
    if len(matches) > 1:
        raise ValueError("Overlapping WarrantTermsVersion records at evaluation time")
    return matches[0]


def _lifecycle(criterion_id: str, status: WarrantLifecycle) -> CriterionResult:
    usable = status is WarrantLifecycle.ACTIVE
    return CriterionResult(
        criterion_id,
        CriterionOutcome.FULFILLED if usable else CriterionOutcome.NOT_FULFILLED,
        "Reference is active" if usable else "Reference is inactive",
        status.value,
        WarrantLifecycle.ACTIVE.value,
    )


def _terms_effective(terms: WarrantTermsVersion, evaluated_at: datetime) -> CriterionResult:
    effective = terms.effective_from <= evaluated_at and (
        terms.effective_to is None or evaluated_at < terms.effective_to
    )
    return CriterionResult(
        "terms-effective",
        CriterionOutcome.FULFILLED if effective else CriterionOutcome.NOT_FULFILLED,
        (
            "Terms version is effective at evaluation time"
            if effective
            else "Terms version is not effective at evaluation time"
        ),
        str(terms.version_no),
        "effective at evaluated_at",
    )


def _maturity(terms: WarrantTermsVersion, evaluated_at: datetime) -> CriterionResult:
    valid = terms.maturity_date >= evaluated_at.date()
    return CriterionResult(
        "maturity-valid",
        CriterionOutcome.FULFILLED if valid else CriterionOutcome.NOT_FULFILLED,
        "Product has not matured" if valid else "Product is already matured",
        terms.maturity_date.isoformat(),
        f">= {evaluated_at.date().isoformat()}",
    )


def _direction(
    direction: OptionDirection, rule: DirectionEligibilityRule | None
) -> CriterionResult:
    if rule is None:
        return CriterionResult(
            "direction-compatible",
            CriterionOutcome.NOT_EVALUABLE,
            "Direction compatibility model rule is not approved/configured",
            direction.value,
            None,
            DataAvailability.INSUFFICIENT,
        )
    compatible = direction in rule.allowed_directions
    return CriterionResult(
        "direction-compatible",
        CriterionOutcome.FULFILLED if compatible else CriterionOutcome.NOT_FULFILLED,
        (
            f"Direction is {'compatible' if compatible else 'incompatible'} "
            f"with model rule {rule.rule_id}"
        ),
        direction.value,
        ",".join(sorted(item.value for item in rule.allowed_directions)),
    )
