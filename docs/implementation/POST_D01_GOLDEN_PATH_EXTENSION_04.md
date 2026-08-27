# Post-D01 Golden Path Extension 04 – Product Selection → Trade/Position Handoff

## Goal

Qualify the next released downstream seam after FT-008 without adding new business logic:

```text
ProductSelection
→ record workspace purchase
→ Trade
→ immutable PURCHASE ExecutionRecord
→ Position
```

The slice proves that FT-009 consumes the exact historic FT-008 decision and preserves its upstream provenance when a real purchase is recorded.

## Why now

The post-D01 stabilization sequence already qualifies:

```text
Market Data
→ Analysis
→ Candidate
→ TradePlan
→ Product Selection
```

FT-009 is the next released consumer. Its workspace-guided entry contract requires an existing ProductSelection and reuses the known product, TradePlan, ProductSelection and provenance context. The user supplies only the new execution facts.

## Qualified invariants

The deterministic integration test proves that:

- an explicit FT-008 `ProductSelection` is resolved as the workspace purchase origin;
- the created `Trade` has origin `WORKSPACE_SELECTION`;
- the Trade pins the exact `trade_plan_id`, `trade_plan_version_id`, `product_selection_id` and `product_evaluation_id` from the selected historical context;
- the selected warrant identity becomes the Trade and Execution product identity;
- quantity and actual price create an immutable purchase `ExecutionRecord`;
- `gross_amount` is calculated by the system;
- `Position` is derived deterministically from the effective purchase execution;
- Trade, Execution and Position are added within one FT-009 unit-of-work commit;
- later FT-008 activity cannot retarget the already recorded Trade provenance.

## Scope

- deterministic backend integration test;
- public/domain application contracts only;
- existing FT-008 and FT-009 behavior;
- no provider or broker dependency.

## Non-scope

- additional purchases;
- execution corrections;
- sales or position closing;
- FT-010 trade-management events;
- broker order placement or synchronization;
- live quote requirements;
- automatic position sizing or risk-budget decisions;
- production-code or persistence-schema changes.

## Resulting qualified path

After this slice the stabilization path is qualified through the initial real purchase boundary:

```text
Market Data
→ Analysis
→ Candidate Qualification
→ TradePlan
→ Product Selection
→ Trade + Purchase Execution + Position
```

The next independent downstream seam is Trade/Position → Trade Management / Exit / Post-Trade and should be reviewed as a separate slice rather than folded into this handoff.
