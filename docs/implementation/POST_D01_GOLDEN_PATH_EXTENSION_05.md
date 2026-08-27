# Post-D01 Golden Path Extension 05

## Purpose

Qualify the next released downstream seam after Product Selection -> Trade/Position:

```text
WORKSPACE_SELECTION Trade + open Position
-> user-confirmed full SELL
-> immutable SELL ExecutionRecord
-> deterministic Position reprojection
-> open_quantity = 0
-> FT-011 eligible
```

This slice proves the workspace-originated path. The existing FT-010 integration coverage already exercises the same economic close/handoff rule for an EXTERNAL trade; Extension 05 closes the provenance gap for trades created from an FT-008 ProductSelection.

## Invariants under qualification

- The full exit is an actual `SELL ExecutionRecord`, not a separate close mutation or management event.
- Closed state is derived from effective execution history.
- `open_quantity` becomes zero and remaining `cost_basis` becomes zero.
- Realized P&L remains explicitly gross before fees, commissions and taxes.
- FT-011 eligibility changes from false to true only after the full economic exit.
- Stable Trade identity is preserved.
- Historical `trade_plan_id`, `trade_plan_version_id`, `product_selection_id`, and `product_evaluation_id` remain unchanged through the exit.
- No provider, broker, quote, or live market-data dependency is required to record the historical sale.

## Scope

One deterministic backend integration test using the released FT-010 application/domain contracts. The test starts with a `WORKSPACE_SELECTION` Trade, its original BUY execution and derived open Position, records a full SELL, and verifies the resulting FT-011 eligibility and provenance invariants.

## Non-scope

- starting or refreshing an FT-011 PostTradeObservation,
- Exit Review lifecycle,
- FT-012 learning/journal handoff,
- partial exits,
- additional purchases,
- execution corrections,
- management-event workflows,
- broker order placement or synchronization,
- fees, commissions, taxes, or net P&L,
- production-code or schema changes.

## Expected qualification

The slice must pass the normal same-head repository gates. In particular, the backend run must satisfy Ruff, Black, strict mypy, Alembic upgrade, the full test suite, and the configured 85% coverage gate. Frontend and Playwright E2E remain regression gates even though this slice changes only backend tests/documentation.
