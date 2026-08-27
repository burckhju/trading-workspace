# Post-D01 Golden Path Extension 03 — TradePlan → Product Selection Handoff

## Purpose

Extend the post-D01 stabilization path across the next released downstream seam without adding new business behavior.

This slice qualifies that FT-008 starts from one exact approved FT-007 snapshot and preserves provenance through the explicit user product-selection decision.

## Qualified path

`Candidate-originated TradePlan → APPROVED TradePlanVersion → ProductSelectionRun → ELIGIBLE ProductEvaluation → explicit ProductSelection`

The integration test verifies that:

- Product Selection resolves the TradePlan in the expected workspace;
- Product Selection resolves the exact requested TradePlanVersion;
- the version must already be `APPROVED`;
- the run stores the exact `trade_plan_id`, `trade_plan_version_id`, version status, workspace and underlying;
- the product universe is loaded for the TradePlan underlying;
- a deterministic valid WarrantListing quote produces an `ELIGIBLE` ProductEvaluation;
- the explicit user decision selects a ProductEvaluation from the same immutable run;
- the run snapshot and the later explicit selection are persisted as separate transactions;
- later TradePlanVersions or later ProductSelectionRuns cannot retarget the already-created provenance chain.

## Determinism

The test uses existing service/domain contracts and deterministic in-memory repository/provider doubles. It performs no live EODHD request and introduces no provider-specific orchestration into the golden path.

## Non-scope

This slice does not:

- approve TradePlans automatically;
- change FT-007 or FT-008 production logic;
- define ProductSelection override policy;
- create a Trade or Position;
- introduce broker/execution behavior;
- introduce runtime model activation or dynamic model loading;
- change migrations or persistence schemas.

## Architecture result

The FT-007 → FT-008 boundary is explicit and stable: FT-008 consumes one already-approved immutable TradePlanVersion and snapshots its identity before evaluating product candidates. The later user selection is separately persisted against the exact ProductSelectionRun and ProductEvaluation, so subsequent plan versions or product-selection reruns do not silently change historical decision provenance.

The next unqualified downstream seam is `Product Selection → Trade / Position` (FT-008 → FT-009). It should be reviewed independently before extending the golden path further.
