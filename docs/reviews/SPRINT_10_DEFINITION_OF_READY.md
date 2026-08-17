# Sprint 10 – Definition of Ready Review

## Result
PASS – FT-010 specification is ready for explicit implementation approval.

This PASS means fachliche and architectural readiness only. It does not authorize production implementation by itself.

## Confirmed baseline

- `main == origin/main == 0c8ef40e2ea4c36d584e9a98772350bbcb840cb4`
- release tag `v1.1.0-trade-position` points to the baseline
- Alembic head at review start: `20260817_0014`
- FT-009 is the released upstream contract
- known local non-Sprint files/changes remain outside Sprint 10 scope

## Confirmed scope
FT-010 V1 includes:

- evolution of ExecutionRecord to `BUY | SELL`,
- actual SELL capture,
- LONG-only over-sell validation,
- derived partial/full exit,
- deterministic Position projection from effective execution history,
- closed Position/Trade representation,
- Average Cost Method,
- realized gross P&L before fees/commissions/taxes,
- immutable execution correction/effectiveness completion,
- immutable TradeManagementEvent history,
- V1 management types `STOP_CHANGED`, `TARGET_CHANGED`, `THESIS_UPDATED`, `MANAGEMENT_NOTE`,
- REST/API/frontend workflows necessary for these user actions,
- FT-011 handoff contract after full exit.

## Confirmed user workflow

For a sale the user normally enters only:

- quantity sold,
- actual average sale price per unit,
- execution time only for backdating.

The system derives partial/full exit, remaining quantity, remaining cost basis, realized gross P&L and lifecycle.

For management changes the user explicitly records the changed stop/target/thesis or a note. Original planning history remains unchanged.

## Confirmed boundaries

- `Trade != ExecutionRecord != TradeManagementEvent != Position`
- BUY/SELL are actual economic executions
- stop/target/thesis/note are management history
- Position is derived state, not a second economic ledger
- TradePlanVersion/ProductSelection remain immutable historical context
- no automatic sell/hold/stop/target decision
- FT-011 starts only after a full economic exit
- FT-012 remains downstream

## Confirmed V1 rules

- execution side is `BUY | SELL`
- execution quantities remain positive and integral
- V1 remains LONG-only
- `SELL <= open_quantity_before`
- smaller sale = partial exit
- exact remaining sale = full exit
- lifecycle derives from effective execution history
- Average Cost Method is the only V1 cost-basis method
- realized P&L is gross before fees/commissions/taxes
- correction preserves original historical records
- materialized Position must equal deterministic reconstruction

## Confirmed V1 non-scope

- SHORT trading
- product change/product substitution
- automatic trading decisions
- automatic stop/target decisions
- broker order placement
- broker order lifecycle
- individual broker fill synchronization
- depot/broker synchronization
- portfolio allocation / portfolio-risk engine
- fees
- commissions
- taxes
- transaction costs
- net P&L
- FT-011 virtual observation/Exit Review implementation
- FT-012 Journal/Performance implementation

## Cross-feature gaps explicitly accepted for implementation

### Execution side gap
Released FT-009 persistence has no BUY/SELL side. Sprint 10 must migrate historical purchase records safely to BUY semantics.

### Closed-position gap
Released FT-009 Position constraints require strictly positive quantity/cost basis. Sprint 10 must support zero open quantity after full exit.

### Effective-history/correction gap
Released FT-009 specification requires effective-history reconstruction, while the implementation currently lacks complete persisted supersession/effective-history querying. Sprint 10 must close this gap without weakening historical immutability.

### Projection gap
Released FT-009 can incrementally apply additional purchases. Sprint 10 must centralize deterministic projection so BUY, SELL and correction sequences rebuild to the same materialized state.

### TradeManagementEvent gap
Trade Event ownership is assigned to FT-010 but has no released technical implementation. Sprint 10 introduces it without creating duplicate economic truth.

## Accepted ADRs

1. `ADR-S10-001-EXECUTION-SIDE-AND-SELL-EVOLUTION.md`
2. `ADR-S10-002-EFFECTIVE-EXECUTION-HISTORY-AND-POSITION-PROJECTION.md`
3. `ADR-S10-003-PARTIAL-FULL-EXIT-AND-LONG-ONLY-LIFECYCLE.md`
4. `ADR-S10-004-AVERAGE-COST-AND-GROSS-REALIZED-PNL.md`
5. `ADR-S10-005-TRADE-MANAGEMENT-EVENT-BOUNDARY.md`
6. `ADR-S10-006-CLOSED-POSITION-REPRESENTATION.md`
7. `ADR-S10-007-EXECUTION-AND-MANAGEMENT-CORRECTIONS.md`

## Required implementation units after approval

1. Execution side evolution and backward-compatible migration
2. Effective execution repository/effectiveness model
3. Deterministic Position projector and closed-state model
4. SELL / partial / full exit application use cases
5. TradeManagementEvent domain, persistence and service layer
6. Stop / target / thesis / management-note use cases
7. REST read/write contracts and composition timeline
8. Frontend active-trade management workflows
9. Regression, unit, integration and browser E2E coverage
10. Traceability, architecture review, technical closeout and release readiness

## Required test invariants
Implementation must prove at least:

- released FT-009 BUY behavior remains regression-equivalent,
- all migrated historical executions are BUY,
- BUY/BUY projection preserves weighted average entry,
- BUY/SELL partial exit computes remaining quantity/cost basis correctly,
- full exit produces zero quantity and CLOSED state,
- over-sell fails closed,
- no negative Position is possible,
- realized gross P&L follows Average Cost Method,
- projection rebuild equals materialized Position,
- corrected execution excludes superseded fact from current projection while retaining audit history,
- stop/target/thesis management does not mutate TradePlanVersion,
- timeline composition does not persist duplicate sale truth,
- FT-011 eligibility is false for partial exit and true after full exit,
- provider/broker unavailability does not block historical execution capture.

## Implementation gate
The Sprint 10 fachliche specification and DoR are complete. Production code must not begin until the user explicitly approves implementation.
