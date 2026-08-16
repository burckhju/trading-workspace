# ADR-S8-001 – Product Selection Run and Decision Boundary

## Status
Accepted for Sprint 8 after S8-00 review.

## Decision
`ProductSelectionRun` is the FT-008 aggregate root. A run references exactly one approved `TradePlanVersion` and captures one historically reproducible product-selection context.

`ProductEvaluation` is a system-produced, immutable evaluation result inside a run. `ProductSelection` is a separate explicit user decision and must never be inferred from ranking, score, eligibility or ordering.

Multiple runs may reference the same approved TradePlanVersion. A later TradePlan amendment never rewrites or carries forward an earlier run or selection.

## User impact
The user can repeat product evaluation for the same approved plan when market/product data changes. Earlier comparisons remain intact. The application never turns a high score into a user choice automatically.
