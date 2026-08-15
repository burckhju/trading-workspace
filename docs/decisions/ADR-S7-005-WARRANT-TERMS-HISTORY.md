# ADR-S7-005 – Warrant Terms History and Ratio Semantics

## Status
Accepted for Sprint 7C after S7C-00 review.

## Decision
Contractual terms that can be corrected or adjusted are versioned separately from Warrant identity. `WarrantTermsVersion` is effective-dated and immutable after creation.

V1 terms are: option direction, strike, maturity date and ratio. Ratio means **units of underlying represented by one warrant**. Therefore `ratio = 0.1` means ten warrants represent one unit of the underlying. Ratio must be greater than zero; strike must be non-negative.

Creating a new terms version closes the previous open version immediately before the new version becomes effective. Corporate-action processing itself is outside FT-004.

## Consequences
Historical product selections can later retain the exact terms context that was valid at selection time. No corporate-action engine is introduced.

## User impact
Changing strike or ratio is a versioned action rather than an in-place edit. Users gain a visible history and cannot accidentally rewrite the meaning of past selections or trades.
