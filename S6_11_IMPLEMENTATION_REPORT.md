# S6-11 Implementation Report – TradePlan UI + Frontend Gate Bootstrap

## Scope

- Added the FT-007 TradePlan page and route.
- Added manual-origin and CandidateEvaluation-origin creation forms.
- Added thesis, LONG-only entry, invalidation/stop, first target, and plan-risk inputs.
- Added explicit lifecycle actions and version-history read-side.
- Added Candidate → concrete CandidateEvaluation → TradePlan deep-link.
- Added `scripts/bootstrap-frontend.sh` to make the pinned Node/npm + `npm ci` prerequisite explicit before `scripts/check-frontend.sh`.

## Frontend gate handling

The repository already pins Node/npm versions, package versions, and `package-lock.json`. The prior gate failure was caused by the execution environment not containing `node_modules` and not being able to complete an npm dependency installation. S6-11 does **not** weaken typecheck/lint/format/coverage/build thresholds to hide that environmental issue.

The intended reproducible sequence is now explicit:

```bash
./scripts/bootstrap-frontend.sh
./scripts/check-frontend.sh
```

In the current execution environment `npm ci` cannot complete, therefore Vitest/ESLint/Prettier/local TypeScript dependencies remain unavailable and the frontend quality gate cannot honestly be reported as green here.

## Architectural boundaries

- TradePlan remains product-neutral.
- Candidate origin does not accept an Underlying override; the backend resolves it from the exact CandidateEvaluation.
- Approval remains an explicit user action.
- No position sizing, order quantity, execution, Warrant, Issuer, leverage, spread, ratio, expiry, or product scoring UI is introduced.

## Next unit

S6-12 – Audit / Provenance UI and integration hardening, followed by integration/E2E once the frontend dependency toolchain can be installed in the execution environment.
