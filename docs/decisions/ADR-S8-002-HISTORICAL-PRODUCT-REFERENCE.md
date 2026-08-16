# ADR-S8-002 – Historical Product Reference

## Status
Accepted for Sprint 8 after S8-00 review.

## Decision
A ProductEvaluation identifies the evaluated instrument context by `warrant_id`, the exact `warrant_terms_version_id`, and the concrete `warrant_listing_id`.

FT-008 does not copy or redefine FT-004 product identity. Historical evaluation and selection records retain these exact references and must not be reinterpreted using later current terms or another listing.

## User impact
A historical selection continues to mean the product, terms and tradable listing that were actually evaluated at the time, even after reference data changes.
