# Post-D01 Golden Path Extension 02 – Candidate to TradePlan Handoff

## Purpose

This stabilization slice extends the post-D01 qualification by one released cross-feature seam:

`Candidate Qualification -> explicit planning handoff -> TradePlan -> TradePlanVersion`

It does not add a new product capability and does not change Candidate or TradePlan business rules.

## Qualified handoff

The deterministic integration contract proves that a LONG candidate which is `QUALIFIED` and has reached the user lifecycle state `READY_FOR_PLANNING` can be handed explicitly into FT-007 as a candidate-originated TradePlan.

The TradePlan keeps:

- the same workspace;
- the same underlying resolved by the released FT-007 origin gateway;
- the exact candidate ID;
- the exact immutable CandidateEvaluation ID selected at handoff time;
- `CANDIDATE_EVALUATION` as origin type;
- a first immutable TradePlanVersion in `DRAFT`.

A later CandidateEvaluation is represented by a distinct immutable ID and does not mutate or redirect the existing TradePlan provenance.

## Boundary

`READY_FOR_PLANNING` remains a process/lifecycle signal, not automatic approval and not an automatic TradePlan creation trigger. FT-007 continues to require an explicit create action.

This slice therefore does not introduce:

- automatic TradePlan creation;
- TradePlan approval;
- Product Selection;
- position sizing;
- execution;
- model activation;
- new orchestration or persistence rules.

## Why this seam

The previous post-D01 stabilization closed the MarketReference/MDI analysis seam into Candidate Qualification. The next documented integration-confidence gap was Candidate Qualification to TradePlan. FT-007 already exposes the natural handoff contract through a concrete CandidateEvaluation reference, so no synthetic domain object or new workflow service is necessary.

## Determinism and CI

The integration test uses released domain qualification behavior and the released FT-007 application service with deterministic in-memory boundary doubles. No provider network access, live credentials, migrations, or external service calls are required.

## Definition of Done

This slice is complete when:

- the candidate-to-TradePlan integration test is in the regular backend suite;
- the exact CandidateEvaluation provenance is pinned and verified;
- later re-evaluation cannot be mistaken for the selected TradePlan origin;
- Ruff, Black, mypy and backend coverage gates pass;
- unaffected frontend and Playwright gates remain green on the same PR head;
- no unrelated product or architecture change is mixed into the slice.

## Next seam

After qualification of this slice, the next natural golden-path candidate is:

`Approved TradePlanVersion -> Product Selection`

That seam should be reviewed separately before implementation because Product Selection has its own approval and product-neutrality boundaries.
