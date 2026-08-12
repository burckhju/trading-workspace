# S6-13a Implementation Report – FT-007 E2E Integration Fixes

## Scope

Hardening of the S6-13 FT-007 Playwright scenarios after the first real Docker-backed E2E run.

## Changes

- Lifecycle UI now applies the `TradePlanVersionResponse` returned by lifecycle mutation endpoints immediately instead of depending on a subsequent GET refresh before showing the new status.
- The local version history is updated by immutable version identity after lifecycle mutations.
- Candidate/TRIGGER E2E uses an unambiguous textbox selector for the Trigger input.
- Amendment E2E uses an exact Playwright route for the POST amendment resource; the broader TradePlan mock delegates that exact request via `route.fallback()`.
- Backend amendment route itself was verified as `/api/v1/trade-plans/{trade_plan_id}/versions/{base_version_id}/amendments` with HTTP 201.

## Verification in this environment

- Backend `compileall`: passed.
- Full npm/Playwright execution: not declared here because this packaged runtime does not contain the complete frontend dependency installation.
- Required external gate: `./scripts/run-e2e.sh` on the prepared project environment.

## Expected gate

All 8 Playwright tests should pass before S6-14 begins. No E2E assertion was weakened to hide a product failure.
