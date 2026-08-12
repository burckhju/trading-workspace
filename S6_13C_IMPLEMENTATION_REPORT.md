# S6-13c Implementation Report – Deterministic E2E Request Tracking

## Scope

Hardening of FT-007 Playwright tests after S6-13b revealed that `page.waitForResponse()` URL heuristics were timing out despite mocked route handling.

## Changes

- Replaced lifecycle `waitForResponse()` checks with deterministic request counters maintained inside the existing `page.route()` handlers.
- Added `expect.poll()` assertions for submit-review and approve request captures before validating UI state.
- Replaced detail/history `waitForResponse()` checks in the amendment scenario with deterministic GET counters in the route handler.
- Kept exact request payload assertions and visible UI-state assertions unchanged.
- No backend/domain/API production behavior changed.

## Expected gate

Run `./scripts/run-e2e.sh`. Target: 8/8 Playwright E2E tests passing.
