# S6-10 Implementation Report — FT-007 Frontend API / Types

## Scope

Add the TypeScript contracts and frontend API client for the approved FT-007 REST surface. No TradePlan page, form, route or workflow UI is introduced in this unit.

## Implemented

- Added `frontend/src/features/trade_plan/types/api.ts` with the complete FT-007 REST contract:
  - product-neutral origins (`MANUAL`, `CANDIDATE_EVALUATION`);
  - LONG-only direction;
  - Entry, Invalidation, ordered Targets and Risk Assumptions;
  - immutable version response and lifecycle status;
  - exact CandidateEvaluation provenance;
  - approval proof and lifecycle events.
- Creation contracts are a discriminated union:
  - manual creation requires `underlying_id` and cannot carry Candidate provenance;
  - Candidate creation requires `candidate_id` + `candidate_evaluation_id` and cannot carry a client-supplied `underlying_id`.
- Added `tradePlanApiClient` for:
  - create;
  - latest detail;
  - version history;
  - exact version read;
  - amendment against an exact base-version ID;
  - submit for review;
  - return to draft;
  - abandon;
  - approve.
- Extended the shared HTTP transport with optional `X-Correlation-ID` propagation.
- Corrected the local fallback request identity to the UUID-shaped local actor already used by the FT-007 backend, avoiding FastAPI UUID-header validation failures in local frontend mutations.
- Added focused client tests covering origin payload boundaries, exact version paths, amendments and lifecycle command mapping.

## Invariants preserved

- Candidate-originated TradePlans cannot submit an underlying override from the frontend contract.
- The client reads and mutates exact TradePlanVersion resources; it does not resolve a latest CandidateEvaluation.
- Approval remains an explicit command against one concrete version.
- No Warrant, Issuer, Product Selection, Position Sizing, Order Quantity or Execution contract was introduced.
- S6-10 contains no TradePlan UI workflow.

## Quality gates

- Node.js `v22.16.0` and npm `10.9.2` match the repository engine requirements.
- Frontend test/typecheck/lint/format gates could not be executed in the supplied ZIP runtime because `node_modules` is absent.
- `npm ci --offline` was attempted but the local npm cache is incomplete (`yocto-queue@0.1.0` not cached); network installation is unavailable in this runtime.
- Therefore no Vitest, TypeScript, ESLint or Prettier pass is claimed for this unit.

## Next unit

S6-11 — TradePlan UI: implement the user-facing product-neutral TradePlan workflow on top of the typed S6-10 client, including origin selection, planning content, lifecycle actions, approval and version history.
