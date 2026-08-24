# Post-FT-012 External Observation – Definition of Ready

## Decision
Variant A is approved: clean records are handled automatically; ambiguous/incomplete records enter a user review queue. Bulk upload of at least 100 PDFs is the primary workflow.

## Ready
- [x] business goal defined
- [x] why-now rationale established
- [x] scope and non-scope defined
- [x] released FT-012 consumer contracts identified
- [x] ExternalObservation/Trade provenance boundary accepted
- [x] identity-resolution policy accepted
- [x] historical outcome/evidence boundary accepted
- [x] domain ownership remains with FT-012 Learning/External Observation contracts
- [x] persistence and audit baseline exists in migration `20260820_0020`
- [x] current migration head verified as `20260824_0021`
- [x] review-queue UX selected
- [x] 100+ PDF bulk-upload requirement accepted
- [x] test strategy defined at contract level
- [x] representative Hebeltrader PDFs inspected across 09.01., 24.02., 21.04., 02.06. and 10.07.2026
- [x] stable six-page 2026 layout and core labels observed across those samples
- [x] German decimal/date formats and EUR/USD currency variants observed
- [x] core derivative and underlying extraction contract identified

## Parser findings
Across the inspected 2026 samples, pages 1–6 retain the same semantic roles: recommendation/derivative facts, leverage scenario, underlying technical facts, peer group, market context, principles/legal. Core recommendation labels remain stable enough for a label/anchor-based parser rather than fixed coordinates.

Observed data-quality exceptions prove that validation is mandatory: issue #03/2026 is dated 09.01.2026 but its page-1 price-indication footnote says 09.01.2025; issue #30/2026 contains placeholder peer-group dates `Xx.xx.26`. These values must be preserved as source facts and surfaced as validation issues rather than silently corrected.

## Still required before declaring the adapter production-stable
- [ ] source identifiers mapped against released Reference Data lookup contracts in implementation
- [ ] representative parser fixtures checked into tests without redistributing full copyrighted newsletters
- [ ] ambiguous/invalid fixture cases derived from source-safe minimal excerpts/structured fixtures
- [ ] older-year layouts sampled if the intended 100+ archive extends materially before 2026

## Implementation slices
1. Multi-file import-job aggregate above existing per-file FT-012 import batches.
2. Hebeltrader 2026 label/anchor parser and validation layer.
3. Reference-data identity resolver and exception-only review application service.
4. Frontend bulk upload, progress summary and review queue.
5. PostgreSQL integration, 100+ file load/fixture test, frontend tests and E2E acceptance.

## Test invariants
- import never creates a Trade;
- unresolved identity never becomes an accepted observation silently;
- raw source payload and import provenance remain recoverable;
- one malformed file cannot roll back successful files in the same job;
- duplicate file hashes do not create duplicate observations silently;
- source inconsistencies are reported, not auto-corrected;
- correction creates a new observation version rather than mutating history;
- external evidence cannot directly mutate model versions.
