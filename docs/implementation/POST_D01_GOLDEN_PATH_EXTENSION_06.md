# Post-D01 Golden Path Extension 06

## Purpose

Qualify the next released downstream seam after Extension 05: a fully economically closed workspace trade can enter FT-011, complete the deterministic post-trade observation horizon, produce a finalized current ExitReviewVersion, and become ready at the existing FT-012 handoff gate.

## Qualified path

`closed WORKSPACE_SELECTION trade -> PostTradeObservation ACTIVE -> 20-point underlying EOD horizon -> PostTradeObservation COMPLETED -> ExitReview DRAFT -> ExitReviewVersion FINALIZED/CURRENT -> FT-012 handoff READY`

The integration test uses the released FT-011 application services and domain contracts. Market observations are deterministic in-memory facts; no live provider call is introduced.

## Invariants

- FT-011 starts only from a fully economically closed trade context.
- The observation remains bound to the original `trade_id` and resolved underlying listing.
- Completion requires the configured 20-observation horizon.
- Exit review creation requires a completed observation.
- Finalization stores a reproducible input fingerprint.
- The FT-012 handoff remains blocked before a finalized current review and becomes `READY` only afterwards.
- Historical TradePlan provenance remains input context; FT-011 does not rewrite it.

## Non-scope

- FT-012 learning evidence or lesson creation
- model governance / FT-013
- runtime model activation
- broker integration
- production logic or schema changes
- live EODHD calls in CI

## Implementation

Added `tests/integration/backend/test_ft011_post_trade_exit_review_handoff.py`.

No production code or migration is changed by this slice.
