# S6-06 Implementation Report – CandidateEvaluation Handoff / Provenance Integration Hardening

## Scope

S6-06 hardens the FT-005 → FT-007 handoff and introduces a persistence-backed, version-specific TradePlan read side in preparation for the REST contract. No REST routes or frontend code are added.

## Implemented

- Added `TradePlanQueryService` with exact lookup by version id and version number.
- Added immutable read-side views for approval and lifecycle events.
- Added `SqlAlchemyTradePlanProvenanceGateway` resolving the exact persisted `CandidateEvaluation` referenced by the durable `TradePlan`.
- Candidate provenance validation binds workspace, candidate, underlying and exact evaluation id; it never resolves a latest evaluation.
- Candidate evaluation source snapshots are exposed by exact source id/version without copying them into TradePlan persistence.
- Manual-originated plans return no CandidateEvaluation provenance.
- Unresolvable persisted candidate provenance fails closed instead of silently degrading.
- Existing Candidate handoff validation additionally rejects invalid non-positive evaluation versions.

## Architectural Result

The read side now preserves the decision chain:

`CandidateEvaluation (exact immutable id/version) -> TradePlan -> TradePlanVersion -> Approval / Lifecycle Events`

Later Candidate re-evaluations therefore cannot change the provenance returned for an existing TradePlan.

## Non-Scope preserved

- No REST API.
- No frontend.
- No product / warrant fields.
- No market or candidate recalculation.
- No position sizing, order quantity or execution.

## Quality Gates

- Focused TradePlan/Candidate regression: 30 passed.
- Full backend unit regression suite: passed (see execution gate).
- `compileall backend/app`: passed.
- Ruff: not claimed; no executable/module was available in the current runtime.
