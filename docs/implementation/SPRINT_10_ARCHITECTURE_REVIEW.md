# Sprint 10 – FT-010 Architecture Review

## Result

**ACCEPTED FOR IMPLEMENTATION PR**

The FT-010 implementation is consistent with the approved Sprint 10 feature specification and ADR package. No architecture blocker remains in the implemented V1 scope.

This review is a local pre-PR architecture assessment. It does not claim protected CI, merge, tag, or release completion.

## Reviewed boundaries

### Trade, ExecutionRecord, TradeManagementEvent and Position remain distinct

Confirmed:

- `Trade` remains the durable trade identity and provenance boundary.
- `ExecutionRecord` remains the immutable economic execution fact for both BUY and SELL.
- `TradeManagementEvent` records management decisions and contextual changes only.
- `Position` remains derived/materialized state reproducible from effective execution history.

No generic event abstraction was introduced that collapses economic and management facts.

### FT-009 is evolved rather than replaced

FT-010 extends the released FT-009 module in place:

- no parallel SaleExecution aggregate;
- no second Position aggregate;
- no replacement Trade identity;
- historical execution rows migrate to BUY semantics;
- one Position per Trade remains.

### Effective history and corrections

Execution and management corrections are append-only supersession relationships.

The original fact remains available for audit. Current Position is rebuilt from effective execution history rather than repaired through inverse mutations.

### LONG-only lifecycle

The V1 lifecycle remains execution-derived:

- open quantity greater than zero -> OPEN;
- exact full economic exit -> zero open quantity and CLOSED;
- over-sell is rejected;
- no implicit SHORT state is created.

### Cost basis and P&L

Average Cost is the single V1 cost-basis method. Realized P&L is explicitly gross before fees, commissions and taxes. Transaction-cost modeling remains outside FT-010.

### Planning and selection boundaries

FT-010 does not mutate TradePlanVersion, ProductSelection, ProductEvaluation or CandidateEvaluation. Historical provenance is consumed as context only.

### Broker/provider boundary

An actual execution is a user-confirmed aggregated fact, not an Order or broker fill.

The sale workflow has no provider/broker availability dependency. Missing live capability therefore cannot prevent historical capture of an execution that already occurred.

### Timeline boundary

The timeline is a composed read model. SELL is displayed from the authoritative ExecutionRecord and is not duplicated as an independent TradeManagementEvent.

### FT-011 boundary

FT-010 exposes only an eligibility/handoff contract:

- partial exit -> not eligible;
- full economic exit -> eligible.

No PostTradeObservation, ExitReview, Journal or Performance implementation is introduced.

## Persistence review

The Sprint 10 migration chain is linear from released FT-009 head `20260817_0014`:

`0014 -> 0015 -> 0016 -> 0017 -> 0018`

The migrations add execution side, supersession, closed-position/P&L state and management-event persistence while preserving the released aggregate boundaries.

Validated Alembic head: `20260817_0018`.

## API and UI review

The REST API extends the existing `/api/v1/trade-position` boundary.

The frontend uses a dedicated `features/trade` boundary and does not move trade-management concerns into TradePlan. User inputs remain intentionally minimal and calculated lifecycle/P&L fields remain system-derived.

## Verification considered

- 126 FT-010 backend unit tests PASS;
- 1 FT-010 backend integration scenario PASS;
- 86 frontend tests PASS;
- Ruff, ESLint, TypeScript and Prettier PASS;
- frontend production build PASS;
- 1 FT-010 Playwright scenario PASS through the repository Docker Compose/reverse-proxy harness;
- branch diff check PASS.

## Open items outside architecture acceptance

The following are delivery steps rather than architecture gaps:

- push feature branch;
- open implementation pull request;
- protected CI;
- merge;
- release-status documentation/tagging if separately approved.

## Decision

The FT-010 V1 implementation is architecture-consistent and may proceed to the implementation pull request after the final local release-readiness gate.
