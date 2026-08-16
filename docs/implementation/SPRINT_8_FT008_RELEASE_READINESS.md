# Sprint 8 / FT-008 — Release Readiness

## Status

**Release candidate behavior implemented; protected E2E execution still required before release.**

FT-008 now spans domain, application, persistence, REST, provider-neutral warrant market-data contracts, explicit provider-capability fail-closed behavior, user-selection policy, and the frontend decision-support workflow.

## Closed behavior

- A ProductSelectionRun starts only from an exact `APPROVED TradePlanVersion`.
- ProductEvaluation is a reproducible system result and remains separate from ProductSelection.
- Historical evaluation retains exact Warrant, WarrantTermsVersion and WarrantListing references.
- Universe construction and eligibility are distinct and omissions/reasons remain visible.
- Market-data capability is fail-closed. Unverified warrant quote support cannot produce an eligible market-data result.
- Provider values and calculated values are labelled separately; spread is transparent calculation only, not a threshold or recommendation.
- V1 permits selection only for `ELIGIBLE`; `INELIGIBLE` and `NOT_EVALUABLE` have no normal override path.
- One explicit ProductSelection can be persisted per run; it is not inferred from evaluation order or score.
- The frontend exposes historical runs, omissions, criteria, inputs, data quality, metrics and explicit selection confirmation.

## E2E evidence added in S8-12

`tests/e2e/ft008-product-selection.spec.ts` covers two browser-level scenarios:

1. approved TradePlan handoff -> missing/unverified warrant quote -> `NOT_EVALUABLE`, visible reasons/omissions and disabled selection;
2. fixture-backed verified quote -> `ELIGIBLE` -> explicit confirmation -> one persisted user selection with rationale.

The eligible path is intentionally fixture-backed and does **not** claim live EODHD support for the released European warrant universe.

## Local quality evidence

- Backend unit tests: 381/381 PASS.
- Frontend TypeScript: PASS.
- Frontend ESLint: PASS.
- Frontend Prettier: PASS.
- Frontend Vitest: 24/24 files, 81/81 tests PASS.
- Frontend production build: PASS.
- Playwright discovery/TypeScript loading of the new FT-008 E2E spec: PASS (2 tests discovered).
- Actual Playwright browser navigation: **BLOCKED BY EXECUTION ENVIRONMENT**. The sandbox starts system Chromium but rejects navigation to the local Vite server with `net::ERR_BLOCKED_BY_ADMINISTRATOR` before application/test assertions execute.

This infrastructure block must not be reported as an E2E PASS. Protected CI or another repository-supported environment must execute the E2E suite before release.

## Operational provider dependency

A production workflow that expects live WarrantListing Bid/Ask still requires a provider capability explicitly verified for the actual FT-004 warrant universe. Current fail-closed behavior is release-safe decision-support behavior, but it will legitimately yield `NOT_EVALUABLE` where that quote capability is unavailable or unverified.

## User impact

Users can trace exactly why a product was considered, omitted, excluded or not evaluable and can document an eligible product only by an explicit confirmation action. The workflow never turns missing provider evidence into a recommendation. Until a verified live warrant quote path exists, quote-dependent products may remain not evaluable rather than receive guessed or unsupported data.

## Release gate

Do not create the FT-008 release tag until:

1. protected Backend CI passes;
2. protected Frontend CI passes;
3. protected End-to-End CI executes and passes the FT-008 scenarios;
4. migration head `20260816_0013` is verified on PostgreSQL/Alembic;
5. release documentation records the provider capability limitation accurately.

## S8-13 release validation

S8-13 rechecked the repository-defined protected quality contracts rather than weakening them to fit the execution environment.

### Repository-defined protected gates

- Backend workflow requires Ruff, Black, mypy, unit + integration tests with >=85% coverage.
- Frontend workflow requires TypeScript, ESLint, Prettier, coverage thresholds, and production build.
- End-to-End workflow requires PostgreSQL through the repository Docker Compose stack, installed Playwright Chromium, and the full Playwright smoke suite.

### Evidence available in the supplied implementation workspace

- S8-12 local backend evidence: 381/381 unit tests PASS.
- S8-12 local frontend evidence: TypeScript, ESLint, Prettier, 24/24 test files / 81/81 tests, and production build PASS.
- FT-008 Playwright specs: discovery/compilation PASS (2 scenarios).
- Browser execution remains unverified because the available sandbox blocks local browser navigation.
- PostgreSQL/Alembic runtime verification remains unverified because the available execution environment has no Docker runtime.
- This source snapshot contains no `.git` metadata, so protected GitHub CI status, branch protection, merge state, commit identity, and release-tag state cannot be verified from the snapshot itself.

### Release decision

**HOLD — do not tag/release FT-008 from this evidence alone.**

The implementation remains release-candidate ready, but release closeout requires evidence from the actual repository/CI environment:

1. protected Backend CI PASS;
2. protected Frontend CI PASS;
3. protected End-to-End CI PASS including the FT-008 scenarios;
4. PostgreSQL migration upgrade to Alembic head `20260816_0013` verified;
5. repository `main`/merge commit and release tag established only after the protected gates pass.

No quality gate is waived by S8-13.
