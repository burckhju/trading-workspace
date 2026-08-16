# ADR-S8-007 – Provider Capability Resolution and V1 Selection Policy

## Status
Accepted in S8-09.

## Context
FT-008 can evaluate a WarrantListing only when its market-data capability is explicitly verified. Provider marketing or a superficially similar endpoint is not sufficient evidence that the released FT-004 warrant universe is supported.

ProductEvaluation and ProductSelection are intentionally separate. V1 therefore needs an explicit rule for whether a user may select an evaluation that the system classified as INELIGIBLE or NOT_EVALUABLE.

## Decision
1. Provider capabilities are resolved explicitly. Unknown or unverified capability is fail-closed and is not usable by FT-008.
2. EODHD `WARRANT_LISTING_QUOTE` remains `UNVERIFIED` for the actual FT-004 WarrantListing universe. The existing EODHD warrant adapter therefore continues to fail closed.
3. V1 ProductSelection may reference only an `ELIGIBLE` ProductEvaluation from the same ProductSelectionRun.
4. There is no V1 override for `INELIGIBLE` or `NOT_EVALUABLE` evaluations.
5. A future override, if required, must be a separate audited domain decision with explicit reason, actor, policy/version and user-facing warning; it must not be smuggled through the normal selection command.

## User impact
Users cannot persist a normal product selection when the product failed an eligibility rule or lacks sufficient evaluation data. This prevents an incomplete or excluded product from appearing as an ordinary valid selection. If override support is introduced later, it will be visibly distinct and auditable.

Users also do not receive quote-dependent conclusions from a provider capability that has not been verified for the actual warrant universe.
