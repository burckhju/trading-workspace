# S6-13f Implementation Report – Unified FT-007 E2E Route Dispatcher

## Scope

S6-13f removes overlapping Playwright route matchers from the FT-007 E2E suite and replaces them with one deterministic route dispatcher per scenario.

## Changes

- Added one shared regex route matcher for the external reverse-proxy contract: `/api/api/v1/trade-plans...`.
- Manual lifecycle scenario now dispatches create, detail, history, submit-review and approve inside one handler.
- CandidateEvaluation scenario uses the same unified matcher.
- Amendment scenario now dispatches amendment POST, detail GET and history GET inside one handler; the previous specific amendment route plus catch-all/fallback combination was removed.
- Existing request diagnostics remain in place for the two historically unstable scenarios.
- No backend, domain, persistence, REST production contract or frontend production behavior was changed in this unit.

## Verification status

The E2E suite must be executed in the repository runtime with:

```bash
./scripts/run-e2e.sh
```

Target gate: 8/8 Playwright E2E tests passing.
