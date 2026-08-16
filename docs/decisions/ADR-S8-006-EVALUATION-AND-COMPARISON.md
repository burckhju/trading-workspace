# ADR-S8-006 – Product Evaluation and Comparison Semantics

## Status
Accepted for Sprint 8 after S8-00 review.

## Decision
FT-008 evaluation models are explicitly identified and versioned. Each result preserves inputs, parameters/rules, derived values, quality/missing-data state, outcome and reasons.

Provider-supplied values remain labelled provider data. FT-008 V1 does not implement Black-Scholes, an IV solver or an internal Greeks engine.

Comparison may sort or group evaluations only by explicitly approved, explainable criteria. No “best product” or automatic recommendation exists unless a future approved model defines that semantics; even then, user selection remains separate.

## User impact
The user sees why products compare differently and whether a value was calculated by Trading Workspace or supplied by a provider. Missing information remains visible instead of being replaced with opaque estimates.
