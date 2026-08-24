# Post-FT-012 External Observation – Definition of Ready

## Decision
Variant A is approved: clean rows are handled automatically; ambiguous/incomplete rows enter a user review queue.

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
- [x] test strategy defined at contract level

## Still required before source-specific parser production code
- [ ] representative Hebeltrader source file(s) available
- [ ] actual columns, encodings, delimiters and date/number formats inspected
- [ ] source identifiers mapped to released reference-data contracts
- [ ] historical source-time fields separated from later outcome fields
- [ ] representative clean, ambiguous and invalid rows captured as test fixtures

## Implementation slices
1. Source-neutral import/review application contracts over existing FT-012 persistence.
2. Hebeltrader adapter after real samples are available.
3. Frontend import summary and exception-only review queue.
4. PostgreSQL integration, frontend tests and E2E acceptance.

## Test invariants
- import never creates a Trade;
- unresolved identity never becomes an accepted observation silently;
- raw source payload and import provenance remain recoverable;
- correction creates a new observation version rather than mutating history;
- external evidence cannot directly mutate model versions.
