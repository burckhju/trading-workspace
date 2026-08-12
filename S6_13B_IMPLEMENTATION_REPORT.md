# S6-13b Implementation Report – E2E Contract Hardening

## Scope

Hardening of FT-007 Playwright E2E assertions after the second integration run.

## Changes

- Replaced invalid Playwright `page.getAllByText(...)` usage with `page.getByText(...).first()`.
- Manual lifecycle flow now asserts the actual `submit-review` and `approve` HTTP responses before asserting UI state.
- Lifecycle UI assertions use stable visible status text plus action enablement rather than depending on heading-role matching.
- Amendment reload now explicitly waits for and validates both detail and version-history GET responses before asserting rendered lineage.
- Backend/API routes and production domain behavior remain unchanged.

## Gate status

Requires execution in the repository E2E environment:

```bash
./scripts/run-e2e.sh
```

Expected target: 8/8 Playwright E2E tests passing.
