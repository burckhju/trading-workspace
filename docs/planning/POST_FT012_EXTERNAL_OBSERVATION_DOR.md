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
- [x] current migration head verified as `20260824_0022`
- [x] review-queue UX selected
- [x] 100+ PDF bulk-upload requirement accepted
- [x] test strategy defined at contract level
- [x] representative Hebeltrader PDFs inspected across 09.01., 24.02., 21.04., 02.06. and 10.07.2026
- [x] stable six-page 2026 layout and core labels observed across those samples
- [x] German decimal/date formats and EUR/USD currency variants observed
- [x] core derivative and underlying extraction contract identified
- [x] source WKNs mapped against released Underlying/Warrant reference-data contracts
- [x] source-safe parser fixtures checked into tests
- [x] ambiguous/invalid source cases represented in validation tests
- [x] frontend bulk upload and exception review implemented
- [x] backend, frontend and E2E CI gates green before final hardening

## Parser findings
Across the inspected 2026 samples, pages 1–6 retain the same semantic roles: recommendation/derivative facts, leverage scenario, underlying technical facts, peer group, market context, principles/legal. Core recommendation labels remain stable enough for a label/anchor-based parser rather than fixed coordinates.

Observed data-quality exceptions prove that validation is mandatory: issue #03/2026 is dated 09.01.2026 but its page-1 price-indication footnote says 09.01.2025; issue #30/2026 contains placeholder peer-group dates `Xx.xx.26`. These values are preserved as source facts and surfaced as validation issues rather than silently corrected.

## Remaining compatibility note
- [ ] older-year layouts still need representative sampling if the intended archive extends materially before 2026; unsupported layouts must fail explicitly rather than be guessed.

## Implemented slices
1. Multi-file import-job aggregate above existing per-file FT-012 import batches.
2. Hebeltrader 2026 label/anchor parser and validation layer.
3. Reference-data identity resolver and exception-only review application service.
4. Frontend bulk upload, status summary and review queue.
5. PostgreSQL migration `20260824_0022`, backend/frontend tests and E2E coverage.

## Test invariants
- import never creates a Trade;
- unresolved identity never becomes an accepted observation silently;
- source payload and import provenance remain recoverable;
- one malformed file cannot roll back successful files in the same job;
- duplicate file hashes do not create duplicate observations silently;
- source inconsistencies are reported, not auto-corrected;
- external evidence cannot directly mutate model versions.
