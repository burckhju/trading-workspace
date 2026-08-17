# Sprint 10 – Technical Closeout

## Scope

Sprint 10 implements FT-010 Trade Management on top of released FT-009 Trade & Position.

## Delivered capabilities

- BUY/SELL evolution of ExecutionRecord with backward-compatible historical BUY migration;
- immutable effective execution history and correction supersession;
- deterministic Position reconstruction;
- LONG-only partial and full exits;
- Average Cost remaining cost basis;
- realized gross P&L;
- zero-quantity CLOSED Position representation;
- immutable stop, target, thesis and management-note history;
- management-event corrections;
- current management-state projection;
- REST contracts for sale, management, corrections, Position, timeline and FT-011 eligibility;
- active-trade frontend workflow;
- composed timeline without duplicate sale truth;
- FT-011 eligibility only after full economic exit;
- integration and browser-E2E coverage.

## Explicit V1 boundaries

Not implemented:

- SHORT trading;
- automatic sell/hold/stop/target decisions;
- product substitution;
- broker orders, fills or synchronization;
- fees, commissions, taxes or net P&L;
- portfolio allocation/risk engine;
- FT-011 post-trade observation/review implementation;
- FT-012 journal/performance implementation.

## Persistence

Sprint 10 migrations:

- `20260817_0015` – execution side;
- `20260817_0016` – execution supersession;
- `20260817_0017` – deterministic closed-position/P&L state;
- `20260817_0018` – immutable management events.

Validated head: `20260817_0018`.

## Verification evidence

Local feature-branch evidence:

- backend FT-010 unit suite: `126 passed`;
- backend FT-010 integration scenario: `1 passed`;
- Ruff: PASS;
- frontend Vitest suite: `86 passed`;
- ESLint: PASS;
- TypeScript: PASS;
- Prettier: PASS;
- production build: PASS;
- targeted FT-010 Playwright E2E via Docker Compose/reverse proxy: `1 passed`;
- branch diff check: PASS.

## Implementation commits

Feature implementation history at closeout preparation:

- `6657dc8` – execution side foundation;
- `916bc52` – execution supersession history;
- `50f514b` – deterministic position projection;
- `06f3f3c` – sale execution use cases;
- `061097f` – management-event foundation;
- `70e90b7` – management commands and state;
- `7778df8` – trade-management REST contracts;
- `e988445` – trade-management frontend;
- `20d3733` – corrections, timeline and FT-011 handoff;
- `762cdd9` – integration and browser-E2E coverage.

Baseline: merge commit `2d6d966` containing the approved FT-010 specification.

## Delivery state

Implementation and local qualification are complete.

Not yet claimed:

- remote implementation PR;
- protected CI;
- merge to `main`;
- release tag/status.

## Closeout decision

FT-010 is technically complete for the approved Sprint 10 V1 implementation scope and may proceed to the final release-readiness gate and implementation PR.
