# ADR-S10-001 – Execution Side and SELL Evolution

## Status
Accepted for Sprint 10 specification after S10-00 review and user approval.

## Context
FT-009 released an immutable `ExecutionRecord` representing aggregated PURCHASE executions. FT-010 must record actual sales without creating a second execution world or weakening historical FT-009 data.

## Decision
Evolve the existing `ExecutionRecord` with an explicit execution side:

```text
BUY | SELL
```

Execution quantity remains a positive integral value. Direction is never encoded as a negative quantity.

All historical FT-009 execution rows are migrated/interpreted as `BUY`.

FT-010 does not introduce a separate `SaleExecution` aggregate.

## Consequences
BUY and SELL share one immutable economic execution contract, one correction/effectiveness model and one deterministic projection input. Existing purchase APIs may retain purchase-oriented command names for backward compatibility while mapping to `side=BUY` internally.

Migration must prove that all released FT-009 histories remain behaviorally identical after adding side semantics.

## User impact
The user sees one coherent execution history containing actual purchases and sales instead of separate technical histories.
